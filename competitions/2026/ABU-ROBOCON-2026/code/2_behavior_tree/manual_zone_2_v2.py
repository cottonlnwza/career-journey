import time
import py_trees
from py_trees.common import Status, Access
from std_msgs.msg import Int8, Int8MultiArray, Float32MultiArray, Float32
from rclpy.qos import QoSProfile, ReliabilityPolicy

# Button index map (verified from real hardware/UDP data):
# [0]=X   [1]=O   [2]=Triangle  [3]=Square  [4]=R1   [5]=R2
# [7]=L1  [8]=L2  [11]=Share    [12]=Options [13]=PS logo

# Zone 2 — v2
# Drive:        Left + Right joystick (MecanumDrive node, handled by BT)
# Z presets:    X[0]→20cm, O[1]→40cm, Triangle[2]→60cm  (edge detect → PID)
#               (no manual Z velocity — Z moves via PID presets and Square sequence only)
# Z range:      0–70 cm
# Y control:    R1[4]=OUT, L1[7]=IN  (hold to move, same as Zone 0)
#               Auto-override during Square sequence Y_INWARD state
# Box gripper:  Square[3] sequence (see state machine below)
# Weapon grip:  Triggered once on zone entry (=1), then locked
# Weapon angle: Fixed at ZONE2_WEAPON_ANGLE (0°) throughout zone
# NeoPixel:     Zone 2 color handled by Teensy (green)
#
# Square sequence state machine:
#   IDLE     → [Square↓]  → GRIPPED  : box grip ON, wait 0.5s
#   GRIPPED  → [0.5s]     → LIFTING  : z_target = current+10 cm
#   LIFTING  → [Z±10cm]   → Y_INWARD : Y moves inward slowly
#   Y_INWARD → [5.0s]     → Z_DOWN   : z_target = 20 cm (PID)
#   Z_DOWN   → (holds until Square↓ again)
#
#   [Square↓ again, any active state]: box release, z_target = current−10 cm → IDLE

# ──────────────────────────────────────────────────────────────────
#  TUNEABLE CONSTANTS
# ──────────────────────────────────────────────────────────────────
ZONE2_WEAPON_ANGLE = 37.44  # deg — 0° = home position; motor stays here throughout Zone 2 (placeholder, tune after fixed-home calibration)

# Square state constants
_SQ_IDLE     = 0
_SQ_GRIPPED  = 1   # gripped, waiting 0.5s
_SQ_LIFTING  = 2   # Z moving to current+10 cm
_SQ_Y_INWARD = 3   # Y inward slowly (y_inward_timeout)
_SQ_Z_DOWN   = 4   # Z moving to 20 cm (PID), holds here

# Zone 2 entry sequence constants
_ENTRY_IDLE    = 0   # no entry sequence (normal control)
_ENTRY_Y_OUT   = 1   # Y moving outward for 0.5s
_ENTRY_RELEASE = 2   # release box gripper, sequence done


