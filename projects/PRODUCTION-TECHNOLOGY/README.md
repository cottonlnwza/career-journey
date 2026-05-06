# Production Technology — Combat Robot

## My Role

- **Team Leader** — led the full robot design from concept to completion
- System Architecture & Board Layout Planning
- Sensor Selection & Placement Design
- All System Diagrams (wiring, power distribution, control flow)
- Embedded Software Development (ESP32 + Arduino framework)

---

## Overview

A combat robot built as a Year 2 coursework project for the Production Technology subject.

The robot uses a **3-wheel Omni drive** for omnidirectional movement, a 2-axis arm system (X and Y axes) for attack positioning, and a servo-controlled weapon head. Control is handled wirelessly via a **PS5 controller** over Bluetooth, connected directly to an ESP32.

As team leader, I was responsible for the overall design — deciding where every board, sensor, and wire would go — and for drawing all system diagrams used during development. I also wrote the entire embedded control software.

---

## Development Process

### 1. System Design & Hardware Planning

Before building, I designed the full system layout:

- Planned board placement within the robot chassis to minimize cable length and EMI
- Selected sensors suited to each task (limit switches for X-axis homing)
- Designed all wiring and power distribution diagrams
- Chose ESP32 as the main controller for its native Bluetooth support

**Why ESP32 + ps5Controller library instead of a separate receiver:**  
Direct Bluetooth pairing with the PS5 controller removes the need for a separate RF receiver module. The MAC address of the controller is hardcoded, so only the team's controller can connect.

### 2. Drive System — 3-Wheel Omni

- Drive uses **3 omnidirectional wheels** in a triangular configuration
- Wheel speeds calculated using Omni3 kinematics:
  - Front wheel: `-w + x`
  - Right wheel: `-w - 0.5x - 0.866y`
  - Left wheel:  `-w - 0.5x + 0.866y`
- **Slow mode** (L2): halves all motor outputs for precision movement
- **Analog swap** (Share toggle): swaps left/right stick assignments

### 3. Arm System

**Axis X (horizontal sweep):**
- R1 / L1 to move left/right
- Options button to auto-home (resets to right limit switch position)
- Limit switches (left + right) prevent over-travel — motor stops immediately on contact

**Axis Y (attack thrust):**
- Manual: Triangle (extend) / Cross (retract)
- Semi-auto attack (R2): triggers a timed sequence — extends for 120ms, then retracts for 120ms automatically, no need to hold

**Servo weapon head:**
- Up / Down: incremental rotation (+3°/step at 15ms interval)
- Square: reset to 0°
- Right: snap to 90°
- Left: snap to 180°

### 4. Testing & Debugging

During the testing checklist (documented in code comments):

**Issue:** Servo skipped angles when called too frequently  
**Fix:** Added a 15ms interval guard (`millis()` check) — servo only updates once per interval

**Issue:** Limit switch state uncertain during rapid input  
**Fix:** Configured `INPUT_PULLUP` — HIGH = not triggered, LOW = triggered — added explicit state checks before every motor write

**Issue:** Motor jitter at rest when stick is near center  
**Fix:** `adjust_speed()` function zeroes any value with `|speed| < 10` as a deadband filter

### 5. Result

- **Grade: A**
- The semi-auto attack (SemiAuto_Y) was the most technically satisfying feature — timing the thrust and retract as a non-blocking state machine using `millis()` instead of `delay()` kept the control loop responsive throughout

---

## Personal Reflection

**Hardest part:**  
Planning the board layout. The robot chassis has limited space, and deciding where to mount the ESP32, motor drivers, and limit switch wiring — while keeping everything accessible for debugging — required multiple iterations on paper before touching any hardware.

**What I learned:**
- How to implement non-blocking timed sequences with `millis()` — avoids freezing the control loop like `delay()` would
- How to use limit switches with `INPUT_PULLUP` correctly — the inverted logic (LOW = triggered) is a common source of bugs
- How Omni3 kinematics work in practice and how to normalize wheel speeds to prevent clipping

**Overall:**  
Leading this project taught me that the most important work happens before writing a single line of code. The diagrams and layout plans I drew shaped everything else — code, wiring, and debugging. Getting an A confirmed that the systematic approach paid off. The semi-auto attack feature was something I was particularly proud of designing and implementing independently.

---

## Code

| Module | Path |
|---|---|
| Main Control (ESP32/Arduino) | [code/Code_PREROBOT.ino](code/Code_PREROBOT.ino) |
