# Code — ABU Robocon 2026 R1 Robot

Full source code for Robot R1 (Manual + Semi-Auto), organized by system layer.

The final system runs **ROS2 Jazzy on Ubuntu 24.04** (Mini PC on the robot).
Early prototype used Arduino only — see [`Draft1_robot/`](Draft1_robot/).

---

## System Overview

```
PS5 (USB) → Raspberry Pi → UDP/LAN → Mini PC (ROS2) → Teensy 4.1 (Serial) → ESP32 v2
```

| Layer | Section | Language |
|-------|---------|----------|
| Joystick sender (Pi side) | `1_joy_controller/` | Python |
| Game logic / Behavior Tree | `2_behavior_tree/` | Python (ROS2) |
| Arm, weapon, sensor control | `3_upper_base_control/` | Python (ROS2) |
| Wheel PID, IMU, arm motor | `4_teensy_firmware/` | C++ (Arduino) |
| Pneumatics, conveyor, LEDs | `5_esp32_firmware/` | C++ (Arduino) |
| ROS2 startup | `6_launch/` | Python |
| Early prototype (Bluetooth era) | `Draft1_robot/` | C++ (Arduino) |

---

## Section 1 — Joy Controller (`1_joy_controller/`)

**Runs on: Raspberry Pi (connected to PS5 via USB)**

Reads PS5 controller input via Linux `evdev`, packages into JSON with sequence number, and sends over UDP to the robot's Mini PC.

| File | Description |
|------|-------------|
| `joy_main_v2.py` | Main loop — finds joystick device, maps axes/buttons, calls network send at 20Hz |
| `joy_network_v2.py` | UDP socket wrapper — sends `{seq, t, data}` packets, receives ACK from robot |

**Why UDP over LAN instead of Bluetooth:**
In 2025, Bluetooth signal was disrupted by interference from 20+ teams in the arena, causing mid-match disconnects. Switching to USB+UDP over a dedicated router eliminated this entirely.

---

## Section 2 — Behavior Tree (`2_behavior_tree/`)

**Runs on: Mini PC (ROS2 node)**

Core game logic for R1. Built with `py_trees_ros`, ticking at ~20Hz. The tree selects between E-Stop, Semi-Auto, and Manual mode — then routes to the correct zone node based on D-pad input.

```
Root
└── GetJoyValue          ← reads UDP joy topic → blackboard every tick
└── Mode Selector
    ├── E-Stop           ← highest priority, triggers on button or disconnect
    ├── Semi-Auto        ← planned (stubs in place)
    └── Manual           ← fully implemented, zone-aware
        ├── Zone 0       ← pre-match / homing
        ├── Zone 1       ← Martial Club: weapon assembly
        ├── Zone 2       ← Meihua Forest: scroll collection
        └── Zone 3       ← Arena: placement + combat
```

| File | Description |
|------|-------------|
| `main_bt.py` | Tree structure — wires all nodes together, starts ROS2 spin |
| `get_joy_value.py` | Reads `/joy_controller_value` topic, writes to blackboard (zone, e-stop, semi flag) |
| `check_condition.py` | Generic blackboard condition checker — reusable across all branches |
| `stop_robot.py` | Publishes zero velocity to all actuators — used by E-Stop branch |
| `base_mecanum_drive.py` | Reads joystick axes → publishes `TwistStamped` to mecanum controller |
| `manual_zone_0.py` | Zone 0: pre-match homing and setup mode |
| `manual_zone_1.py` | Zone 1 v1: weapon gripper (L/R) + staff arm J1/J2 |
| `manual_zone_1_v2.py` | Zone 1 v2: revised button mapping after field testing |
| `manual_zone_2.py` | Zone 2 v1: KFS arm J1/J2 + gripper toggle + conveyor direction |
| `manual_zone_2_v2.py` | Zone 2 v2: tuned arm speed + improved gripper toggle logic |
| `manual_zone_3.py` | Zone 3 v1: weapon release (L/R) + KFS placement arm |
| `manual_zone_3_v2.py` | Zone 3 v2: final version used in competition |

---

## Section 3 — Upper Base Control (`3_upper_base_control/`)

**Runs on: Mini PC (ROS2 nodes)**

Independent ROS2 nodes for each subsystem. Each subscribes to command topics from the BT and publishes hardware commands downstream.

