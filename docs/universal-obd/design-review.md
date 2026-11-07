# CANOpener Universal — Community and Academic Mock Design Review

## Important note on methodology

The people named below **did not review this CANOpener design and were not contacted**. This is a **mock design review**: their public technical posts or published papers were used as a lens to ask, "What would a reviewer with this demonstrated focus probably challenge in our architecture?"

This avoids inventing endorsements or quotations.

The r/CarHacking contributors below were selected for **high technical relevance to this design**, not because there is an objective way to rank the "smartest" users in the subreddit.

---

# Part A — r/CarHacking review

## Reviewer lens 1 — `u/csselectronics` (Martin, CSS Electronics)

### Public technical signal

In a 2026 r/CarHacking post on CAN reverse engineering, Martin distinguished standardized OBD requests from the much higher-volume proprietary CAN traffic between ECUs, described Python/CAN tooling, and discussed XCP/seed-key use when the authentication method is already known.

Source:
- https://www.reddit.com/r/CarHacking/comments/1ucraus/new_intro_can_bus_reverse_engineering_with_ai/

### Mock review

**Likely challenge:** Do not optimize this as an OBD PID box. The hardware must preserve the raw network data path, timestamp quality, throughput, and metadata needed for later software analysis.

### Change accepted

- Raw frames are first-class data, not an optional debug mode.
- Shared hardware timestamps across channels become P0.
- Local logging must survive high bus loads without silent drops.
- Expose open host APIs usable by Python tooling.
- Maintain a clear separation between physical bus capture and higher-layer OBD/UDS decoding.

---

## Reviewer lens 2 — `u/Martarts` / Matthew KuKanich (CAN Commander)

### Public technical signal

The CAN Commander project emphasizes multi-bus operation, man-in-the-middle routing, replay, DBC work, OBD and direct-wire connections, plus Wi-Fi/Bluetooth. The thread also contains discussion showing why SWCAN should use an appropriate physical layer rather than assuming a normal HS-CAN transceiver can always substitute.

Source:
- https://www.reddit.com/r/CarHacking/comments/186jjz6/i_developed_an_open_source_can_reverse/

### Mock review

**Likely challenge:** "Universal" should mean multiple buses can be open simultaneously, bridged in real time, and observed from both sides. One shared transceiver switched among pins is not enough.

### Change accepted

- Multiple independent CAN-family channels rather than one multiplexed controller.
- Architecture supports true two-sided gateway/MITM laboratory use.
- Per-channel buffering and independent bitrate configuration.
- Direct-wire/breakout attachment is required in addition to OBD.
- Wireless is convenience; deterministic local routing remains on the real-time controller.

---

## Reviewer lens 3 — `u/WestonP`

### Public technical signal

WestonP has repeatedly emphasized physical-layer correctness: K-Line is 12-V UART-like signaling with special initialization and should not be wired to a CAN transceiver. In a 2026 OBD breakout discussion, WestonP also highlighted alternate CAN pairs (3/11 and 12/13), SWCAN on pin 1, independent power control, external power, LEDs, and onboard termination as useful test features.

Sources:
- https://www.reddit.com/r/CarHacking/comments/1h0686x/k_line_arduino_shield/
- https://www.reddit.com/r/CarHacking/comments/1smoos1/obd2_splitter_obdt/

### Mock review

**Likely challenge:** A universal digital protocol engine is worthless if the physical layer is wrong. Also, do not hard-wire OEM discretionary pins.

### Change accepted

- Dedicated K/L-Line/LIN-class PHY.
- Electronic pin-routing matrix.
- Alternate CAN pair support.
- SWCAN dedicated path.
- Software-switchable termination.
- Per-pin test points and external bench power options.
- Passive sensing before any drive.

---

## Reviewer lens 4 — `u/maker_monkey`

### Public technical signal

In the K-Line thread, maker_monkey described monitoring a real scan tool's initialization, then reproducing it, and wrote a sniff mode that records raw high/low transitions with timestamps because initialization timing can be unusual.

Source:
- https://www.reddit.com/r/CarHacking/comments/1h0686x/k_line_arduino_shield/

### Mock review

**Likely challenge:** Protocol controllers alone are not enough. We need a raw electrical timing mode that can observe and reproduce edge sequences not yet understood by software.

### Change accepted

- Raw comparator/edge-capture path on discretionary pins.
- Shared deterministic timestamp clock.
- Programmable edge generation via FPGA/CPLD/PIO-class engine.
- Capture-before-decode workflow.
- Trigger output for oscilloscope/logic-analyzer correlation.

This is one of the most important additions because it lets the hardware investigate an unfamiliar legacy initialization method rather than requiring a new PCB first.

---

## Reviewer lens 5 — `u/zJustzSomebody`

