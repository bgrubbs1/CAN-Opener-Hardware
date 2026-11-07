# CANOpener Universal — Pre-Layout / Design-Freeze Checklist

The Universal board should **not be released for PCB layout/fabrication** until every P0 item below has an owner, selected implementation, and verification method.

## P0 — architecture

- [ ] Freeze application-computer choice or compute-module interface.
- [ ] Freeze real-time MCU.
- [ ] Freeze programmable timing engine (FPGA/CPLD/PIO MCU).
- [ ] Define internal high-speed host link between compute layer and real-time layer.
- [ ] Define one shared timestamp domain across all bus channels.
- [ ] Define firmware-safe state independent of Linux/SBC state.
- [ ] Define external expansion connector and pinout.

## P0 — protocol/PHY coverage

- [ ] Classical CAN.
- [ ] CAN FD.
- [ ] SWCAN / J2411.
- [ ] ISO 11898-3 fault-tolerant CAN.
- [ ] LIN.
- [ ] K-Line/L-Line / ISO 9141 / ISO 14230 physical layer.
- [ ] J1850 VPW.
- [ ] J1850 PWM.
- [ ] Legacy serial engine for SCI / GM UART / ALDL-class signaling.
- [ ] FlexRay A and B.
- [ ] 100BASE-TX diagnostic Ethernet.
- [ ] DoIP software path.
- [ ] Decide main-board vs expansion for 10BASE-T1S.
- [ ] Decide main-board vs expansion for 100BASE-T1 / 1000BASE-T1.
- [ ] Decide main-board vs expansion for CAN XL.
- [ ] MOST remains external optical pod, not main OBD board.
- [ ] Direct debug/memory protocols remain bench pod.

## P0 — J1962 electrical front end

- [ ] High-Z ADC measurement on every discretionary signal pin.
- [ ] Raw comparator/edge capture on every low-speed-capable discretionary pin.
- [ ] Programmable pull-up/down strategy.
- [ ] Current-limited sink/source strategy.
- [ ] Programmable 0–24 V-class engineering output strategy.
- [ ] Dedicated 5–20 V-class programming-voltage subsystem.
- [ ] Programming-voltage current limit + readback.
- [ ] Controlled short-to-ground function where required.
- [ ] Passive-measure-before-drive interlock.
- [ ] Full high-Z disconnect on reset.
- [ ] Independent hardware TX kill.

## P0 — routing

- [ ] Low-speed/HV routing matrix architecture.
- [ ] High-speed differential routing architecture.
- [ ] Confirm supported OBD pin pairs.
- [ ] Switchable CAN termination.
- [ ] Ethernet activation/detection resistor network.
- [ ] Measure switch capacitance/leakage/Ron effects.
- [ ] SPICE/S-parameter model for HS routes.
- [ ] Prototype the HS matrix before full-board layout.
- [ ] Eye/TDR/BER acceptance criteria written before schematic freeze.

## P0 — power

- [ ] Reverse battery protection.
- [ ] Cranking/cold-crank behavior.
- [ ] Load-dump/transient protection target.
- [ ] ESD target.
- [ ] Input fuse/PTC strategy.
- [ ] Power-path current measurement.
- [ ] Low-quiescent always-on supervisor.
- [ ] SBC hard power gate.
- [ ] Graceful shutdown strategy.
- [ ] Vehicle-bus/ignition wake.
- [ ] USB-powered bench mode.
- [ ] No vehicle back-power from USB.

## P0 — timing / buffering / logging

- [ ] Timestamp resolution target.
- [ ] Cross-channel timestamp skew target.
- [ ] Buffer depth calculated for worst-case simultaneous load.
- [ ] Overflow counter/reporting.
- [ ] No silent packet loss.
- [ ] Local storage throughput benchmark.
- [ ] Real-time bridge latency benchmark.
- [ ] Host disconnect does not break local bus handling.
- [ ] External scope trigger output.

## P0 — host/software compatibility

- [ ] Open internal device protocol documented.
- [ ] SocketCAN adapter plan.
- [ ] J2534 compatibility plan and exact revision(s).
- [ ] J2534 programmable-voltage behavior verified.
- [ ] D-PDU API feasibility preserved by the internal protocol.
- [ ] DoIP support plan.
- [ ] Firmware update mechanism.
- [ ] Recovery/bootloader mechanism.
- [ ] Device firmware/API version negotiation.
- [ ] Windows driver approach decided.
- [ ] Linux/macOS access approach decided.

## P0 — testability

- [ ] Test pad for every J1962 signal.
- [ ] Test pad for every PHY TX/RX/control line.
- [ ] Boundary/self-test strategy.
- [ ] Known-good loopback fixture.
- [ ] OBD breakout harness.
- [ ] Direct-wire harness.
- [ ] Bench ECU harness connector.
- [ ] Automated manufacturing test plan.
- [ ] Thermal test in enclosed OBD housing.
- [ ] Sleep-current test.
- [ ] ESD/transient test plan.
- [ ] Stuck-transmitter/fail-safe test.

## P1 — future-proofing

- [ ] CAN XL daughterboard/interface reservation if not main-board.
- [ ] 10BASE-T1S daughterboard/interface reservation if not main-board.
- [ ] 100/1000BASE-T1 HS pod if not main-board.
- [ ] MOST optical pod.
- [ ] J1708/J1587 / heavy-duty adapter.
- [ ] SENT/PSI5 sensor-bus bench pod.
- [ ] secure element/TPM for device credentials.
- [ ] external PPS/PTP time synchronization.
- [ ] galvanic isolation options for bench/USB.

## Design-freeze gates

### Gate 1 — physical-layer completeness
Can every protocol in the P0 list be connected through a real, correct electrical PHY or the raw programmable legacy path?

### Gate 2 — pin universality
Can the routing architecture place those functions on the required discretionary J1962 pins without unsafe static wiring?

### Gate 3 — signal integrity
Has the high-speed routing topology been measured, not merely simulated?

### Gate 4 — safe failure
If all processors reset at the worst moment, does the vehicle-facing side become passive?

### Gate 5 — programming reliability
Can the device sustain a long diagnostic/programming transaction while the host is busy, wireless is down, or logging is saturated without losing timing-critical traffic?

### Gate 6 — future expansion
Can CAN XL/new Ethernet/other future PHYs be added without redesigning the vehicle power front end and application computer?

**No-build rule:** do not order the Universal main PCB until Gates 1–5 pass at prototype/block level.
