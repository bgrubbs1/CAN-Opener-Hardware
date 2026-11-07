# CANOpener Universal — Research Sources

This is the working source list used for the 2026-09-20 design review.

## r/CarHacking / community

1. CSS Electronics / Martin — CAN reverse engineering with AI; raw CAN vs OBD distinction; Python/CAN workflow  
   https://www.reddit.com/r/CarHacking/comments/1ucraus/new_intro_can_bus_reverse_engineering_with_ai/

2. Matthew KuKanich (`u/Martarts`) — CAN Commander, multi-bus/MITM/DBC/Wi-Fi/Bluetooth design  
   https://www.reddit.com/r/CarHacking/comments/186jjz6/i_developed_an_open_source_can_reverse/

3. K-Line Arduino shield discussion — physical-layer correctness and raw init timing (`u/WestonP`, `u/maker_monkey`)  
   https://www.reddit.com/r/CarHacking/comments/1h0686x/k_line_arduino_shield/

4. OBD2 splitter/breakout discussion — alternate pins, power control, termination, probing, power-protection concerns  
   https://www.reddit.com/r/CarHacking/comments/1smoos1/obd2_splitter_obdt/

5. CANipulator v2 discussion — ISO 11898-3 fault-tolerant CAN request/use case  
   https://www.reddit.com/r/CarHacking/comments/1u1zt6f/i_created_this_black_little_box_for_car_can/

6. Recent J2534 reliability discussion  
   https://www.reddit.com/r/CarHacking/comments/1whouc2/anyone_else_had_trouble_with_j2534_interfaces/

7. J2534 reliability vs feature count discussion  
   https://www.reddit.com/r/CarHacking/comments/1sfh3qu/i_trust_the_car_more_than_the_j2534_interface/

8. J2534 interface recommendations  
   https://www.reddit.com/r/CarHacking/comments/1w0chqy/what_j2534_passthru_device_do_you_guys_use/

9. Stellantis/FCA secure gateway discussion — OBD topology/gateway limits  
   https://www.reddit.com/r/CarHacking/comments/1ldd6jb/chryslerfcastellantis_secure_gateway_module_sgm/

10. OBD-II bus/gateway discussion — not every internal bus is exposed  
    https://www.reddit.com/r/CarHacking/comments/1egkicj/two_general_questions_about_obdii_spec/

11. J1850 VPW <-> CAN bridge; example of dedicated deterministic legacy-bus engine  
    https://www.reddit.com/r/CarHacking/comments/1w0cjlp/j1850vpw_can_bus_bridge/

12. J1850 / ALDL distinction discussion  
    https://www.reddit.com/r/CarHacking/comments/111tjt1/gm_j1850_input_signal_conversion/

## Peer-reviewed / academic

1. Karl Koscher et al., *Experimental Security Analysis of a Modern Automobile*, IEEE Symposium on Security and Privacy, 2010.  
   DOI: https://doi.org/10.1109/SP.2010.34

2. Mert D. Pesé et al., *LibreCAN: Automated CAN Message Translator*, ACM CCS, 2019.  
   DOI: https://doi.org/10.1145/3319535.3363190

3. Jin Ho Kim, Suk-Hyun Seo, Nguyen Tien Hai, Bo Mu Cheon, Young Seo Lee, Jae Wook Jeon, *Gateway Framework for In-Vehicle Networks Based on CAN, FlexRay, and Ethernet*, IEEE Transactions on Vehicular Technology, 2015.  
   DOI: https://doi.org/10.1109/TVT.2014.2371470

4. Trong-Yen Lee, I-An Lin, Ren-Hong Liao, *Design of a FlexRay/Ethernet Gateway and Security Mechanism for In-Vehicle Networks*, Sensors, 2020.  
   DOI: https://doi.org/10.3390/s20030641

5. Daniel Thiele, Johannes Schlatow, Philip Axer, Rolf Ernst, *Formal timing analysis of CAN-to-Ethernet gateway strategies in automotive networks*, Real-Time Systems, 2016.  
   DOI: https://doi.org/10.1007/s11241-015-9243-y

## Standards / implementation references

- SAE J2534-1, Recommended Practice for Pass-Thru Vehicle Programming  
  https://saemobilus.sae.org/standards/j2534-1_5_00-recommended-practice-pass-thru-vehicle-programming

- ISO 22900-2 D-PDU API overview (Softing)  
  https://automotive.softing.com/applications/api-interfaces/d-pdu-api.html

- CAN in Automation — CAN XL  
  https://www2.can-cia.org/canxl

- Microchip — automotive 10BASE-T1S products  
  https://www.microchip.com/en-us/products/high-speed-networking-and-video/ethernet/single-pair-ethernet/10base-t1s

- Microchip — automotive Ethernet portfolio  
  https://www.microchip.com/en-us/products/interface-networking-connectivity/ethernet/automotive-ethernet-products

## Competitive-capability sanity checks

A broad modern pass-thru tool feature set is a useful checklist even when we are not copying its architecture. Current tool documentation commonly includes combinations of:

- multiple CAN/CAN-FD channels;
- SWCAN;
- ISO 11898-3 fault-tolerant CAN;
- J1850;
- K/L-Line;
- Chrysler SCI;
- programmable voltage;
- DoIP;
- legacy serial;
- RP1210/J1708 on heavy-duty products.

The Universal design should be judged against the **union of these physical capabilities**, then add raw programmable timing, electronic pin routing, local compute/storage, and future expansion.
