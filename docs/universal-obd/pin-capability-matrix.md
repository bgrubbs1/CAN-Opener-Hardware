# CANOpener Universal — J1962 Pin Capability Matrix

## 1. Principle

The discretionary J1962 pins should not be permanently assigned to one protocol. Each signal-capable pin should be measurable and, where safe, electronically routable to the appropriate low-speed or high-speed physical layer.

Pins 4, 5, and 16 are special:

- **Pin 4** — chassis ground
- **Pin 5** — signal ground
- **Pin 16** — vehicle battery

These are not arbitrary programmable outputs.

## 2. Per-pin low-speed universal front end

Every discretionary signal pin should have, directly or through a protected switching stage:

- high-impedance voltage measurement;
- approximately 0–30 V measurement range, with automotive transient protection beyond that normal range;
- comparator with programmable or selectable threshold;
- raw edge timestamp capture;
- open-drain/low-side drive;
- high-side/open-source drive where required;
- push-pull drive only through an explicitly enabled current-limited path;
- software-selectable pull-up and pull-down;
- current sensing where practical;
- programmable current limit;
- 0–24 V-class programmable voltage capability for slow/legacy signaling where practical;
- full electrical disconnect/high-Z;
- route to relevant dedicated PHYs.

**All active drive modes must be opt-in. Passive sensing comes first.**

## 3. Pin-by-pin target

| J1962 pin | Standard/common use | Universal target |
|---:|---|---|
| 1 | Manufacturer discretionary; often SWCAN in some GM applications | HV universal I/O, SWCAN route, legacy serial route, optional HS route |
| 2 | J1850 Bus+ | J1850 PWM/VPW route, HV universal I/O |
| 3 | Manufacturer discretionary; alternate CAN or diagnostic Ethernet on some vehicles | HV universal I/O + high-speed differential matrix |
| 4 | Chassis ground | Protected ground/reference only |
| 5 | Signal ground | Protected signal ground/reference + sensing |
| 6 | CAN-H / ISO 15765 | HS CAN/CAN-FD/CAN-XL route; optional programming-voltage route where supported |
| 7 | ISO 9141/14230 K-Line | K/L/LIN-class PHY + HV universal I/O |
| 8 | Manufacturer discretionary / Ethernet activation on some vehicles | HV universal I/O, programmable resistor/activation network |
| 9 | Manufacturer discretionary; legacy GM UART/ALDL in some tooling | HV universal I/O, legacy serial route, optional programming-voltage route |
| 10 | J1850 Bus- | J1850 PWM route + HV universal I/O |
| 11 | Manufacturer discretionary; alternate CAN / Ethernet pair | HV universal I/O + high-speed differential matrix + optional programming voltage |
| 12 | Manufacturer discretionary; alternate CAN / Ethernet pair | HV universal I/O + high-speed differential matrix + optional programming voltage |
| 13 | Manufacturer discretionary; alternate CAN / Ethernet pair | HV universal I/O + high-speed differential matrix + optional programming voltage |
| 14 | CAN-L / ISO 15765 | HS CAN/CAN-FD/CAN-XL route + optional programming voltage |
| 15 | ISO 9141/14230 L-Line | K/L PHY, HV universal I/O, controlled short-to-ground function where API compatibility requires it |
| 16 | Battery positive | Protected power input and voltage measurement only |

The table describes **capability**, not a claim that every protocol is legal/appropriate on every pin.

## 4. Programmable voltage

For maximum service-tool compatibility, provide a dedicated controlled programming-voltage subsystem rather than using a generic GPIO driver.

Design targets:

- approximately 5–20 V standard-compatible range;
- consider wider 0–24 V engineering range if it can be made safe;
- programmable slew;
- voltage readback;
- current measurement;
- programmable current limit;
- hardware overcurrent shutdown;
- hard OFF independent of application computer;
- route only to allowed/configured pins;
- no route can be enabled until the pin has been passively measured.

Legacy J2534 practice specifically uses programmable voltage on several discretionary pins. The exact supported pin set should be frozen against the J2534 revision(s) we claim to support.

## 5. Passive discovery mode

Before making an active connection, the device should be able to:

1. measure DC voltage on all discretionary pins;
2. detect likely differential pairs from correlated activity;
3. measure approximate bus termination where it can be done without disturbing the vehicle;
4. capture raw edge timing;
5. identify idle level/polarity;
6. estimate candidate baud/bit rate;
7. refuse an unsafe routing/drive configuration.

The host should show a **pin map discovered from the actual vehicle**, not only a hard-coded "pin 6/14 = CAN" assumption.

## 6. High-speed routing rules

High-speed pair selection must preserve:

- differential impedance;
- pair symmetry;
- low insertion loss;
- low return loss;
- low added capacitance;
- low stub length;
- common-mode range;
- EMC protection.

The final design should include S-parameter/eye/TDR acceptance tests for:

- CAN FD maximum intended rate;
- CAN XL if included;
- FlexRay 10 Mbps;
- 100BASE-TX diagnostic Ethernet;
- 10BASE-T1S if main-board;
- 100/1000BASE-T1 if main-board.

If the universal matrix cannot pass those tests in the available OBD form factor, move the fastest PHYs to a controlled external remap/HS pod rather than compromising every channel.

## 7. Termination

Each differential CAN-family channel should offer:

- software-switchable 120-ohm termination;
- ability to leave termination completely off;
- readback/status if practical.

Do not automatically add termination to an already terminated in-vehicle bus.

For other protocols use protocol-appropriate termination/bias, not a generic CAN resistor.

## 8. Test access

Community review strongly supports keeping the device easy to probe.

Provide:

- labeled test pads for every J1962 pin;
- test pads for each PHY-side TX/RX signal;
- timestamp/trigger output;
- ground spring/probe points;
- optional compact breakout accessory.

A universal interface that cannot be scoped easily will be painful to validate.

## 9. Protection/failure requirements

Per signal path:

- automotive ESD protection;
- transient/overvoltage tolerance appropriate to vehicle wiring;
- current limiting where active drive is possible;
- reverse-current protection;
- stuck-dominant/stuck-active detection where feasible;
- hardware TX disable;
- fail-open routing switch behavior where feasible.

The board must be designed so a single MCU boot glitch cannot place an arbitrary voltage onto an unknown bus.
