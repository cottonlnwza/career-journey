import time
import py_trees
from py_trees.common import Status, Access
from std_msgs.msg import Int8, Int8MultiArray, Float32MultiArray, Float32
from rclpy.qos import QoSProfile, ReliabilityPolicy

# Button index map (verified from real hardware/UDP data):
# [0]=X   [1]=O   [2]=Triangle  [3]=Square  [4]=R1   [5]=R2
# [7]=L1  [8]=L2  [11]=Share    [12]=Options [13]=PS logo

# Zone 1 — v2
# Drive:        Left + Right joystick (MecanumDrive node, handled by BT)
# Z manual:     R1[4]=UP, L1[7]=DOWN  (velocity mode)
# Z auto-entry: Auto-move to 20cm on zone entry (PID mode)
# Z presets:    X[0] → 10cm, Triangle[2] → 30cm  (edge detect → PID)
# KeepWeapon:   O[1] — IDLE→grip→wait 1s→motor→180°  (edge detect, one-shot)
# NeoPixel:     PS[13] — solid-red for 3s, then zone color returns
# Removed:      PS weapon toggle, Y-axis manual control, Box gripper (Square[3])

# ──────────────────────────────────────────────────────────────────
#  TUNEABLE CONSTANTS
# ──────────────────────────────────────────────────────────────────
ZONE1_WEAPON_ENTRY_ANGLE = 154.0     # deg — motor angle on zone entry (placeholder, tune after fixed-home calibration)
ZONE1_WEAPON_ARMED_ANGLE = 230.76   # deg — motor angle after KW O-button sequence (placeholder, tune later)
ZONE1_KW_GRIP_WAIT       = 1.0     # s   — wait between grip and motor→armed angle
ZONE1_PS_NEO_DURATION    = 3.0     # s   — solid-red NeoPixel duration (zone=5)

# KeepWeapon state constants
_KW_IDLE          = 0
_KW_GRIP_Z10      = 1   # O press 1: gripper grip + Z→10
_KW_LIFT_Z40_WAIT = 2   # O press 2: Z→40, waiting 1s timer
_KW_ARMED         = 3   # motor → 135°
_KW_ARMED_Z        = 4   # timer done: weapon→

