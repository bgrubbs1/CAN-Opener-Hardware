# Universal OBD bench and enclosure handoff

The [CANOpener SE hardware specification](../hardware.md) covers the existing dual-CAN design. The Universal OBD work is a separate concept for a configurable vehicle interface. This handoff records the proposed CAN bench prototype and the separate Pocket OBD enclosure study.

## CAN bench prototype

Start with the onboard CAN channel of the [NXP FRDM-A-S32K344](https://www.nxp.com/design/design-center/development-boards-and-designs/FRDM-A-S32K344) on a controlled bench bus. The proposed expansion shield targets four additional CAN FD SIC channels with TJA1463 transceivers. Five simultaneous channels, including the onboard channel, is a design target. Before schematic capture, verify the exact board revision, header pin multiplexing, shared nets, and I/O voltage domains against the schematic and pin configuration. Keep the onboard CAN0 transceiver on its existing controller.

- Give each shield channel a locking CANH/CANL/ground connector, CAN-FD-rated protection, switchable termination shipped open, and access to TXD, RXD, EN, STB_N, CANH, and CANL for measurement.
- Budget a separate regulated supply for the shield. Measure the actual current and rail headroom before considering power from the FRDM header. Leave J1962 pin 16 disconnected on the bench revision. Vehicle power requires a qualified input protection stage.
- With valid supplies, the TJA1463 enters listen-only with `STB_N` high and `EN` low. Use a physical arm latch and per-channel MCU authorization before allowing transmit. Verify the circuit defaults to transmit-disabled at startup and disarms on reset, brownout, or heartbeat loss. [NXP TJA1463 datasheet, sections 7.1.1 and 7.1.2](https://www.nxp.com/docs/en/data-sheet/TJA1463.pdf)
- Use a scope to check enable and TXD transitions during fault injection. A logic analyzer can corroborate digital timing. Keep the setup on a controlled bench until disarm, power protection, and transceiver checks pass.

The shield is a pre-layout concept. Complete the safety and interface-module bench gates before ordering the integrated PCB. An assembly quote needs reviewed fabrication files, a traceable BOM, and pick-and-place data.

## Pocket OBD enclosure

The V2 fit study models a **92 × 76 × 32 mm** main enclosure with a trapezoidal 16-pin J1962 plug reference, USB-C opening, and microSD access. It uses the official Arduino UNO Q STEP model and a reserved interface-board envelope. The nominal vertical gap above the UNO Q envelope is **0.2 mm** in the model. Treat that gap as a tolerance risk until the actual board stack and parts are measured.

Before releasing the enclosure, check the purchased J1962 plug and pin geometry, USB-C cable overmold access, card insertion and removal, fasteners, antenna keepout, and thermal clearances with the actual assembly. The present evidence covers modeled reference envelopes. Physical BOM fit, electrical and thermal validation, and opening the experimental F3D in Fusion remain open.