class manual_zone2_v2(py_trees.behaviour.Behaviour):
    def __init__(self, name='manual_zone2_v2'):
        super(manual_zone2_v2, self).__init__(name)

        self.weapon_gripper      = 0   # triggered once on zone entry, then locked
        self.weapon_target_angle = 0.0
        self.box_gripper         = 1   # keep clamped from Zone 0/1; released after entry sequence

        # Entry sequence state machine
        self.entry_state       = _ENTRY_IDLE
        self.entry_timer       = 0.0
        self.entry_y_out_speed = 80   # Y OUT speed during entry sequence (1–100)

        self.min_z2 = 0.0    # cm — lower encoder limit
        self.max_z2 = 70.0   # cm — upper encoder limit
        self.current_z_pos  = 0.0

        # z_target: None = stop/hold; float = PID position setpoint (cm)
        self.z_target = None
        self.last_tick_time = 0.0

        self.y_speed          = 80    # R1/L1 manual Y speed: 1–100
        self.y_auto_speed     = 100   # Y inward speed during Square sequence
        self.y_inward_timeout = 1.0   # seconds of Y inward movement before Z_DOWN

        # Square sequence state machine
        self.sq_state         = _SQ_IDLE
        self.sq_timer         = 0.0
        self.sq_lift_z_target = None

        self.pre_x_value   = 0
        self.pre_o_value   = 0
        self.pre_tri_value = 0
        self.pre_sq_value  = 0

        self.last_preset_z = None   # last Z preset selected: 20/40/60 cm or None

        self.blackboard = self.attach_blackboard_client(name=self.name)
        self.blackboard.register_key(key='joy_msg_button',    access=Access.READ)
        self.blackboard.register_key(key='box_gripper_state', access=Access.WRITE)

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
        # index 10 = Z raw encoder count (confirmed correct index)
        if len(msg.data) >= 11:
            self.current_z_pos = msg.data[10] * 4.81 / 1000.0   # raw → cm

    def update(self):
        joy = self.blackboard.joy_msg_button
        now = time.monotonic()

        # --- Zone entry detection ---
        # Gap > 200ms means zone was inactive → treat as fresh entry
        fresh_entry = (now - self.last_tick_time) > 0.2
        if fresh_entry:
            self.weapon_gripper      = 1                   # trigger weapon once on entry
            self.weapon_target_angle = ZONE2_WEAPON_ANGLE  # motor → 0°
            self.sq_state            = _SQ_IDLE
            self.sq_lift_z_target    = None
            self.box_gripper         = 1                   # keep clamped from Zone 0/1
            self.z_target            = 40.0                # auto-move to entry height
            self.last_preset_z       = None
            self.entry_state         = _ENTRY_Y_OUT        # start entry Y-out sequence
            self.entry_timer         = now
        self.last_tick_time = now

        # --- Entry sequence: Y OUT 0.5s → release box gripper ---
        if self.entry_state == _ENTRY_Y_OUT:
            arm_y = float(self.entry_y_out_speed)
            if now - self.entry_timer >= 0.5:
                self.box_gripper = 0
                self.entry_state = _ENTRY_RELEASE
        elif self.entry_state == _ENTRY_RELEASE:
            arm_y = 0.0   # stop Y, normal control takes over next tick
            self.entry_state = _ENTRY_IDLE

        # --- Z preset buttons (edge detect) — always available ---
        if joy[0] == 1 and self.pre_x_value == 0:        # X → 20 cm
            self.z_target      = 20.0
            self.last_preset_z = 20.0
        if joy[1] == 1 and self.pre_o_value == 0:        # O → 40 cm
            self.z_target      = 40.0
            self.last_preset_z = 40.0
        if joy[2] == 1 and self.pre_tri_value == 0:      # Triangle → 60 cm
            self.z_target      = 60.0
            self.last_preset_z = 60.0

        # --- Square button: start or cancel sequence (edge detect) ---
        if joy[3] == 1 and self.pre_sq_value == 0:
            if self.sq_state == _SQ_IDLE:
                self.box_gripper = 1
                self.sq_timer    = now
                self.sq_state    = _SQ_GRIPPED
            else:
                self.box_gripper      = 0
                self.sq_lift_z_target = None
                if self.last_preset_z is not None:
                    self.z_target = self.last_preset_z
                else:
                    self.z_target = max(self.min_z2, self.current_z_pos - 10.0)
                self.sq_state = _SQ_IDLE

        # --- Square state machine transitions ---
        if self.sq_state == _SQ_GRIPPED:
            if now - self.sq_timer >= 0.5:
                self.sq_lift_z_target = min(self.max_z2, self.current_z_pos + 10.0)
                self.z_target         = self.sq_lift_z_target
                self.sq_state         = _SQ_LIFTING

        elif self.sq_state == _SQ_LIFTING:
            if (self.sq_lift_z_target is not None and
                    abs(self.current_z_pos - self.sq_lift_z_target) < 10.0):
                self.sq_timer = now
                self.sq_state = _SQ_Y_INWARD

        elif self.sq_state == _SQ_Y_INWARD:
            if now - self.sq_timer >= self.y_inward_timeout:
                self.z_target = 20.0
                self.sq_state = _SQ_Z_DOWN

        # _SQ_Z_DOWN: z_target=20.0, arm_y=0 — holds until Square↓ again

        # --- Z control (PID position mode only — no manual velocity) ---
        if self.z_target is not None:
            target    = max(self.min_z2 + 0.5, min(self.z_target, self.max_z2))
            arm_z_cmd = target
        else:
            arm_z_cmd = 0.0

        # --- Y control: entry sequence → Square sequence → manual (priority order) ---
        if self.entry_state != _ENTRY_IDLE:
            pass   # arm_y already set by entry sequence above
        elif self.sq_state == _SQ_Y_INWARD:
            arm_y = -float(self.y_auto_speed)
        elif joy[4] == 1:                        # R1 — Y outward
            arm_y = float(self.y_speed)
        elif joy[7] == 1:                        # L1 — Y inward
            arm_y = -float(self.y_speed)
        else:
            arm_y = 0.0

        # --- Update edge detect state ---
        self.pre_x_value   = joy[0]
        self.pre_o_value   = joy[1]
        self.pre_tri_value = joy[2]
        self.pre_sq_value  = joy[3]

        # --- Share gripper state with Zone 3 (guard check) ---
        self.blackboard.box_gripper_state = self.box_gripper

        # --- Publish arm command (box gripper INVERTED: send 1-box_gripper) ---
        arm_msg = Float32MultiArray()
        arm_msg.data = [arm_z_cmd, arm_y, float(1 - self.box_gripper), 0.0]
        self.arm_kfs_publisher.publish(arm_msg)

        # --- Publish weapon command ---
        weapon_msg = Int8MultiArray()
        weapon_msg.data = [self.weapon_gripper, 0]
        self.weapon_cmd_publisher.publish(weapon_msg)

        # --- Publish weapon angle (fixed at 0° throughout Zone 2) ---
        angle_msg = Float32()
        angle_msg.data = self.weapon_target_angle
        self.weapon_angle_publisher.publish(angle_msg)

        # --- Publish zone ---
        zone_msg = Int8()
        zone_msg.data = 2
        self.zone_publisher.publish(zone_msg)

        return Status.SUCCESS