class manual_zone1_v2(py_trees.behaviour.Behaviour):
    def __init__(self, name='manual_zone1_v2'):
        super(manual_zone1_v2, self).__init__(name)

        self.weapon_gripper = 0   # 0=release, 1=grip

        self.min_z1 = 0.0   # cm — lower encoder limit
        self.max_z1 = 70.0  # cm — upper encoder limit
        self.current_z_pos = 0.0

        self.z_target = None
        self.last_tick_time = 0.0

        self.y_homing = False
        self.y_homed  = False
        self.sw_y_in  = 0

        self.pre_ps_value  = 0
        self.pre_o_value   = 0
        self.pre_x_value   = 0
        self.pre_tri_value = 0

        # Z manual speed: 50–100 (50=slowest/power40, 100=Zone0 baseline/power80)
        self.z_up_speed = 50
        self.z_dn_speed = 50

        # KeepWeapon state machine
        self.kw_state            = _KW_IDLE
        self.kw_timer            = 0.0
        self.weapon_target_angle = 0.0

        # PS NeoPixel override (solid red for ZONE1_PS_NEO_DURATION seconds)
        self.ps_neo_active = False
        self.ps_neo_timer  = 0.0

        self.blackboard = self.attach_blackboard_client(name=self.name)
        self.blackboard.register_key(key='joy_msg_button', access=Access.READ)

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
        # index 10 = Z raw encoder count; index 12 = Y-IN limit switch (pin 5: 1=hit)
        if len(msg.data) >= 13:
            self.current_z_pos = msg.data[10] * 4.81 / 1000.0   # raw → cm
            self.sw_y_in = int(msg.data[12])

    def update(self):
        joy = self.blackboard.joy_msg_button
        now = time.monotonic()

        # --- Zone entry detection ---
        # Gap > 200ms means the zone was inactive → treat as fresh entry.
        if now - self.last_tick_time > 0.2:
            self.z_target            = 29.9              # auto-move to entry height
            self.y_homing            = True                   # start Y auto-home
            self.y_homed             = False
            self.kw_state            = _KW_IDLE
            self.weapon_gripper      = 0
            self.weapon_target_angle = ZONE1_WEAPON_ENTRY_ANGLE
            self.ps_neo_active       = False
        self.last_tick_time = now

        # --- Preset position buttons (edge detect: trigger once on press) ---
        if joy[0] == 1 and self.pre_x_value == 0:        # X → move to 10cm
            self.z_target = 10.0
        if joy[2] == 1 and self.pre_tri_value == 0:      # Triangle → move to 30cm
            self.z_target = 30.0

        # --- Z velocity control (manual override — clears PID target on press) ---
        if joy[4] == 1 and self.current_z_pos < self.max_z1:           # R1 — UP
            arm_z_cmd = float(self.z_up_speed)
            self.z_target = None
        elif joy[7] == 1 and self.current_z_pos > self.min_z1 + 0.5:  # L1 — DOWN
            arm_z_cmd = -float(self.z_dn_speed)
            self.z_target = None
        elif self.z_target is not None:
            target    = max(self.min_z1 + 0.5, min(self.z_target, self.max_z1))
            arm_z_cmd = target
        else:
            arm_z_cmd = 0.0

        # --- Y auto-home (runs once per zone entry; locks Y after pin 5 triggers) ---
        if self.y_homing:
            if self.sw_y_in == 1:
                self.y_homing = False
                self.y_homed  = True
                arm_y = 0.0
            else:
                arm_y = -80.0   # drive Y inward; Teensy also enforces limit switch
        else:
            arm_y = 0.0

        # --- KeepWeapon 2-press staged sequence (O button, edge detect) ---
        # Press 1: wgrip=release, Z→10; Press 2: wgrip=grip, Z→40, wait 1s, motor→135°
        if joy[1] == 1 and self.pre_o_value == 0:
            # if self.kw_state == _KW_IDLE:
            #     # O press 1: release weapon gripper, Z → 10
            #     self.weapon_gripper = 0
            #     self.kw_state       = _KW_GRIP_Z10
            if self.kw_state == _KW_IDLE:
                # O press 2: Z → 40, start 1s delay
                self.weapon_gripper = 1
                self.z_target = 31.9
                self.kw_timer = now
                self.kw_state = _KW_LIFT_Z40_WAIT
            elif self.kw_state == _KW_LIFT_Z40_WAIT:
                # O press 2: Z → 40, start 1s delay
                self.z_target = 43.7
                self.kw_timer = now
                self.weapon_target_angle = ZONE1_WEAPON_ARMED_ANGLE
                self.kw_state = _KW_ARMED

        # if self.kw_state == _KW_LIFT_Z40_WAIT:
        #     if now - self.kw_timer >= ZONE1_KW_GRIP_WAIT:
        #         self.weapon_target_angle = ZONE1_WEAPON_ARMED_ANGLE
        #         self.kw_state            = _KW_ARMED

        # --- PS logo: solid-red NeoPixel for ZONE1_PS_NEO_DURATION seconds ---
        if joy[13] == 1 and self.pre_ps_value == 0:
            self.ps_neo_active = True
            self.ps_neo_timer  = now

        if self.ps_neo_active and (now - self.ps_neo_timer >= ZONE1_PS_NEO_DURATION):
            self.ps_neo_active = False

        # --- Update edge detect state ---
        self.pre_o_value   = joy[1]
        self.pre_ps_value  = joy[13]
        self.pre_x_value   = joy[0]
        self.pre_tri_value = joy[2]

        # --- Publish arm command ---
        # box gripper always grip (=0 in inverted protocol); conveyor=0
        arm_msg = Float32MultiArray()
        arm_msg.data = [arm_z_cmd, arm_y, 0.0, 0.0]
        self.arm_kfs_publisher.publish(arm_msg)

        # --- Publish weapon command ---
        weapon_msg = Int8MultiArray()
        weapon_msg.data = [self.weapon_gripper, 0]
        self.weapon_cmd_publisher.publish(weapon_msg)

        # --- Publish weapon angle ---
        angle_msg = Float32()
        angle_msg.data = self.weapon_target_angle
        self.weapon_angle_publisher.publish(angle_msg)

        # --- Publish zone (PS override → zone 5 = solid-red NeoPixel) ---
        zone_msg = Int8()
        zone_msg.data = 5 if self.ps_neo_active else 1
        self.zone_publisher.publish(zone_msg)

        return Status.SUCCESS