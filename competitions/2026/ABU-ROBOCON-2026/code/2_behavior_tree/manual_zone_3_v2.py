import time
import py_trees
from py_trees.common import Status, Access
from std_msgs.msg import Int8, Int8MultiArray, Float32MultiArray, Float32
from rclpy.qos import QoSProfile, ReliabilityPolicy

# Button index map (evdev-verified, button_keys=[305,307,308,310,311,312,313,314,315,...]):
# [0]=O(Circle)  [1]=Triangle  [2]=Square  [3]=L1(310)  [4]=R1(311)  [5]=L2(312)  [6]=R2(313)
# [7]=Share/Create(314)  [8]=Options(315)  [9]=PS  [10]=L3  [11]=R3  [12]=Touchpad

# Zone 3 — v2
# Guard:        box_gripper_state (blackboard, written by Zone 2) must be 1 on entry
#               If 0 → skip ENTRY, go straight to READY (arm actions still work)
# Drive:        Joystick (BT handles MecanumDrive)
# On entry:     weapon_gripper=1, motor→ENTRY_ANGLE; Z→40cm (PID), Y outward (entry_y_timeout)
#
# ENTRY / READY / PRESET:
#   X[0]        → Z=40cm + motor=230.76° → _Z3_PRESET
#   O[1]        → Z=50cm + motor=158.04° → _Z3_PRESET
#   L1[3]       → Z velocity DOWN (manual, clears PID target) — always available
#   R1[4]       → Z velocity UP   (manual, clears PID target) — always available
#   R2[5] press1→ weapon→230°, Z→10 → _Z3_R2_ARMED
#   Triangle[2] → Z=10, box_gripper=release, weapon→0° → _Z3_READY
#
# _Z3_R2_ARMED (weapon at 230°, waiting):
#   R2[5] press2→ weapon_gripper=release, weapon→0°, Z=10 → _Z3_READY
#   Triangle[2] → Z=10, box_gripper=release, weapon→0° → _Z3_READY
#
# Y manual control (always available, level-hold):
#   Share[7]   → Y inward
#   Options[8] → Y outward
#
# Retract sequence (from ENTRY, READY, or PRESET):
#   SQ_WAIT → [0.25s] → Y_IN → [y_inward_timeout] → Z_DOWN (holds until zone exit)

# ──────────────────────────────────────────────────────────────────
#  TUNEABLE CONSTANTS
# ──────────────────────────────────────────────────────────────────
ZONE3_ENTRY_ANGLE   = 147.69   # deg — motor angle on zone entry (default hold)
ZONE3_X_Z           = 40.0    # cm  — Z target for X preset
ZONE3_X_ANGLE       = 230.76   # deg — motor angle for X preset
ZONE3_O_Z           = 50.0    # cm  — Z target for O preset
ZONE3_O_ANGLE       = 158.04   # deg — motor angle for O preset
ZONE3_OPTIONS_Z     = 55.0    # cm  — Z target for Options button
ZONE3_OPTIONS_ANGLE = 180.0   # deg — motor angle for Options button
ZONE3_R2_ARMED_ANGLE = 230.0  # deg — R2 press 1: weapon angle
ZONE3_R2_Z           = 10.0   # cm  — R2 press 1 & 2: Z target
ZONE3_TRI_RESET_Z    = 10.0   # cm  — Triangle reset: Z target

# Zone 3 state constants
_Z3_ENTRY   = 0
_Z3_READY   = 1
_Z3_SQ_WAIT = 2
_Z3_Y_IN    = 3
_Z3_Z_DOWN  = 4
_Z3_PRESET   = 5   # active preset selected; preset switching available
_Z3_R2_ARMED = 6   # R2 pressed once: weapon→230°, Z→10, waiting for second R2