### Public technical signal

In the CAN Commander thread, this contributor described moving from "normal CAN transceiver used as a workaround" to a dedicated NCV7356 SWCAN transceiver, specifically valuing host wake-up/low-current behavior and noting that bit timing and transceiver wiring behavior matter.

Source:
- https://www.reddit.com/r/CarHacking/comments/186jjz6/i_developed_an_open_source_can_reverse/

### Mock review

**Likely challenge:** Vehicle-installed hardware has to behave like automotive hardware while the car sleeps. Correct wake behavior, quiescent current, and a proper physical layer matter as much as feature count.

### Change accepted

- Dedicated SWCAN/J2411 path rather than treating it as a CAN-H hack.
- Always-on supervisor with very low sleep current.
- Bus/ignition wake capability.
- Application computer hard power gating.
- Bit-timing validation per channel.
- No assumption that "same voltage" means "same physical layer."

---

## Additional subreddit findings that changed the design

### A. Add ISO 11898-3 fault-tolerant CAN

A 2026 CANipulator discussion explicitly called out low-speed fault-tolerant CAN, including early Mercedes interior CAN-B use.

Source:
- https://www.reddit.com/r/CarHacking/comments/1u1zt6f/i_created_this_black_little_box_for_car_can/

**Decision:** Add a dedicated ISO 11898-3-capable path.

### B. Power protection is not optional

A 2026 OBD breakout discussion includes a report of modules/fuses being damaged by an OBD dongle short.

Source:
- https://www.reddit.com/r/CarHacking/comments/1smoos1/obd2_splitter_obdt/

**Decision:** automotive power protection, per-path current limiting, fail-open switching, and hardware TX disable are P0.

### C. J2534 reliability is a product feature

Recent r/CarHacking J2534 discussions repeatedly emphasize driver/interface stability, buffering, and reliable long programming sessions over raw feature count.

Sources:
- https://www.reddit.com/r/CarHacking/comments/1whouc2/anyone_else_had_trouble_with_j2534_interfaces/
- https://www.reddit.com/r/CarHacking/comments/1sfh3qu/i_trust_the_car_more_than_the_j2534_interface/
- https://www.reddit.com/r/CarHacking/comments/1w0chqy/what_j2534_passthru_device_do_you_guys_use/

**Decision:** Treat USB/host protocol, buffering, watchdog behavior, firmware update/recovery, and driver/API quality as design requirements — not "software later."

### D. OBD may expose only a gateway

Recent threads reinforce that newer vehicles can place a secure/diagnostic gateway between the J1962 connector and internal networks.

Sources:
- https://www.reddit.com/r/CarHacking/comments/1ldd6jb/chryslerfcastellantis_secure_gateway_module_sgm/
- https://www.reddit.com/r/CarHacking/comments/1egkicj/two_general_questions_about_obdii_spec/

**Decision:** keep a direct-wire/breakout mode. Do not advertise OBD access as equivalent to physical access to every internal bus.

---

# Part B — academic mock review

Again, the researchers below did not review our board. Their published work is being used as a technical design lens.

## Academic lens 1 — Karl Koscher et al.

Paper:
- **Experimental Security Analysis of a Modern Automobile**
- IEEE Symposium on Security and Privacy, 2010
- DOI: https://doi.org/10.1109/SP.2010.34

### What the paper contributes to our review

The work treats a modern vehicle as a network of many ECUs rather than a single engine-computer endpoint and demonstrates the importance of direct access to in-vehicle networks.

### Mock review

**Likely challenge:** Do not conflate "OBD diagnostic access" with "the vehicle network." Build for raw buses, multiple channels, gateway topology, and laboratory-safe observation.

### Change accepted

- Multi-bus simultaneous capture.
- Direct-wire breakout mode.
- Passive/read-only startup mode.
- Hardware TX disable.
- Explicit topology discovery/recording in software.

---

## Academic lens 2 — Mert D. Pesé et al.

Paper:
- **LibreCAN: Automated CAN Message Translator**
- ACM CCS 2019
- DOI: https://doi.org/10.1145/3319535.3363190

### What the paper contributes

LibreCAN focuses on extracting semantics from proprietary CAN traffic beyond standardized OBD and demonstrates why high-fidelity raw data matters for automated analysis.

### Mock review

**Likely challenge:** Data quality and synchronization are part of hardware capability. A universal interface that drops frames or timestamps channels inconsistently undermines later decoding.

### Change accepted

- Shared timestamp clock across all channels.
- Overflow/drop counters.
- High-throughput local logging.
- Raw + decoded data stored together.
- External trigger/PPS/PTP hooks considered.

---

## Academic lens 3 — Jin Ho Kim, Jae Wook Jeon et al.

