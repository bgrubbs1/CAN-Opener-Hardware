"""Bounded UNO Q receiver. Usage: python capture.py --bench-only --seconds 120

Only imports the board's official Bridge runtime when a real capture is requested.
No vehicle control, network service, credentials, or external upload is implemented.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import time
import uuid

DLC_BYTES = (0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 20, 24, 32, 48, 64)
BOOT_RE = re.compile(r"^[0-9a-f]{16}$")


def integer(value, lo, hi, name):
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError(f"Invalid {name}: {value!r}")
    return value


def decode(value):
    if not isinstance(value, str) or len(value) > 1024:
        raise ValueError("Expected a bounded JSON string from MCU")
    return json.loads(value)


def status(value):
    s = decode(value)
    if not isinstance(s, dict) or s.get("v") != 1 or not BOOT_RE.fullmatch(str(s.get("boot", ""))):
        raise ValueError("Unsupported MCU status")
    for key in ("init", "rc"):
        integer(s[key], -4096, 0, key)
        if s[key] != 0:
            raise RuntimeError(f"MCU {key} failed: {s[key]}")
    for key in ("running", "started", "fd", "held"):
        integer(s[key], 0, 1, key)
    for key in ("rx", "drop"):
        integer(s[key], 0, 0xFFFFFFFF, key)
    for key in ("rec", "tec"):
        integer(s[key], 0, 255, key)
    integer(s["q"], 0, 64, "queue depth")
    integer(s["state"], 0, 4, "CAN state")
    integer(s["tick_hz"], 1, 1000000000, "tick frequency")
    return s


def validate_frame(fields):
    if not isinstance(fields, list) or len(fields) != 6:
        raise ValueError("Invalid frame shape")
    seq, us, ident, flags, dlc, data = fields
    integer(seq, 1, 0xFFFFFFFF, "sequence")
    integer(us, 0, 0xFFFFFFFFFFFFFFFF, "timestamp")
    integer(flags, 0, 31, "flags")
    integer(ident, 0, 0x1FFFFFFF if flags & 1 else 0x7FF, "CAN identifier")
    integer(dlc, 0, 15 if flags & 4 else 8, "DLC")
    if (flags & 2 and flags & 4) or (flags & 24 and not flags & 4):
        raise ValueError("Invalid RTR/FD/BRS/ESI combination")
    length = 0 if flags & 2 else DLC_BYTES[dlc]
    if not isinstance(data, str) or len(data) != 2 * length or not re.fullmatch(r"[0-9a-f]*", data):
        raise ValueError("Invalid payload length or encoding")
    return {"seq": seq, "mcu_us": us, "id": ident, "flags": flags, "dlc": dlc, "data": data}


def response(value, boot):
    item = decode(value)
    if not isinstance(item, list) or len(item) != 3 or item[0] != boot:
        raise ValueError("MCU reset, wrong session, or malformed response")
    batch = integer(item[1], 0, 0xFFFFFFFF, "batch")
    if item[2] is None:
        if batch != 0:
            raise ValueError("Empty batch with nonzero identifier")
        return 0, None
    if batch == 0:
        raise ValueError("Frame with zero batch identifier")
    return batch, validate_frame(item[2])


def durable_line(stream, value):
    stream.write(json.dumps(value, separators=(",", ":")) + "\n")
    stream.flush()
    os.fsync(stream.fileno())


def capture(bridge, output_root, seconds=120, fd=False, min_free_bytes=256 * 1024 * 1024):
    """Create a new capture directory; return (directory, summary). Never resume files."""
    if not 0 < seconds <= 3600:
        raise ValueError("Duration must be >0 and <=3600 seconds")
    root = Path(output_root).resolve(strict=True)
    if not root.is_dir() or shutil.disk_usage(root).free < min_free_bytes:
        raise RuntimeError("Output directory unavailable or insufficient free space")
    initial = status(bridge.call("capture.status", timeout=2))
    if initial["started"] or initial["running"] or initial["rx"] or initial["drop"] or initial["q"] or initial["held"]:
        raise RuntimeError("MCU is not fresh; reset it intentionally before a new session")
    if bool(initial["fd"]) != bool(fd):
        raise RuntimeError("Sketch FD mode does not match logger --fd")
    boot = initial["boot"]
    name = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    dest = root / name
    dest.mkdir(exist_ok=False)
    metadata = {"schema": 1, "utc_start": dt.datetime.now(dt.timezone.utc).isoformat(),
                "platform": platform.platform(), "python": sys.version, "seconds": seconds,
                "initial": initial, "mode": "listen-only", "nominal_bitrate": 500000,
                "data_bitrate": 2000000 if fd else None, "output": str(dest),
                "timestamp": "MCU callback kernel ticks converted to us; not CAN SOF",
                "durability": "flush+fsync before each record acknowledgement; medium power-loss behavior untested"}
    with (dest / "metadata.json").open("x", encoding="utf-8") as f:
        durable_line(f, metadata)
    ack = 0
    count = 0
    last_seq = 0
    last_us = 0
    gaps = 0
    max_rec = max_tec = 0
    final = None
    errors = []
    start_attempted = False
    with (dest / "frames.jsonl").open("x", encoding="utf-8", newline="\n") as frames, (dest / "events.jsonl").open("x", encoding="utf-8", newline="\n") as events:
        try:
            start_attempted = True
            rc = bridge.call("capture.start", timeout=2)
            if type(rc) is not int or rc != 0:
                raise RuntimeError(f"capture.start failed: {rc!r}")
            durable_line(events, {"event": "started", "host_ns": time.time_ns()})
            print(f"READY: {dest}", flush=True)
            deadline = time.monotonic() + seconds
            next_status = time.monotonic()
            draining = False
            while True:
                now = time.monotonic()
                if not draining and now >= deadline:
                    rc = bridge.call("capture.stop", timeout=2)
                    if type(rc) is not int or rc != 0:
                        raise RuntimeError(f"capture.stop failed: {rc!r}")
                    draining = True
                    deadline = time.monotonic() + 10
                if draining and now >= deadline:
                    raise TimeoutError("Queue drain deadline exceeded")
                if now >= next_status:
                    if shutil.disk_usage(dest).free < min_free_bytes:
                        raise RuntimeError("Free space reserve reached")
                    current = status(bridge.call("capture.status", timeout=2))
                    if current["boot"] != boot or current["fd"] != initial["fd"]:
                        raise RuntimeError("MCU reset or configuration changed")
                    max_rec = max(max_rec, current["rec"])
                    max_tec = max(max_tec, current["tec"])
                    durable_line(events, {"event": "status", "host_ns": time.time_ns(), "status": current})
                    if not current["started"] or current["running"] != int(not draining):
                        raise RuntimeError("Unexpected MCU capture state")
                    if current["state"] != (4 if draining else 0):
                        raise RuntimeError(f"CAN controller state fault: {current['state']}")
                    next_status = now + 1
                batch, frame = response(bridge.call("capture.read", ack, timeout=2), boot)
                if frame is None:
                    if draining:
                        break
                    time.sleep(0.005)
                    continue
                if batch != ack + 1 or frame["seq"] <= last_seq or frame["mcu_us"] < last_us:
                    raise ValueError("Batch/sequence replay, wrap, or timestamp regression")
                gaps += frame["seq"] - last_seq - 1
                frame.update({"batch": batch, "boot": boot, "host_ns": time.time_ns()})
                durable_line(frames, frame)
                ack = batch
                count += 1
                last_seq, last_us = frame["seq"], frame["mcu_us"]
        except (Exception, KeyboardInterrupt) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
        finally:
            if start_attempted:
                try:
                    rc = bridge.call("capture.stop", timeout=2)
                    if type(rc) is not int or rc != 0:
                        raise RuntimeError(f"capture.stop failed: {rc!r}")
                    final = status(bridge.call("capture.status", timeout=2))
                    if final["boot"] != boot:
                        raise RuntimeError("MCU reset before final status")
                    max_rec = max(max_rec, final["rec"])
                    max_tec = max(max_tec, final["tec"])
                except Exception as exc:
                    errors.append(f"Finalization {type(exc).__name__}: {exc}")
    complete = bool(final and final["state"] == 4 and final["started"] == 1
                    and not final["running"] and not final["q"] and not final["held"]
                    and final["rx"] == count and final["drop"] == 0)
    passed = complete and count > 0 and gaps == 0 and max_rec == max_tec == 0 and not errors
    result = {"schema": 1, "software_capture_ok": bool(passed), "stored": count,
              "sequence_gaps": gaps, "max_sampled_rec": max_rec, "max_sampled_tec": max_tec,
              "final": final, "errors": errors,
              "limitations": "Not proof of lossless bus capture. Compare traffic-source counters; hardware FIFO loss and errors between status samples can escape these counters."}
    with (dest / "summary.json").open("x", encoding="utf-8") as f:
        durable_line(f, result)
    return dest, result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bench-only", action="store_true")
    parser.add_argument("--seconds", type=float, default=120)
    parser.add_argument("--fd", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if not args.bench_only or not 1 <= args.seconds <= 3600:
        parser.error("Requires --bench-only and --seconds between 1 and 3600")
    root = args.output
    if root is None:
        root = Path(__file__).resolve().parents[1] / "data"
        root.mkdir(exist_ok=True)
    try:
        from arduino.app_utils import Bridge
        dest, result = capture(Bridge, root, args.seconds, args.fd)
        print(json.dumps({"directory": str(dest), **result}, indent=2))
        return 0 if result["software_capture_ok"] else 2
    except Exception as exc:
        print(f"Capture unavailable: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
