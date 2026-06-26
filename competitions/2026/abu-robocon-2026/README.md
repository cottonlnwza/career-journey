# ABU Robocon 2026 — Kung Fu Quest

## My Role

- **Embedded Software Developer & Wiring — Robot R1 (Manual + Semi-Auto)**
- Inherited ROS2 package infrastructure from a Year 4 senior; wrote all game logic on top
- Wrote zone-based Behavior Tree nodes covering all 3 competition zones (manual mode)
- Built the UDP joystick receiver node (Pi → LAN → robot PC)
- Responsible for all physical wiring on Robot R1

**Team:** ~10 people across 3 departments — Mechanical (structure), Coding (software), Wiring (electronics).
All 3 departments collaborated on system design before splitting into individual roles.

---

## Overview

**TPA Robot Cup 2026 / ABU Robocon 2026 — "Kung Fu Quest"**
Hosted at Queen Elizabeth Stadium, Wan Chai, Hong Kong. Contest date: 23 August 2026.

The theme is a Kung Fu martial arts journey. Each team fields two robots:
- **R1** (Manual/Semi-Auto) — assembles weapons, collects Kung Fu Scrolls (KFS), and plays Tic-Tac-Toe in the Arena
- **R2** (Autonomous) — collects scrolls independently; gets lifted by R1 to place scrolls on the top row

The field is divided into three zones that map directly to the robot's control modes:

| Zone | Area | Objective |
|------|------|-----------|
| Zone 1 | Martial Club (MC) | Assemble weapons using the staff arm |
| Zone 2 | Meihua Forest (MF) | Collect Kung Fu Scrolls (KFS) with the KFS arm |
| Zone 3 | Arena | Place KFS on the 3×3 Tic-Tac-Toe rack (10–80 pts/slot), release weapons |

**National qualifier result: Passed — Top 12 teams in Thailand**

---

## Development Process

### 1. System Architecture — Solving the 2025 Signal Problem

In 2025, the PS5 controller disconnected mid-match due to heavy 2.4GHz Bluetooth interference in the arena. For 2026, we eliminated wireless Bluetooth entirely and built a new communication chain:

```
PS5 Controller (USB)
  → Raspberry Pi  [joy_main_v2.py — reads via evdev, sends UDP/LAN]
  → Router / LAN (UDP port 12345, JSON payload with sequence number)
  → Mini PC  [Ubuntu 24.04 + ROS2 Jazzy]
      → get_joy_from_network.py  [UDP → /joy_controller_value topic]
      → Behavior Tree (py_trees_ros, 20Hz)
      → r1_micro_ros_hardware  [ROS2 Control hardware interface]
  → Teensy 4.1  [Micro-ROS Serial /dev/ttyACM0 @ 115200]
      → Wheel PID control (4× mecanum motors, 30ms loop)
      → Arm KFS PID control
      → Serial5 UART @ 115200
  → ESP32 v2  [actuator bus — write-only]
      → Pneumatic solenoids (4× weapon + 1× KFS gripper)
      → Conveyor motor
      → NeoPixel LEDs (zone color indicator)
```

**Hardware on robot:**

| Component | Role |
|-----------|------|
| Mini PC (Ubuntu 24.04) | ROS2 host, behavior tree, joystick RX, LIDAR processing |
| Teensy 4.1 | Wheel PID, motor PWM, IMU read, arm KFS motor control |
| ESP32 v2 | Pneumatics, conveyor, NeoPixel LEDs — downstream-only bus |
| BNO08x (SPI) | IMU — quaternion at ~50Hz for heading hold |
| YDLidar (USB) | 360° LaserScan for object detection |
| 4× Mecanum wheels | Omnidirectional drive (wheel_radius=0.05m, base=0.70m, sep=0.78m) |
| Pneumatic solenoids ×4 | Weapon gripper/lift (L and R sides) |

### 2. Behavior Tree — Zone-Based Game Logic

The core of R1's software is a **Behavior Tree** built with `py_trees_ros`, ticking at ~20Hz.

The tree selects between three modes in priority order:

```
Root Sequence
└── GetJoyValue (reads UDP joystick → blackboard)
└── Mode Selector
    ├── [Priority 1] E-Stop Sequence
    │     → Immediately publishes cmd_vel=0, arm hold
    │     → Triggers when: E-stop button pressed OR joystick disconnects (>500ms timeout)
    │     → Hardware-level backup: Teensy pin 34 cuts all PWM instantly
    ├── [Priority 2] Semi-Auto Mode (Zone-aware)
    │     → Zone 1: staff arm auto-control + follow R2 [planned]
    │     → Zone 2: KFS arm auto-aim via LIDAR [planned]
    │     → Zone 3: auto weapon sequence + lift R2 [planned]
    └── [Priority 3] Manual Mode (Zone-aware) ← FULLY IMPLEMENTED
          ├── Zone 1: weapon gripper (L/R) + staff arm (J1/J2 position)
          ├── Zone 2: KFS arm (J1/J2) + KFS gripper toggle + conveyor direction
          └── Zone 3: weapon release (L/R) + KFS placement arm
```

