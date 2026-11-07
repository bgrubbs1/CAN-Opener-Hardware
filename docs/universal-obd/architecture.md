# CANOpener Universal — System Architecture and Protocol Coverage

## 1. Relationship to CANOpener SE

The current CANOpener SE Rev A is intentionally simple: ESP32-C5 plus two CAN-FD channels on the common J1962 CAN pairs. That is a strong Standard Edition architecture.

The Universal design should **not** mutate SE into an unmaintainable board. Treat it as a separate edition/platform with a modular architecture and explicit validation requirements.

## 2. Compute architecture

### 2.1 Application computer

A Pi Zero-class board is acceptable for a prototype because it provides microSD, Wi-Fi, Bluetooth, USB, and Linux in a small package. For a custom integrated board, a compute module/SOM with eMMC is attractive because it improves storage robustness and makes controlled shutdown easier.

The application layer should handle:

- file system and local database;
- SD/eMMC logging;
- Wi-Fi and Bluetooth;
- USB/Ethernet host connection;
- web/API UI;
- Python and native tools;
- firmware/image storage;
- DBC/ODX/PDX/calibration metadata;
- J2534 host compatibility;
- ISO 22900-2 D-PDU host compatibility if practical;
- SocketCAN-compatible access;
- DoIP, UDS, KWP, ISO-TP, XCP/CCP, J1939 and other higher-layer protocols in software.

### 2.2 Real-time bus controller

Use an automotive MCU or equivalent deterministic controller for:

- CAN/CAN-FD controllers;
- FlexRay controller if main-board FlexRay is retained;
- deterministic LIN/K-Line timing;
- wake/sleep management;
- shared hardware timestamping;
- bus state monitoring;
- watchdog/fail-safe state;
- pin matrix control.

An Infineon AURIX-class MCU is a strong candidate because suitable family members combine multiple CAN-FD channels, FlexRay, Ethernet connectivity, serial peripherals, advanced timers, and automotive qualification. Exact device selection remains a schematic-stage trade.

### 2.3 Programmable timing engine

Add a small FPGA/CPLD or deterministic PIO-style MCU for:

- raw edge capture;
- raw edge generation;
- legacy/proprietary serial timing;
- unusual 5-baud/fast-init sequences;
- hardware correlation across bus channels;
- future protocol experiments;
- protocol bridging without Linux scheduling jitter.

This block should share the same master timestamp domain as the automotive MCU.

## 3. Mandatory protocol/PHY coverage

| Capability | Main board target | Notes |
|---|---:|---|
| Classical CAN | Yes, multiple channels | Raw RX/TX, listen-only, error frames where controller permits |
| CAN FD | Yes, >=2 channels | Prefer enough channels for two-bus MITM plus spare monitoring |
| CAN XL | Strong future-proofing target | Main board if controller/PHY maturity and layout permit; otherwise dedicated expansion |
| SWCAN / SAE J2411 / GMLAN | Yes | Dedicated PHY preferred; support wake behavior |
| ISO 11898-3 fault-tolerant CAN | Yes | Added after community review; distinct from HS CAN and SWCAN |
| LIN | Yes, >=2 | Dedicated automotive PHY |
| ISO 9141 K-Line / L-Line | Yes | Dedicated K/L electrical interface, not a CAN transceiver |
| ISO 14230 KWP physical layer | Yes | Same K-Line hardware plus correct init/timing |
| SAE J1850 VPW | Yes | Dedicated or validated discrete physical layer |
| SAE J1850 PWM | Yes | Dedicated or validated physical layer |
| Chrysler SCI / SAE J2610-class | Yes via programmable legacy serial path | Needed for broad legacy J2534 coverage |
| GM UART / ALDL-class serial | Yes via programmable legacy serial path | Include arbitrary baud/timing and 12-V-class level handling |
| Raw programmable single-ended signaling | Yes | Protected comparator/ADC + programmable drive |
| FlexRay A/B | Yes | Dual channel; dedicated controller + PHYs |
| Diagnostic Ethernet 100BASE-TX | Yes | Important for OBD-exposed Ethernet such as BMW ENET-style access |
| DoIP | Software | Requires Ethernet access; ISO 13400 higher layer |
| 10BASE-T1S | Future-proofing target | Increasingly relevant in zonal/edge vehicle architectures |
| 100BASE-T1 | Yes or HS daughterboard | Automotive single-pair Ethernet |
| 1000BASE-T1 | Yes or HS daughterboard | Automotive single-pair Ethernet |
| MOST optical | Expansion only | Optical medium cannot be made universal through copper J1962 pins |
| J1708/J1587 | Expansion / heavy-duty adapter | Not core passenger-car J1962 requirement, but leave timing/PHY path available |
| SENT / PSI5 | Expansion / bench pod | Sensor-local protocols, generally not an OBD need |
| JTAG/SWD/BDM/DAP/BSL | Bench pod | Not an OBD bus; important for direct ECU development/recovery |
| SPI/QSPI/I2C/Microwire direct memory | Bench pod | EEPROM/flash work |
| eMMC/NAND/NOR direct programming | Bench pod | Larger connector/fixture requirements; keep outside OBD shell |

## 4. J2534 compatibility requirements that affect hardware

J2534 is a host API, but full practical compatibility places hardware requirements on the VCI.

The design should include:

