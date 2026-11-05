"""UNO Q capture tools. Usage: python obd_server.py --logs /path/to/captures"""

import argparse
import json
import math
import os
import re
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations


SESSION = re.compile(r"\d{8}T\d{6}Z-[0-9a-f]{8}")
MAX_WINDOW_BYTES = 2 * 1024 * 1024
READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
LOCAL_CONTROL = ToolAnnotations(destructiveHint=False, openWorldHint=False)


def safe_file(directory, name):
    path = directory / name
    if path.resolve() != path:
        raise ValueError(f"Linked {name} is outside the capture format")
    return path


def read_json(path):
    with path.open("rb") as stream:
        data = stream.read(65537)
    if len(data) > 65536:
        raise ValueError(f"{path.name} exceeds the metadata size limit")
    result = json.loads(data)
    if not isinstance(result, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return result


def read_profile(path):
    if path is None:
        return {}, None
    profile = read_json(path)
    name, signals = profile["name"], profile["signals"]
    if not isinstance(name, str) or not name or len(name) > 100 or not isinstance(signals, dict) or len(signals) > 100:
        raise ValueError("Expected a named profile with at most 100 signals")
    for key, spec in signals.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,47}", key) or not isinstance(spec, dict):
            raise ValueError("Invalid signal key or definition")
        ident, offset, size = (spec[k] for k in ("can_id", "byte_offset", "byte_length"))
        for value, minimum, maximum in ((ident, 0, 0x1FFFFFFF), (offset, 0, 63), (size, 1, 8)):
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(f"{key} has an invalid CAN ID or byte range")
        if spec.get("byte_order") not in ("little", "big") or offset + size > 64:
            raise ValueError(f"{key} has an invalid payload layout")
        for flag in ("extended", "signed"):
            if type(spec.get(flag, False)) is not bool:
                raise ValueError(f"{key} has an invalid {flag} flag")
        if ident > 0x7FF and not spec.get("extended"):
            raise ValueError(f"{key} requires an extended identifier")
        unit = spec.get("unit")
        if not isinstance(unit, str) or not unit or len(unit) > 24:
            raise ValueError(f"{key} requires a unit")
        for field, default in (("scale", 1), ("offset", 0)):
            val = spec.get(field, default)
            if type(val) not in (int, float) or not math.isfinite(val) or abs(val) > 1e12:
                raise ValueError(f"{key} has an invalid {field}")
    return signals, name


class Captures:
    def __init__(self, root):
        self.root = root.resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("The capture root must be a directory")

    def sessions(self, limit):
        if not 1 <= limit <= 100:
            raise ValueError("limit must be 1–100")
        return sorted(
            (p.name for p in self.root.iterdir()
             if SESSION.fullmatch(p.name) and p.resolve() == p and p.is_dir()),
            reverse=True,
        )[:limit]

    def directory(self, session):
        if session is None:
            newest = self.sessions(1)
            if not newest:
                raise ValueError("No captures found. Start the UNO Q recorder or select its capture directory.")
            session = newest[0]
        if not SESSION.fullmatch(session):
            raise ValueError("Use a session ID returned by list_sessions")
        path = self.root / session
        if path.resolve(strict=True) != path or not path.is_dir():
            raise ValueError("Capture session is unavailable")
        return path

    def frames(self, session, count):
        if not 1 <= count <= 10000:
            raise ValueError("sample_frames must be 1–10000")
        path = safe_file(self.directory(session), "frames.jsonl")
        with path.open("rb") as stream:
            length = stream.seek(0, 2)
            start = max(0, length - MAX_WINDOW_BYTES)
            stream.seek(start)
            data = stream.read(length - start)
        lines = data.splitlines()
        if start:
            lines = lines[1:]
        if not data.endswith(b"\n"):
            lines = lines[:-1]
        for line in lines[-count:]:
            try:
                frame = json.loads(line)
                if not isinstance(frame, dict):
                    raise ValueError("Frame must be an object")
                ident, flags, host_ns = (frame[key] for key in ("id", "flags", "host_ns"))
                payload = frame["data"]
                if (type(ident) is not int or type(flags) is not int or not 0 <= flags <= 31
                        or not 0 <= ident <= (0x1FFFFFFF if flags & 1 else 0x7FF)
                        or type(host_ns) is not int or not 0 <= host_ns < 10**20
                        or not isinstance(payload, str) or not re.fullmatch(r"(?:[0-9a-fA-F]{2}){0,64}", payload)):
                    raise ValueError("Frame fields out of range")
                yield ident, flags, host_ns, bytes.fromhex(payload)
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("Invalid complete frame record in the selected sample") from exc

    def status(self, session):
        directory = self.directory(session)
        meta = read_json(safe_file(directory, "metadata.json"))
        summary = safe_file(directory, "summary.json")
        report = read_json(summary) if summary.is_file() else {}
        return {"session": directory.name, "mode": meta.get("mode"), "started_utc": meta.get("utc_start"),
                "nominal_bitrate": meta.get("nominal_bitrate"), "finalized": bool(report),
                "stored": report.get("stored"), "sequence_gaps": report.get("sequence_gaps"),
                "software_capture_ok": report.get("software_capture_ok"),
                "reported_errors": len(report.get("errors", [])),
                "meaning": "Capture evidence only. A missing summary may be live or interrupted."}