| File | Node Name | Description |
|------|-----------|-------------|
| `get_joy_from_network.py` | `get_joy_value` | UDP receiver — parses JSON packets from Pi, publishes `/joy_controller_value` Joy msg. Detects packet drops via sequence number. Publishes connection status `/joy_is_connection` |
| `arm_kfs_control.py` | `arm_kfs_controller` | Subscribes to `/arm_kfs_cmd [arm_y, arm_z, gripper, conveyor]` → publishes JointState for URDF visualization + commands to Teensy |
| `weapon_control.py` | `weapon_controller` | Non-blocking state machine for pneumatic weapon sequence (keep: gripper→lift→lock / release: reverse). Handles L and R sides independently |
| `lidar_object_detector.py` | `lidar_object_detect` | Clusters YDLidar `/scan` data → detects weapon box (−20° to −160°) and R2 robot (40° to 140°) → publishes TF transforms `target_box`, `target_r2` |
| `lift_r2.py` | — | Lift R2 robot control node (in development) |
| `connect_to_teensy.py` | `command_and_get_teensy` | UDP bridge: receives arm/weapon commands from ROS2, packs as struct binary, sends to Teensy. Receives IMU + sensor data back |

---

## Section 4 — Teensy Firmware (`4_teensy_firmware/`)

**Runs on: Teensy 4.1 (connected to Mini PC via Serial /dev/ttyACM0)**

Micro-ROS firmware. Receives wheel velocity commands and arm position targets from ROS2 via Serial, closes PID loops locally, and outputs PWM to motor drivers.

| File | Description |
|------|-------------|
| `r1_teensy_v2.ino` | Main file — setup, loop, Micro-ROS agent init, task dispatch |
| `connect_to_pc.ino` | Serial communication with Mini PC — parses ROS2 messages, sends sensor data back |
| `connect_to_esp.ino` | UART Serial5 communication with ESP32 v2 — sends actuator commands downstream |
| `wheel_speed_control.ino` | Per-wheel velocity PID (kp=0.2, ki=0.1, kd=0.2, PPR=1000, 30ms loop) |
| `arm_kfs_control.ino` | Arm motor PID (kp=15.2, ki=0.0, kd=7.3) using AS5600 magnetic encoder |
| `as5600_control.ino` | AS5600 magnetic encoder read via I2C — absolute angle feedback for arm |
| `imu.ino` | BNO08x IMU read via SPI — quaternion output at ~50Hz |
| `encoder.ino` | Wheel encoder interrupt handler — counts pulses for velocity feedback |

---

## Section 5 — ESP32 Firmware (`5_esp32_firmware/`)

**Runs on: ESP32 v2 (connected to Teensy via UART Serial5)**

Downstream-only actuator bus. Receives packed command bytes from Teensy and drives all pneumatic solenoids, conveyor motor, and NeoPixel LEDs.

| File | Description |
|------|-------------|
| `esp_v2.ino` | Receives UART commands from Teensy → controls 4× pneumatic solenoids (weapon L/R gripper+lift), KFS conveyor motor, NeoPixel zone color indicator (Zone1=Red, Zone2=Green, Zone3=Blue) |

---

## Section 6 — Launch Files (`6_launch/`)

**ROS2 launch files — start all nodes with one command**

| File | Description |
|------|-------------|
| `r1_start.launch.py` | Main launch — starts all nodes: joy receiver, BT, arm KFS, weapon control, lidar detector, robot state publisher, ROS2 controller, Micro-ROS agent (Serial) |
| `load_ros2_controller.launch.py` | Loads `mecanum_drive_controller` plugin into `ros2_control` framework |

---

## Draft1_robot/ — Early Prototype (Bluetooth Era)

First version before switching to ROS2 architecture. PS5 connects to ESP32 via Bluetooth, sends CSV serial to Arduino Mega.

| File | Description |
|------|-------------|
| `Draft1_robot/Robot-R1/Main_ESP32_Trans.ino` | ESP32 reads PS5 Bluetooth → sends CSV joystick values via Serial |
| `Draft1_robot/Robot-R1/Main_Mega_R1_Receive.ino` | Arduino Mega receives CSV → controls mecanum drive + rack + gripper |
| `Draft1_robot/Robot-R2-Auto/Main_GIGAR1_R2_Auto.ino` | Arduino Giga: timed autonomous sequence for R2 |

**Why this was replaced:**
Heavy Bluetooth interference in competition arena caused mid-match disconnects (2025 result: lost control of robot). The entire communication stack was rebuilt around USB+UDP+LAN for 2026.