Paper:
- **Gateway Framework for In-Vehicle Networks Based on CAN, FlexRay, and Ethernet**
- IEEE Transactions on Vehicular Technology, 2015
- DOI: https://doi.org/10.1109/TVT.2014.2371470

### What the paper contributes

The paper emphasizes a reusable/configurable gateway across heterogeneous buses, including diagnostic routing, network management, dynamic routing, multiple routing configurations, and verification.

### Mock review

**Likely challenge:** Separate the routing/gateway architecture from individual PHY implementations. Make configuration declarative and testable instead of hard-coded.

### Change accepted

- Hardware routing table controlled by the real-time MCU.
- Versioned machine-readable pin/PHY configuration.
- Automated self-test/loopback modes.
- Reusable channel abstraction.
- Verification fixtures and tests required with every routing configuration.

---

## Academic lens 4 — Trong-Yen Lee et al.

Paper:
- **Design of a FlexRay/Ethernet Gateway and Security Mechanism for In-Vehicle Networks**
- Sensors, 2020
- DOI: https://doi.org/10.3390/s20030641

### What the paper contributes

The design partitions FlexRay/Ethernet gateway functions across FPGA and processor logic and evaluates low deterministic processing latency.

### Mock review

**Likely challenge:** Do not put time-critical gateway behavior in the Pi/Linux path.

### Change accepted

- Real-time MCU/FPGA owns bridging and timing.
- Application computer is control plane, not data-plane timing engine.
- Deterministic channel-to-channel forwarding is a benchmark.
- FlexRay A/B support uses a real FlexRay controller/PHY rather than software bit-banging.

---

## Academic lens 5 — Daniel Thiele, Johannes Schlatow, Philip Axer, Rolf Ernst

Paper:
- **Formal timing analysis of CAN-to-Ethernet gateway strategies in automotive networks**
- Real-Time Systems, 2016
- DOI: https://doi.org/10.1007/s11241-015-9243-y

### What the paper contributes

The work shows that buffering/multiplexing strategy at heterogeneous gateways changes end-to-end latency and derives timing bounds.

### Mock review

**Likely challenge:** "Fast enough" is not a specification. Characterize worst-case latency, buffer behavior, queue discipline, and loss under simultaneous bus load.

### Change accepted

- Per-channel hardware queues.
- Explicit queue/forwarding policies.
- Worst-case latency test plan.
- No silent loss.
- High-water/overflow telemetry.
- Linux host stalls must not break real-time pass-through.

---

# Part C — items we had overlooked or underweighted

The review changed the architecture in these concrete ways:

| Item | Before review | After review |
|---|---|---|
| ISO 11898-3 fault-tolerant CAN | Missing | P0 protocol |
| Raw edge capture/generation | Nice-to-have | P0 for unknown legacy signaling |
| Shared cross-channel timebase | Mentioned | P0 |
| J2534 programmable-voltage details | General 0–24 V concept | Dedicated controlled subsystem |
| Chrysler SCI / GM UART / ALDL-class legacy serial | Under-specified | Explicit legacy serial engine |
| J2534 API reliability/buffering | "software later" | Product requirement |
| ISO 22900-2 D-PDU API | Missing | Software architecture requirement |
| 100BASE-TX diagnostic Ethernet | Underweighted vs BASE-T1 | P0 Ethernet mode |
| Diagnostic Ethernet activation resistor/line behavior | Missing | Add programmable activation/detection network |
| 10BASE-T1S | Missing | Future-proof PHY/expansion target |
| CAN XL | Missing from initial M2-derived list | Future-proof main/expansion target |
| Direct internal-bus breakout | Mentioned | Required |
| Hardware TX kill/fail-open | Mentioned | P0 |
| Sleep/wake/quiescent current | Mentioned | P0 |
| Scope/test access | Mentioned | P0 validation feature |
| High-speed routing signal integrity | Under-specified | Separate HS matrix + eye/TDR validation |

---

# Part D — consolidated mock-review verdict

The architecture is strong **only if we resist the temptation to equate universality with one programmable voltage pin driver**.

The optimized direction is:

1. dedicated PHYs for established fast/specialized networks;
2. universal protected analog/HV capability for low-speed and unknown signaling;
3. a real-time controller + programmable timing engine;
4. a shared timestamp domain;
5. electronic pin routing;
6. a safe, passive startup state;
7. robust power/wake behavior;
8. open high-bandwidth host protocol with J2534/D-PDU compatibility;
9. breakout/bench expansion for networks not physically available at the OBD connector;
10. signal-integrity validation before a PCB is released.

The highest-risk technical item is now the **universal high-speed pin-routing fabric**. It should be prototyped and measured before the rest of the Universal PCB is locked.
