# FPGA Pong Game

**Course:** CPE222 — Digital Systems Design  
**Platform:** Basys 3 Artix-7 FPGA  
**Language:** Verilog  
**Tools:** Vivado  
**Demo:** [YouTube — นำเสนอ CPE222 ponggame](https://www.youtube.com/watch?v=Is-U1CZ4i60)

---

## Role

**Team size:** 4 members  
**My responsibilities:** Workflow design and full Verilog programming pipeline

Executed the complete Vivado FPGA design flow:

1. **RTL Design** — wrote all Verilog modules (VGA controller, FSM, clock divider, input handler)
2. **Behavioral Simulation** — verified logic before hardware implementation
3. **Synthesis** — compiled RTL into gate-level netlist targeting Artix-7
4. **Implementation** — place & route on FPGA fabric with timing constraints
5. **Bitstream Generation** — generated `.bit` file for device programming
6. **Hardware Verification** — programmed Basys 3 and validated on physical board

---

## Overview

Implemented a real-time Pong game running entirely on an FPGA — no CPU, no OS, pure digital logic in Verilog. Video output via VGA at 640×480 @ 60Hz.

---

## Technical Implementation

### VGA Controller
- Generates horizontal and vertical sync signals at 640×480 resolution, 60 Hz refresh rate
- Pixel clock at 25 MHz derived from Basys 3's 100 MHz on-board clock using clock divider
- Outputs RGB color signals synchronized to scan position

### Game Logic (FSM)
- Ball movement and direction handled by a Finite State Machine
- Collision detection against walls, paddles, and scoring boundaries
- Score tracking with display on 7-segment display

### Input Handling
- Switch/button debouncing logic for paddle movement
- 16 user switches and push buttons for player control

### Hardware Used
- Basys 3 Artix-7 FPGA board
- VGA port (video output)
- 7-segment display (score)
- User switches / buttons (paddle control)
- On-board LEDs (status)

---

## Key Concepts Demonstrated

- VGA timing and sync signal generation
- Finite State Machine (FSM) design
- Clock domain management (100 MHz → 25 MHz)
- Combinational and sequential logic
- Real-time hardware input/output

---

→ [Back to Projects](../../projects.md)
