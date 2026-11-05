"""Run a real MCP client against the server. Usage: python -m unittest -v test_stdio"""

import asyncio
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from obd_server import Captures, make_server


BASELINE = "20261104T160000Z-00000001"
CURRENT = "20261104T161000Z-00000002"


def write_capture(root, session, values):
    path = root / session
    path.mkdir()
    (path / "metadata.json").write_text(json.dumps({"mode": "listen-only"}), encoding="utf-8")
    (path / "summary.json").write_text(json.dumps({
        "stored": len(values), "sequence_gaps": 0, "software_capture_ok": True, "errors": [],
    }), encoding="utf-8")
    with (path / "frames.jsonl").open("w", encoding="utf-8") as log:
        for value in values:
            log.write(json.dumps({"id": 256, "flags": 0, "host_ns": 1793811600000000000,
                                  "data": f"{value:02x}"}) + "\n")
        log.write('{"incomplete":')


class StdioTest(unittest.TestCase):
    def test_capture_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_capture(root, BASELINE, [30, 40])
            write_capture(root, CURRENT, [50, 60])
            profile = root / "profile.json"
            profile.write_text(json.dumps({"name": "synthetic", "signals": {
                "throttle": {"can_id": 256, "byte_offset": 0, "byte_length": 1,
                             "byte_order": "big", "scale": 0.5, "unit": "%"},
                "absent_signal": {"can_id": 257, "byte_offset": 0, "byte_length": 1,
                                  "byte_order": "big", "unit": "V"},
            }}), encoding="utf-8")
            asyncio.run(self.exercise(root, profile))

    async def exercise(self, root, profile):
        launcher = StdioServerParameters(command=sys.executable, args=[
            str(Path(__file__).with_name("obd_server.py")), "--logs", str(root), "--profile", str(profile),
        ])
        async with stdio_client(launcher) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                names = {tool.name for tool in (await client.list_tools()).tools}
                self.assertEqual(names, {"list_sessions", "capture_status", "list_sensors", "sensor_reading",
                                         "compare_baseline", "diagnose_capture", "diagnose_sensor"})
                sessions = await client.call_tool("list_sessions", {})
                self.assertEqual(sessions.structuredContent["sessions"], [CURRENT, BASELINE])
                sensors = await client.call_tool("list_sensors", {})
                self.assertEqual({s["name"]: s["observed"] for s in sensors.structuredContent["sensors"]},
                                 {"throttle": True, "absent_signal": False})
                now = await client.call_tool("sensor_reading", {"sensor": "throttle"})
                self.assertEqual(now.structuredContent["latest"], 30.0)
                self.assertEqual(now.structuredContent["samples"], 2)
                absent = await client.call_tool("sensor_reading", {"sensor": "absent_signal"})
                self.assertIsNone(absent.structuredContent["latest"])
                diff = await client.call_tool("diagnose_sensor", {"sensor": "throttle", "baseline": BASELINE})
                self.assertEqual(diff.structuredContent["mean_delta"], 10.0)
                self.assertTrue(diff.structuredContent["latest_outside_baseline_range"])
                traversal = await client.call_tool("capture_status", {"session": "../profile.json"})
                self.assertTrue(traversal.isError)
                with (root / CURRENT / "frames.jsonl").open("a", encoding="utf-8") as log:
                    log.write("\n")
                corrupted = await client.call_tool("sensor_reading", {"sensor": "throttle"})
                self.assertTrue(corrupted.isError)

    def test_control_arguments_are_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            script = root / "capture.py"
            profile = "11111111-1111-4111-8111-111111111111"
            server = make_server(Captures(root), {}, None, script, profile)
            with patch("obd_server.subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
                asyncio.run(server.call_tool("log_bench_data", {"seconds": 10}))
                self.assertEqual(run.call_args.args[0], [
                    sys.executable, str(script), "--bench-only", "--seconds", "10", "--output", str(root),
                ])
                self.assertFalse((root / ".agent-recorder.lock").exists())
                with self.assertRaises(Exception):
                    asyncio.run(server.call_tool("log_bench_data", {"seconds": 31}))
                self.assertEqual(run.call_count, 1)
                (root / ".agent-recorder.lock").touch()
                with self.assertRaises(Exception):
                    asyncio.run(server.call_tool("log_bench_data", {"seconds": 1}))
                self.assertEqual(run.call_count, 1)
                asyncio.run(server.call_tool("connect_home_network", {}))
                self.assertEqual(run.call_args.args[0], [
                    "/usr/bin/nmcli", "--wait", "15", "connection", "up", "uuid", profile,
                ])


if __name__ == "__main__":
    unittest.main()