**Zone switching:** Operator uses D-pad to switch zones mid-match (Left=Zone1, Up=Zone2, Right=Zone3). Zone selection changes which button mappings are active — button presses in Zone 2 control the KFS arm, the same buttons in Zone 3 control the weapon release. This prevents accidental cross-zone commands.

**Blackboard pattern:** All zone nodes share state through py_trees blackboard (shared memory). Joy values, zone ID, E-stop flag, and semi-auto flag are all written once per BT tick by `GetJoyValue` and read by downstream nodes.

### 3. Drive System — Mecanum with IMU Heading Hold

`MecanumDrive` BT node publishes `TwistStamped` to `mecanum_drive_controller/cmd_vel`:

```
cmd_vel (TwistStamped: linear.x, linear.y, angular.z)
  → C++ MecanumDriveController (ros2_control plugin, ~50Hz)
      Inverse kinematics:
        ω_FL = (1/R) × (vx - vy - ωz×(L+W))
        ω_FR = (1/R) × (vx + vy + ωz×(L+W))
        ω_BL = (1/R) × (vx + vy - ωz×(L+W))
        ω_BR = (1/R) × (vx - vy + ωz×(L+W))
  → R1MicroRosHardwareInterface → /teensy/wheel_cmd
  → Teensy 4.1: per-wheel velocity PID (kp=0.2, ki=0.1, kd=0.2, PPR=1000, 30ms)
  → Motor PWM output → Wheel encoders → /teensy/wheel_state feedback
```

In semi-auto mode (planned), the BT reads `/Imu_robot` (BNO08x quaternion via Teensy) to snap heading to 0°/90°/180°/270° automatically using a PID heading controller.

### 4. Actuator Control — Arm, Weapon, Pneumatics

**KFS Arm (2-joint):**
- J1 = Y-axis (horizontal sweep), J2 = Z-axis (height)
- Arm PID on Teensy: kp=15.2, ki=0.0, kd=7.3
- Commands published as `/arm_kfs_cmd [arm_y, arm_z, kfs_gripper, conveyor]`
- KFS gripper and conveyor direction packed into ESP32 UART command bytes 4 and 5

**Weapon / Pneumatics:**
- Left and right weapon sides each have: gripper (hold staff) + lift (raise staff)
- `weapon_control.py` runs a non-blocking timed state machine (using `time.monotonic()`):
  - **Keep sequence:** gripper → wait 1.0s → lift → wait 1.5s → lock
  - **Release sequence:** lower lift → wait → open gripper → standby
- Zone indicator: `/r1_current_zone` → Teensy → NeoPixel color (Zone1=Red, Zone2=Green, Zone3=Blue)

**LIDAR Object Detection:**
- `lidar_object_detector.py` clusters YDLidar `/scan` data into objects
- Detects `target_box` in -20° to -160° sector (weapon box zone)
- Detects `target_r2` in 40° to 140° sector (R2 robot tracking)
- Publishes TF transforms for detected targets → available for semi-auto integration

### 5. Debugging — Key Issues Solved

**Issue: UDP data lag under heavy logging**
Printing debug output on every received packet (20Hz) caused the UDP send loop to stall.
**Fix:** Throttled all logger calls to once per second using `time.monotonic()` interval checks. Packet drop detection via sequence number jumps logs only on anomaly.

**Issue: Zone switching button conflicts**
Early versions had all button mappings active globally — Triangle in Zone 2 triggered Zone 1 arm behavior accidentally.
**Fix:** BT Selector ensures only one zone node runs per tick. Button mappings are fully isolated inside each zone node class.

**Issue: IMU fails to initialize on cold boot**
BNO08x SPI occasionally fails if Teensy communicates too early after power-on.
**Fix (workaround):** Power-cycle Teensy, wait 3s before launch. Permanent fix: add 500ms delay in firmware before BNO08x init.

**Issue: Micro-ROS disconnect after PC sleep**
Teensy loses DDS bridge connection when PC suspends; manual agent restart required.
**Fix (procedure):** Kill micro_ros_agent → restart → wait 5-10s for Teensy reconnect.

### 6. Arduino / Firmware Code

**Teensy 4.1 (`r1_teensy_v2`):** Runs the real-time control loop:
- Micro-ROS client subscribes to `/teensy/wheel_cmd`, `/arm_kfs_cmd`, `/weapon_pos`, `/r1_current_zone`
- Micro-ROS publishes `/teensy/wheel_state` (11 values: cmd, velocity, arm state, power) and `/Imu_robot`
- Executes 4-wheel velocity PID at 30ms, arm KFS PID, BNO08x IMU read at ~50Hz
- Sends 8-byte UART command to ESP32 every 40ms: `[weapon_R_gripper, weapon_R_lift, weapon_L_gripper, weapon_L_lift, kfs_gripper, conveyor, LED_lo, LED_hi]`
- Hardware E-stop: pin 34 LOW → all PWM immediately zero (no software path required)

**ESP32 v2 (`esp_v2`):** Peripheral actuator bus:
- Receives 8-byte comma-separated UART from Teensy @ 115200
- Drives pneumatic solenoid valves (4×), conveyor motor, NeoPixel LED strips
- Write-only — no feedback path to Teensy or PC

