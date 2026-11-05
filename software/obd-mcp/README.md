# CAN Opener MCP for the UNO Q

One Python MCP server supplies tools to Codex, Claude Code, and Hermes. It reads the UNO Q R1 passive
recorder format. A tool call can list captured sessions, inspect capture quality, show mapped signals
and their latest recorded values, or compare the current sample to a saved baseline.

The default server reads a single capture directory. A device-side setup can also expose a bounded
bench recorder and activate one Wi-Fi profile that the device owner has configured and approved.
The device keeps the Wi-Fi credentials in NetworkManager. The agent cannot supply an SSID, password,
shell command, vehicle address, or bus payload.

## Start with saved captures

Use Python 3.11 or newer. From this directory in Windows PowerShell:

```powershell
python -m venv .venv
$python = (Resolve-Path .\.venv\Scripts\python.exe).Path
& $python -m pip install -r requirements.txt
& $python -m unittest -v test_stdio
$server = (Resolve-Path .\obd_server.py).Path
$captures = (Resolve-Path 'C:\OBD\captures').Path
$profile = (Resolve-Path 'C:\OBD\my-vehicle-profile.json').Path
codex mcp add can-opener -- $python $server --logs $captures --profile $profile
claude mcp add --scope local can-opener -- $python $server --logs $captures --profile $profile
```

Replace the two example paths with the operator-owned capture folder and profile. Omit `--profile`
to inspect captures without decoding signals. Run each client registration command only for the
client you use. A Codex session must reload its MCP configuration to discover a new server.

For Hermes, add the following to your profile's `config.yaml` using your own absolute paths.
Hermes discovers the tools at startup. [Hermes MCP reference](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference)

```yaml
mcp_servers:
  can-opener:
    command: 'C:\repo\software\obd-mcp\.venv\Scripts\python.exe'
    args:
      - 'C:\repo\software\obd-mcp\obd_server.py'
      - --logs
      - 'C:\OBD\captures'
      - --profile
      - 'C:\OBD\my-vehicle-profile.json'
    timeout: 60
```

For a directly connected UNO Q, run the same server on its Linux side and register it over an
authenticated SSH stdio session. Use a restricted SSH account or forced command and verify the
host key. A read-only server can also run on the home server against a capture folder supplied
by your existing authenticated file sync. There is no HTTP service to expose.

## Device-side controls

The included `recorder/sketch` and `recorder/capture.py` come from the R1 bench kit. Install the sketch
on the MCU and make the official Arduino App Lab Bridge runtime available to the Python interpreter
on the UNO Q. Run the recorder on a terminated, isolated test bus with a separate ACK node.
The recorder stores evidence on Linux and requires a fresh MCU for each run. It does not use the
R2 stress kit's microSD path. Physical operation and sustained capture still need a bench trial.

On the UNO Q Linux host, the owner can launch the server using a saved, preapproved NetworkManager
profile UUID and the fixed recorder path:

```sh
python3 /opt/can-opener/obd_server.py --logs /var/lib/can-opener/captures --profile /etc/can-opener/signals.json --bench-recorder /opt/can-opener/recorder/capture.py --home-profile 11111111-1111-4111-8111-111111111111
```

The example UUID is a placeholder. Create the profile on the device before enabling this tool.
The operator must approve the exact device and profile. Keep a USB or other management path
available when changing the radio carrying your SSH session. The launcher accepts one UUID
and invokes the local NetworkManager binary with fixed arguments. Configure the device account's
permissions locally. The operation reports profile activation, with no inference about reachability
of the home server.

The recorder tool accepts 1–30 seconds, returns the recorder exit code and available capture IDs,
and serializes launches from this server using a lock in the capture directory. If the server is
killed and the lock remains, verify that the recorder has stopped before clearing the lock.
Use `capture_status` to inspect the finished evidence. Both control tools are absent unless the
owner opts in at launch.

## Signal profiles and examples

A profile is an operator-provided mapping for the specific bus, ECU, and vehicle. Signal definitions
support byte-aligned signed and unsigned integers, endianness, scaling, offset, and standard or
extended CAN IDs. This fictional sample illustrates the format. Real IDs and scaling must come
from a verified mapping for the vehicle.

```json
{
  "name": "synthetic bench demonstration",
  "signals": {
    "throttle": {
      "can_id": 256,
      "byte_offset": 0,
      "byte_length": 1,
      "byte_order": "big",
      "scale": 0.5,
      "unit": "%"
    }
  }
}
```

- “List the sensors available in this capture.” The response lists mapped signals and indicates
  which ones appeared in the sample.
- “What was throttle doing?” The response includes the latest recorded value, its timestamp,
  and the sampled range.
- “Compare throttle against the warmed-up idle baseline.” Select a session ID and compare
  similar operating conditions. The diagnosis tool flags a value outside the sampled baseline
  range only when both recorder summaries pass.
- “Log ten seconds of bench traffic.” Available on the device after recorder setup.
- “Connect to my saved home network.” Available on the device after owner-approved Wi-Fi setup.

The server accepts the recorder's timestamped session folders and reads up to the latest
2 MiB or 10,000 records per query. A missing reading is unknown. The server reports an observed
timestamp so a client can tell a recent sample from an old one. Passive capture sees only traffic
already on the bus. Vehicle-wide discovery, DTC queries, continuous sync, and live ECU diagnosis
remain separate development work.

The SDK test drives the actual stdio entry point with synthetic captures and checks the sensor
queries, baseline calculations, malformed evidence rejection, and session path restrictions.
The named AI clients and device controls still need live verification on the installed UNO Q.