def decode(frame, spec):
    ident, flags, _, payload = frame
    if ident != spec["can_id"] or bool(flags & 1) != spec.get("extended", False) or flags & 2:
        return None
    start = spec["byte_offset"]
    end = start + spec["byte_length"]
    if len(payload) < end:
        return None
    raw = int.from_bytes(payload[start:end], spec["byte_order"], signed=spec.get("signed", False))
    return raw * spec.get("scale", 1) + spec.get("offset", 0)


def make_server(captures, signals, profile_name, recorder=None, home_profile=None):
    server = FastMCP("can-opener", instructions=(
        "Use the user's configured signal profile. Never infer signals from raw IDs. "
        "Compare equivalent operating conditions and report capture gaps. "
        "These tools inspect a passive recorder and do not send vehicle traffic."
    ))

    @server.tool(annotations=READ_ONLY, structured_output=True)
    def list_sessions(limit: int = 20) -> dict[str, Any]:
        """List local capture IDs, newest first."""
        return {"sessions": captures.sessions(limit), "signal_profile": profile_name}

    @server.tool(annotations=READ_ONLY, structured_output=True)
    def capture_status(session: str | None = None) -> dict[str, Any]:
        """Inspect recorder evidence for the newest or a named capture."""
        return captures.status(session)

    @server.tool(annotations=READ_ONLY, structured_output=True)
    def list_sensors(session: str | None = None, sample_frames: int = 2000) -> dict[str, Any]:
        """List mapped signals and whether each appeared in the latest bounded sample."""
        frames = list(captures.frames(session, sample_frames))
        return {"profile": profile_name, "frames_sampled": len(frames),
                "sensors": [{"name": key, "unit": spec["unit"],
                             "observed": any(decode(frame, spec) is not None for frame in frames)}
                            for key, spec in signals.items()],
                "meaning": "Signals in this profile. An absent signal does not establish what sensors the vehicle has."}

    def readings(sensor, session, sample_frames):
        if sensor not in signals:
            raise ValueError("Unknown signal. Use list_sensors to inspect the configured profile.")
        spec = signals[sensor]
        samples = [(frame[2], value) for frame in captures.frames(session, sample_frames)
                   if (value := decode(frame, spec)) is not None]
        if not samples:
            return {"unit": spec["unit"], "samples": 0, "latest": None}
        values = [value for _, value in samples]
        ns, value = samples[-1]
        observed = datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).isoformat()
        return {"unit": spec["unit"], "samples": len(samples), "latest": value,
                "min": min(values), "max": max(values), "mean": statistics.fmean(values),
                "observed_utc": observed}

    @server.tool(annotations=READ_ONLY, structured_output=True)
    def sensor_reading(sensor: str, session: str | None = None, sample_frames: int = 2000) -> dict[str, Any]:
        """Show a signal's latest recorded value, timestamp, and recent range."""
        return readings(sensor, session, sample_frames)

    @server.tool(annotations=READ_ONLY, structured_output=True)
    def compare_baseline(sensor: str, baseline: str, current: str | None = None,
                         sample_frames: int = 2000) -> dict[str, Any]:
        """Compare sampled distributions for a signal across two capture sessions."""
        actual = readings(sensor, current, sample_frames)
        reference = readings(sensor, baseline, sample_frames)
        delta = actual["mean"] - reference["mean"] if actual["samples"] and reference["samples"] else None
        return {"sensor": sensor, "profile": profile_name, "current": actual, "baseline": reference,
                "mean_delta": delta, "meaning": "Compare like operating conditions. A difference alone is not a diagnosis."}

    @server.tool(annotations=READ_ONLY, structured_output=True)
    def diagnose_capture(session: str | None = None) -> dict[str, Any]:
        """Identify capture quality issues before interpreting vehicle data."""
        result = captures.status(session)
        issues = []
        if not result["finalized"]:
            issues.append("No final recorder summary")
        elif result["software_capture_ok"] is not True:
            issues.append("Recorder acceptance failed")
        if result["sequence_gaps"]:
            issues.append("Frame sequence gaps reported")
        if result["reported_errors"]:
            issues.append("Recorder reported errors")
        return {"capture": result, "issues": issues,
                "meaning": "This checks recorder evidence. Vehicle diagnosis requires a verified vehicle profile."}

    @server.tool(annotations=READ_ONLY, structured_output=True)
    def diagnose_sensor(sensor: str, baseline: str, current: str | None = None,
                        sample_frames: int = 2000) -> dict[str, Any]:
        """Flag observations outside a comparable baseline and report capture quality."""
        result = compare_baseline(sensor, baseline, current, sample_frames)
        status = [diagnose_capture(session) for session in (current, baseline)]
        actual, reference = result["current"], result["baseline"]
        result["capture_issues"] = [check["issues"] for check in status]
        usable = not any(result["capture_issues"]) and actual["samples"] and reference["samples"]
        result["latest_outside_baseline_range"] = (
            not reference["min"] <= actual["latest"] <= reference["max"] if usable else None
        )
        return result

    if recorder is not None:
        @server.tool(annotations=LOCAL_CONTROL, structured_output=True)
        def log_bench_data(seconds: int = 10) -> dict[str, Any]:
            """Run the configured passive UNO Q bench recorder for up to 30 seconds."""
            if not 1 <= seconds <= 30:
                raise ValueError("seconds must be 1–30")
            # The operator selects the fixed script at server startup. The AI controls only duration.
            command = [sys.executable, str(recorder), "--bench-only", "--seconds",
                       str(seconds), "--output", str(captures.root)]
            lock = captures.root / ".agent-recorder.lock"
            try:
                fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError as exc:
                raise ValueError("Recorder lock exists. Check the running recorder before retrying.") from exc
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    stream.write(str(os.getpid()) + "\n")
                result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=sys.stderr,
                                        stderr=sys.stderr, timeout=seconds + 25, check=False)
            finally:
                lock.unlink()
            return {"exit_code": result.returncode, "sessions": captures.sessions(5),
                    "meaning": "Use capture_status to verify the saved session. The recorder requires a fresh MCU."}

    if home_profile is not None:
        @server.tool(annotations=ToolAnnotations(destructiveHint=True, openWorldHint=True), structured_output=True)
        def connect_home_network() -> dict[str, Any]:
            """Activate the single saved NetworkManager profile preapproved by the device owner."""
            result = subprocess.run(["/usr/bin/nmcli", "--wait", "15", "connection", "up", "uuid", home_profile],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, timeout=20, check=False)
            return {"profile_activated": result.returncode == 0, "exit_code": result.returncode,
                    "meaning": "NetworkManager activation status. Home server access is a separate check."}

    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--profile", type=Path, help="Operator-supplied CAN signal map")
    parser.add_argument("--bench-recorder", type=Path, help="Enable a trusted UNO Q R1 passive capture.py")
    parser.add_argument("--home-profile", type=UUID, help="Enable activation of one preapproved saved Wi-Fi profile")
    args = parser.parse_args()
    if (args.bench_recorder or args.home_profile) and sys.platform != "linux":
        parser.error("Recorder and Wi-Fi controls run on the UNO Q Linux host")
    if args.home_profile and not Path("/usr/bin/nmcli").is_file():
        parser.error("NetworkManager nmcli is required for the Wi-Fi tool")
    recorder = args.bench_recorder.resolve(strict=True) if args.bench_recorder else None
    if recorder and not recorder.is_file():
        parser.error("The configured recorder must be a file")
    signals, profile_name = read_profile(args.profile)
    make_server(Captures(args.logs), signals, profile_name, recorder,
                str(args.home_profile) if args.home_profile else None).run(transport="stdio")


if __name__ == "__main__":
    main()