### 7. Competition Result

- **National qualifier: Passed — Top 12 teams in Thailand**
- Competition date: 23 August 2026, Queen Elizabeth Stadium, Hong Kong

---

## Personal Reflection

**Hardest part:**
Team management across three departments. This competition was significantly harder than 2025 — the robot has three distinct subsystems (drive, KFS arm, weapon + pneumatics) all developed in parallel by different people. Mechanical, coding, and wiring teams had to constantly sync on design decisions. Unlike 2025 where I owned one robot solo, here I had to coordinate while also building.

**What I learned differently from 2025:**
In 2025 I wrote every line of code myself. In 2026 I inherited a running ROS2 codebase from a Year 4 senior and had to read, understand, and extend it without breaking what already worked. That forced me to learn ROS2 not from tutorials but by reading production code — understanding topics, the blackboard pattern, hardware interfaces, and launch files all in context.

The practical ROS2 knowledge I built in one month of building is the foundation I'll deepen in 2027. The plan is to go back and study ROS2 properly — now that I know what the system actually looks like from the inside.

**Overall:**
Proud of the architecture we shipped — a clean zone-based Behavior Tree with full manual control, a robust LAN+UDP communication chain that replaced the failed Bluetooth approach from 2025, and a codebase structured well enough that the 2027 team can plug in semi-auto features without rewiring everything.

---

## Images

> *(Add images to the `images/` folder and link them here)*

| Description | File |
|-------------|------|
| Team photo | `images/team.jpg` |
| Robot R1 full view | `images/robot_r1.jpg` |
| Homing / setup procedure | `images/homing_setup.jpg` |
| Robot running / testing | `images/testing.jpg` |
| Competition at arena | `images/competition.jpg` |

---

## Code

Full ROS2 control stack (Python + C++):
**[EEzakyn/R1_ABU_ROBOCON_2026 — branch: main_v2](https://github.com/EEzakyn/R1_ABU_ROBOCON_2026/tree/main_v2)**

| Module | Description |
|--------|-------------|
| `src/r1_bt/r1_bt/main_bt.py` | Behavior Tree root — E-Stop / Semi-Auto / Manual mode selection |
| `src/r1_bt/r1_bt/manual_zone_1.py` | Zone 1: staff arm + weapon gripper control |
| `src/r1_bt/r1_bt/manual_zone_2.py` | Zone 2: KFS arm + gripper toggle + conveyor control |
| `src/r1_bt/r1_bt/manual_zone_3.py` | Zone 3: weapon release + KFS placement arm |
| `src/r1_bt/r1_bt/base_mecanum_drive.py` | Mecanum drive with IMU heading hold PID |
| `src/r1_upper_base_control_py/.../get_joy_from_network.py` | UDP receiver → ROS2 Joy topic (packet drop detection, ACK) |
| `src/r1_upper_base_control_py/.../weapon_control.py` | Pneumatic state machine (keep/release sequences) |
| `src/r1_upper_base_control_py/.../lidar_object_detector.py` | YDLidar cluster detection for box and R2 robot |
| `src/r1_upper_base_control_py/.../arm_kfs_control.py` | Arm KFS position → JointState publisher |
| `src/r1_hardware/src/r1_micro_ros_hardware.cpp` | ROS2 Control hardware bridge → Teensy Micro-ROS |
| `src/mecanum_drive_controller/` | Custom C++ ros2_control mecanum kinematics plugin |
| `src/gui_dashboard/gui_dashboard/app_v3.py` | Streamlit web dashboard — IMU monitor, init commands |
| `joy_controller_code/joy_main_v2.py` | Raspberry Pi side — reads PS5 via evdev, sends UDP |

Firmware (Arduino/Teensy):

| Module | Description |
|--------|-------------|
| [arduino_code/r1_teensy_v2/r1_teensy_v2.ino](code/Draft1_robot/Robot-R1/) | Teensy 4.1 — wheel PID, arm KFS, IMU, UART→ESP32, Micro-ROS |
| [arduino_code/esp_v2/esp_v2.ino](code/Draft1_robot/) | ESP32 v2 — pneumatics, conveyor, NeoPixel LEDs |

Early prototype (before switching to Micro-ROS + LAN architecture):

| Module | Description |
|--------|-------------|
| [code/Draft1_robot/Robot-R1/Main_ESP32_Trans.ino](code/Draft1_robot/Robot-R1/Main_ESP32_Trans.ino) | Draft: ESP32 reads PS5 via Bluetooth, sends Serial CSV to Mega |
| [code/Draft1_robot/Robot-R1/Main_Mega_R1_Receive.ino](code/Draft1_robot/Robot-R1/Main_Mega_R1_Receive.ino) | Draft: Arduino Mega — mecanum drive + rack + gripper |
| [code/Draft1_robot/Robot-R2-Auto/Main_GIGAR1_R2_Auto.ino](code/Draft1_robot/Robot-R2-Auto/Main_GIGAR1_R2_Auto.ino) | Draft: R2 autonomous timed sequence |