- raw pass-through CAN in addition to ISO-TP assistance;
- ISO 9141 five-baud and fast initialization;
- J1850 PWM/VPW;
- SCI/legacy serial support where targeted;
- programmable voltage supply;
- readback of battery and programming voltage;
- deterministic message filters and periodic transmission;
- enough buffering that host/USB jitter does not corrupt long service-programming sessions.

Historic J2534 requirements include a **5–20 V programmable supply** on certain discretionary J1962 pins. The Universal design can exceed this with a protected 0–24 V-class generator, but it must still be able to reproduce the standard behavior with controlled slew, current limiting, readback, and safe shutdown.

## 5. ISO 22900-2 D-PDU API

Add D-PDU support to the software roadmap. D-PDU is another standardized VCI API used in professional diagnostics/test systems. This is not another vehicle PHY; it is a host-side compatibility layer.

Design consequence: keep the internal device protocol capable of:

- parallel logical channels;
- precise filters;
- periodic messages;
- timing control;
- asynchronous events;
- diagnostic Ethernet;
- multiple physical buses at once.

Do not design an internal USB protocol so narrow that J2534 works but D-PDU cannot be implemented later.

## 6. Per-channel timing and timestamping

Community and academic review both point toward one requirement that should be promoted to P0:

> Every receive/transmit event across every bus should be timestamped against one shared hardware timebase.

Recommended target for design exploration:

- timestamp resolution <= 100 ns;
- deterministic channel-to-channel skew characterized and documented;
- hardware capture before host buffering;
- ability to synchronize external scope/logic analyzer via trigger GPIO;
- optional PPS/PTP discipline for long captures;
- explicit overflow counters so dropped frames are never silent.

The exact numeric target should be verified against component capabilities; the principle is more important than an arbitrary number.

## 7. Routing fabric

### 7.1 Low-speed/HV matrix

Route discretionary J1962 pins to:

- K/L-Line PHY;
- LIN PHY;
- J1850 drivers/receivers;
- SWCAN;
- legacy serial;
- generic analog input;
- generic comparator/edge capture;
- programmable 0–24 V-class source/sink path;
- programmable pull-up/down;
- programming-voltage source.

Requirements:

- open/high-Z default;
- bidirectional where appropriate;
- automotive transient rating;
- known leakage and capacitance;
- current limiting;
- per-route fault detection.

### 7.2 High-speed pair matrix

Route selected OBD pin pairs to dedicated differential PHYs.

High-speed switching is a **signal-integrity problem**. A generic HV analog crosspoint may have too much capacitance/stub loading for CAN FD, CAN XL, FlexRay, or Ethernet.

Candidate approaches to compare before schematic freeze:

1. automotive/high-bandwidth analog switches with S-parameter validation;
2. low-capacitance RF/high-speed crosspoints behind protected front ends;
3. miniature signal relays for selected critical paths;
4. a smaller number of electrically pristine PHY ports plus an external electronically controlled remap pod.

Do not commit to an all-solid-state universal matrix until eye/TDR simulations and bench prototypes prove it.

## 8. Ethernet activation/detection

Do not assume "Ethernet PHY present" is enough.

Some diagnostic Ethernet implementations use J1962 discretionary pins for:

- two Ethernet pairs;
- an activation/detection line;
- resistance-based cable/adapter identification.

Therefore include:

- protected resistor-selection network;
- programmable activation-line behavior;
- ability to measure resistance/voltage before asserting activation;
- normal 100BASE-TX MAC/PHY support in addition to BASE-T1 automotive Ethernet.

## 9. Power architecture

Minimum requirements:

- 8–24 V normal vehicle operation target;
- automotive reverse-battery protection;
- cold-crank survival;
- load-dump/transient protection appropriate to the intended installation class;
- ESD protection;
- controlled inrush;
- input fuse/PTC strategy;
- current monitoring;
- low-quiescent always-on supervisor;
- hard power gating for application computer;
- graceful Linux/SBC shutdown;
- wake from ignition, CAN/SWCAN, timer, or USB as appropriate;
- independent watchdog.

A long-term OBD-installed device should not leave a Linux computer fully awake.

## 10. Bench/debug expansion

Use a small protected expansion connector with:

- Vtarget sense;
- 1.2/1.8/2.5/3.3/5 V logic-level translation;
- programmable GPIO;
- JTAG;
- SWD;
- BDM/DAP/Nexus-capable pins where implementable;
- UART RX/TX;
- RESET/BOOT/TRST;
- SPI/QSPI;
- I2C;
- Microwire;
- target power enable;
- controlled ignition/battery outputs;
- current measurement/current limiting.

Adapters handle SOP clips, pogo fixtures, ECU-specific connectors, optical MOST, etc. Keep bulky fixtures out of the OBD enclosure.

## 11. Future-proof expansion bus

Expose enough internal bandwidth that a future bus does not force a motherboard respin:

- USB 2/3 as architecture permits;
- PCIe if the chosen compute module supports it;
- SPI;
- I2C;
- UART;
- GPIO;
- 3.3 V and 5 V;
- protected vehicle supply;
- wake/reset;
- shared timebase/trigger if feasible.

Reserve for:
- CAN XL revisions;
- future automotive Ethernet;
- MOST pod;
- sensor-bus pod;
- new OEM-specific PHYs.

## 12. Key engineering boundary

No OBD interface can directly reach a bus that is not wired to the diagnostic connector/gateway. The Universal tool should therefore include a breakout/harness mode for direct internal-bus attachment.

The hardware goal is **electrical universality where a wire/path exists**, not a promise that every ECU in every vehicle is physically exposed at the DLC.