class manual_zone3_v2(py_trees.behaviour.Behaviour):
    def __init__(self, name='manual_zone3_v2'):
        super(manual_zone3_v2, self).__init__(name)

        self.box_gripper    = 1     # keep gripping on entry (must be 1 from Zone 2)
        self.weapon_gripper = 1     # weapon gripper gripped on zone entry
        self.min_z3         = 0.0   # cm — lower encoder soft limit
        self.max_z3         = 70.0  # cm — upper encoder soft limit
        self.current_z_pos  = 0.0
        self.z_target       = None
        self.last_tick_time = 0.0

        self.y_out_speed      = 50    # Y outward speed on entry: 1–100
        self.y_in_speed       = 50    # Y inward speed after release: 1–100
        self.entry_y_timeout  = 3.0   # seconds Y moves outward on zone entry
        self.y_inward_timeout = 3.0   # seconds Y moves inward after gripper release

        self.state    = _Z3_ENTRY
        self.sq_timer = 0.0

        # Weapon angle
        self.weapon_target_angle = 0.0
        self.preset_angle        = 0.0   # reference angle for R2 nudge

        self.pre_x_value       = 0
        self.pre_o_value       = 0
        self.pre_tri_value     = 0
        self.pre_sq_value      = 0
        self.pre_r2_value      = 0
        self.pre_options_value = 0
        self.pre_share_value   = 0

        self._y_manual_dbg_time = 0.0   # throttle for Y manual debug print
        self._z_manual_dbg_time = 0.0   # throttle for Z manual debug print

        self.blackboard = self.attach_blackboard_client(name=self.name)
        self.blackboard.register_key(key='joy_msg_button',    access=Access.READ)
        self.blackboard.register_key(key='box_gripper_state', access=Access.READ)

    def setup(self, **kwargs):
        self.node = kwargs.get('node')
        if not self.node:
            raise KeyError("ROS node not found in kwargs")
        self.zone_publisher         = self.node.create_publisher(Int8,              'r1_current_zone',  10)
        self.arm_kfs_publisher      = self.node.create_publisher(Float32MultiArray, 'arm_kfs_cmd',      10)
        self.weapon_cmd_publisher   = self.node.create_publisher(Int8MultiArray,    'weapon_cmd',       10)
        self.weapon_angle_publisher = self.node.create_publisher(Float32,           'weapon_angle_cmd', 10)
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.node.create_subscription(Float32MultiArray, '/teensy/wheel_state',
                                      self._wheel_state_cb, qos)

    def _wheel_state_cb(self, msg):
        if len(msg.data) >= 11:
            self.current_z_pos = msg.data[10] * 4.81 / 1000.0   # raw → cm

    def update(self):
        joy = self.blackboard.joy_msg_button
        now = time.monotonic()

        # --- Zone entry detection ---
        fresh_entry = (now - self.last_tick_time) > 0.2
        if fresh_entry:
            # Guard: box gripper must be gripping (written by Zone 2 each tick)
            try:
                gripper_ok = (self.blackboard.box_gripper_state == 1)
            except KeyError:
                gripper_ok = False   # key absent → Zone 2 never ran

            self.box_gripper         = 1 if gripper_ok else 0
            self.weapon_gripper      = 1                    # always grip weapon on entry
            self.weapon_target_angle = ZONE3_ENTRY_ANGLE
            self.preset_angle        = ZONE3_ENTRY_ANGLE
            self.z_target            = 60.0
            self.sq_timer            = now
            self.state               = _Z3_ENTRY if gripper_ok else _Z3_READY
        self.last_tick_time = now

        # --- ENTRY: Z→40 PID, Y outward until timeout ---
        if self.state == _Z3_ENTRY:
            if now - self.sq_timer >= self.entry_y_timeout:
                self.state = _Z3_READY   # Teensy limit switch has stopped Y by now

        # --- X/O preset buttons (edge detect) — always available ---
        if joy[0] == 1 and self.pre_x_value == 0:        # X
            self.z_target            = ZONE3_X_Z
            self.weapon_target_angle = ZONE3_X_ANGLE
            self.preset_angle        = ZONE3_X_ANGLE
            self.state               = _Z3_PRESET
        if joy[1] == 1 and self.pre_o_value == 0:        # O
            self.z_target            = ZONE3_O_Z
            self.weapon_target_angle = ZONE3_O_ANGLE
            self.preset_angle        = ZONE3_O_ANGLE
            self.state               = _Z3_PRESET

        # --- Triangle: reset Z=10, box_gripper=release, weapon→home — always available ---
        if joy[2] == 1 and self.pre_tri_value == 0:
            self.z_target            = ZONE3_TRI_RESET_Z
            self.weapon_target_angle = 0.0
            self.box_gripper         = 0
            self.state               = _Z3_READY

        # --- R2 two-press launch sequence — always available ---
        # Press 1 (any state except R2_ARMED): weapon→230°, Z→10 → _Z3_R2_ARMED
        # Press 2 (_Z3_R2_ARMED):              weapon_gripper=release, weapon→0°, Z=10 → READY
        if joy[5] == 1 and self.pre_r2_value == 0:
            if self.state != _Z3_R2_ARMED:
                self.weapon_target_angle = ZONE3_R2_ARMED_ANGLE
                self.z_target            = ZONE3_R2_Z
                self.state               = _Z3_R2_ARMED
            else:
                self.weapon_gripper      = 0
                self.weapon_target_angle = 0.0
                self.z_target            = ZONE3_R2_Z
                self.state               = _Z3_READY

        # NOTE: joy[3]=L1 (not Square). Square retract trigger removed to avoid conflict.
        # Retract sequence (_Z3_SQ_WAIT → _Z3_Y_IN → _Z3_Z_DOWN) preserved for state machine.

        # --- State transitions (box gripper retract sequence) ---
        if self.state == _Z3_SQ_WAIT:
            if now - self.sq_timer >= 0.25:
                self.sq_timer = now
                self.state    = _Z3_Y_IN

        elif self.state == _Z3_Y_IN:
            if now - self.sq_timer >= self.y_inward_timeout:
                self.z_target = 40.0
                self.state    = _Z3_Z_DOWN

        # _Z3_Z_DOWN: z_target=20 PID, holds until zone exit

        # --- Z control: L1[3] velocity DOWN, R1[4] velocity UP, or PID position ---
        if joy[3] == 1 and self.current_z_pos > self.min_z3:    # L1 — DOWN
            arm_z_cmd     = -100.0
            self.z_target = None
            if now - self._z_manual_dbg_time >= 0.5:
                print("[Z3] L1 held → Z down")
                self._z_manual_dbg_time = now
        elif joy[4] == 1 and self.current_z_pos < self.max_z3:  # R1 — UP
            arm_z_cmd     = 100.0
            self.z_target = None
            if now - self._z_manual_dbg_time >= 0.5:
                print("[Z3] R1 held → Z up")
                self._z_manual_dbg_time = now
        elif self.z_target is not None:
            target    = max(self.min_z3 + 0.5, min(self.z_target, self.max_z3))
            arm_z_cmd = target
        else:
            arm_z_cmd = 0.0

        # --- Y control (auto states take priority; Share[7]=inward, Options[8]=outward) ---
        if self.state == _Z3_ENTRY:
            arm_y = float(self.y_out_speed)           # entry sequence: Y outward
        elif self.state == _Z3_Y_IN:
            arm_y = -float(self.y_in_speed)           # retract sequence: Y inward
        elif joy[7] == 1:                             # Share held → Y inward
            arm_y = -float(self.y_in_speed)
            if now - self._y_manual_dbg_time >= 0.5:
                print("[Z3] Share held → Y inward")
                self._y_manual_dbg_time = now
        elif joy[8] == 1:                             # Options held → Y outward
            arm_y = float(self.y_out_speed)
            if now - self._y_manual_dbg_time >= 0.5:
                print("[Z3] Option held → Y outward")
                self._y_manual_dbg_time = now
        else:
            arm_y = 0.0

        # --- Edge detect update ---
        self.pre_x_value       = joy[0]
        self.pre_o_value       = joy[1]
        self.pre_tri_value     = joy[2]
        self.pre_r2_value      = joy[5]
        self.pre_share_value   = joy[7]
        self.pre_options_value = joy[8]

        self._publish(arm_z_cmd, arm_y)
        return Status.SUCCESS

    def _publish(self, arm_z_cmd, arm_y):
        # box gripper INVERTED: send 1-box_gripper; blackboard write stays internal (non-inverted)
        arm_msg = Float32MultiArray()
        arm_msg.data = [arm_z_cmd, arm_y, float(1 - self.box_gripper), 0.0]
        self.arm_kfs_publisher.publish(arm_msg)

        weapon_msg = Int8MultiArray()
        weapon_msg.data = [self.weapon_gripper, 0]
        self.weapon_cmd_publisher.publish(weapon_msg)

        angle_msg = Float32()
        angle_msg.data = self.weapon_target_angle
        self.weapon_angle_publisher.publish(angle_msg)

        zone_msg = Int8()
        zone_msg.data = 3
        self.zone_publisher.publish(zone_msg)