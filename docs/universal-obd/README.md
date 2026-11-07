# CANOpener Universal — Design Intent

**Status:** pre-schematic architecture / design-review baseline  
**Date:** 2026-09-20  
**Target repository:** `bgrubbs1/CAN-Opener-Hardware`  
**Target path:** `docs/universal-obd/`

This design is intentionally separate from the existing **CANOpener SE Rev A**. The SE is a compact dual Classical CAN/CAN-FD interface. The Universal concept is a future interface whose purpose is to remove as many **physical-interface limitations** as practical for authorized vehicle diagnostics, configuration, calibration, service programming, logging, bench development, and protocol research.

## 1. Core requirement

> If an authorized operation can be performed through electrical communication that is physically reachable at the SAE J1962/OBD connector, the interface hardware should not be the reason it cannot be done.

That means the hardware should be capable of supporting, when the vehicle and software permit it:

- generic and manufacturer-specific diagnostics;
- coding/configuration and adaptations;
- actuator and bidirectional tests;
- ECU/BCM/TCM service programming;
- calibration access such as fuel and spark tables where the controller exposes an accessible programming path;
- changing feature configuration, including disabling or changing TPMS behavior **in vehicle software** if that is a configurable function;
- raw frame logging, protocol analysis, gateway work, and multi-bus engineering;
- direct bench access to ECUs when an OBD path is insufficient.

**TPMS RF transmit/receive is not a project requirement.** The TPMS use case is software/configuration access through the vehicle network, not impersonating wheel sensors.

This goal does **not** imply that the device can supply OEM signing keys, online dealer authorization, unknown credentials, unknown calibration definitions, or access to a network that is physically not exposed through the diagnostic gateway/connector.

## 2. Design philosophy

The Universal interface should not behave like an ELM327-style interpreter that hides the vehicle behind a narrow command set. It should expose:

- raw bus frames;
- deterministic timestamps;
- raw edge timing for unusual legacy initialization/signaling;
- programmable routing of OBD pins to physical-layer interfaces;
- programmable low-speed voltage behavior;
- dedicated transceivers for high-speed/specialized buses;
- local storage and wireless connectivity;
- a documented, open host protocol;
- host APIs compatible with normal engineering and OEM-service software where practical.

## 3. Recommended functional partition

```text
                    Wi-Fi / Bluetooth / USB / Ethernet
                                 |
                    +------------v------------+
                    | Application computer    |
                    | Pi/CM/SBC or equivalent |
                    |-------------------------|
                    | logging / SD or eMMC    |
                    | local database          |
                    | Python/native tools     |
                    | SocketCAN adapters      |
                    | J2534 / D-PDU host      |
                    | DoIP / UDS / KWP        |
                    +------------+------------+
                                 |
                        high-speed host link
                                 |
                    +------------v------------+
                    | Real-time bus engine    |
                    | automotive MCU          |
                    | + shared timebase       |
                    +------------+------------+
                                 |
                    +------------v------------+
                    | Programmable timing     |
                    | FPGA/CPLD/PIO-class MCU |
                    | edge capture/generation |
                    +------------+------------+
                                 |
        +------------------------+-------------------------+
        |                        |                         |
   protocol controllers     low-speed/HV PHYs       high-speed PHYs
        |                        |                         |
   CAN/CAN-FD/XL*          K/L/LIN/J1850/etc.   CAN/FD/FlexRay/Ethernet
        +------------------------+-------------------------+
                                 |
                 +---------------v----------------+
                 | software-controlled pin routing|
                 | low-speed/HV + HS differential|
                 +---------------+----------------+
                                 |
                           J1962 / OBD-II
```

`*` CAN XL may be main-board or an expansion depending controller availability at schematic freeze.

The **application computer must not be in the critical bit-timing path**. Linux is excellent for storage, networking, UIs, APIs, databases, and analysis; it is not the correct place to guarantee microsecond/sub-microsecond bus timing.

## 4. Universal electrical rule

A single "0–24 V arbitrary driver" is useful but **cannot replace dedicated automotive PHYs**.

Fast differential networks depend on controlled differential impedance, common-mode range, receiver thresholds, edge shaping, termination, EMC behavior, and timing. Therefore use two routing fabrics:

### Low-speed / high-voltage routing domain
For:
- K-Line / L-Line;
- LIN;
- J1850 PWM/VPW;
- SWCAN where topology allows;
- Chrysler SCI / GM UART / ALDL-class legacy serial;
- arbitrary legacy single-ended signaling;
- analog voltage measurement;
- programmable pull-up/pull-down;
- programmable 0–24 V-class drive;
- programming voltage.

### High-speed differential routing domain
For:
- Classical CAN;
- CAN FD;
- CAN XL if included;
- ISO 11898-3 fault-tolerant CAN;
- FlexRay;
- diagnostic Ethernet / 100BASE-TX;
- 10BASE-T1S / 100BASE-T1 / 1000BASE-T1 where included.

High-speed routing must be selected and laid out from **AC/S-parameter/signal-integrity requirements**, not DC switch ratings.

## 5. Safe default state

On reset, brownout, watchdog timeout, application-computer crash, or incomplete configuration:

- all discretionary OBD signal pins are **high impedance**;
- all bus transmitters are disabled;
- programmable voltage outputs are off;
- switchable termination is off;
- pin-routing switches are open;
- the device enters passive sensing before active driving;
- the real-time controller remains able to place the whole front end back into passive mode;
- a hardware TX-disable / emergency disconnect should be available independent of the Linux/SBC layer.

## 6. Documents in this design package

- [`architecture.md`](architecture.md) — bus/PHY coverage and system partition
- [`pin-capability-matrix.md`](pin-capability-matrix.md) — J1962 pin-by-pin electrical requirements
- [`design-review.md`](design-review.md) — r/CarHacking review + academic mock review
- [`design-freeze-checklist.md`](design-freeze-checklist.md) — pre-layout gates and validation plan
- [`research-sources.md`](research-sources.md) — traceable source list

## 7. Bottom line

The target is not "a better scan tool." It is a **software-defined vehicle communication interface** whose electrical front end is broad enough that future work is usually limited by software, protocol knowledge, vehicle topology, or authorization rather than by a missing transceiver, missing voltage range, missing pin route, or inadequate timing hardware.
