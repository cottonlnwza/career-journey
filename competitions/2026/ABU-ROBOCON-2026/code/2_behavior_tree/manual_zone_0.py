import time
import py_trees
from py_trees.common import Status, Access
from std_msgs.msg import Int8, Int8MultiArray, Float32MultiArray, Float32
from rclpy.qos import QoSProfile, ReliabilityPolicy

# Button index map (verified from real hardware/UDP data):
# [0]=X   [1]=O   [2]=Triangle  [3]=Square  [4]=R1   [5]=R2
# [7]=L1  [8]=L2  [11]=Share    [12]=Options [13]=PS logo

# Zone 0 — Startup / Homing / Full-manual debug zone
#
# Homing runs ONCE per process start (has_homed_once flag):
#   HOMING_Z      : drive Z DOWN until pin 25 triggers
#   HOMING_Y      : drive Y IN  until pin 5  triggers
#   HOMING_WEAPON : motor → 0°; brief gripper test; then READY (weapon stays at 0°)
#
# Re-entry (has_homed_once=True, coming back from another zone):
#   Setup pose: Z→30cm (position), Y inward to limit, weapon_gripper=grip, weapon=200°
#   Does NOT reset encoders or re-run homing.
#
# READY state:
#   Z control:    R1[4]=UP, L1[7]=DOWN (velocity ±100); cleared by KW position targets
#   Y control:    Triangle[2]=OUT, X[0]=IN (hold); re-entry Y homing takes priority
#   KeepWeapon:   O[1] — 3-press staged sequence
#                 Press 1 → weapon=200°, wgrip=release
#                 Press 2 → wgrip=grip, Z→10
#                 Press 3 → Z→40, wait 1s, weapon→135°
#   Box gripper:  Square[3] toggle (internal: 0=release, 1=grip)
#                 NOTE: published INVERTED (sent 0=grip, 1=release)
#   NeoPixel:     PS[13] — solid-red for 3s

# ──────────────────────────────────────────────────────────────────
#  TUNEABLE CONSTANTS
# ──────────────────────────────────────────────────────────────────
ZONE0_WEAPON_HOME_ANGLE     = 0.0      # deg — motor stays here after homing (wait for O)
ZONE0_WEAPON_ENTRY_ANGLE    = 154.0    # deg — re-entry pose target + O press 1 target
ZONE0_WEAPON_ARMED_ANGLE    = 230.76    # deg — final armed angle after O press 3 + 1s wait
ZONE0_KW_GRIP_WAIT          = 1.0      # s   — delay between Z=40 and motor→135°
ZONE0_PS_NEO_DURATION       = 3.0      # s   — solid-red NeoPixel duration
ZONE0_HOMING_WEAPON_TIMEOUT = 3.0      # s   — fixed wait for motor to reach 0°
ZONE0_KFS_HOMING_Y_SPEED    = -50.0    # Y inward speed (negative=inward)
ZONE0_Z_DOWN_SPEED          = -100.0   # velocity DOWN for HOMING_Z 
ZONE0_REENTRY_Z_TARGET      = 30.0     # cm  — Z position target on zone re-entry

# KeepWeapon state constants
_KW_IDLE          = 0
_KW_ENTRY_200     = 1   # O press 1: weapon→200°, gripper release
_KW_GRIP_Z10      = 2   # O press 2: gripper grip, Z→10
_KW_LIFT_Z40_WAIT = 3   # O press 3: Z→40, 1s timer running
_KW_ARMED_135     = 4   # timer done: weapon→135°

_KW_NAMES = {
    _KW_IDLE: 'IDLE', _KW_ENTRY_200: 'ENTRY_200',
    _KW_GRIP_Z10: 'GRIP_Z10', _KW_LIFT_Z40_WAIT: 'LIFT_Z40_WAIT',
    _KW_ARMED_135: 'ARMED_135',
}


class manual_zone0(py_trees.behaviour.Behaviour):
    def __init__(self, name='manual_zone0'):
        super(manual_zone0, self).__init__(name)

        self.weapon_gripper = 0   # 0=release, 1=grip
        self.kfs_gripper    = 0   # internal: 0=release, 1=grip (published INVERTED)

        self.pre_o_value  = 0
        self.pre_ps_value = 0
        self.pre_sq_value = 0

        self.y_speed = 50   # Y manual speed: 1–100

        self.min_z0 = 0.0
        self.max_z0 = 70.0
        self.current_z_pos = 0.0

        # Homing state machine: HOMING_Z → HOMING_Y → HOMING_WEAPON → READY
        self.homing_state        = 'HOMING_Z'
        self.has_homed_once      = False   # True after first successful homing; persists across zone switches
        self.sw_z_bottom         = 0
        self.sw_y_in             = 0
        self.homing_weapon_timer = 0.0

        # Re-entry Y drive (runs once on zone re-entry after homing is done)
        self.reentry_y_homing = False

        # KeepWeapon state machine
        self.kw_state            = _KW_IDLE
        self.kw_timer            = 0.0
        self.kw_z_target         = None    # position target (cm) for KW sequence; None = velocity mode
        self.weapon_target_angle = 0.0

        # PS NeoPixel override
        self.ps_neo_active = False
        self.ps_neo_timer  = 0.0

        self._last_published_angle = None   # tracks /weapon_angle_cmd to log on change
        self.weapon_angle_current  = 0.0   # feedback from /weapon_angle_state[0]

        self.last_tick_time            = 0.0
        self._last_debug_time          = 0.0
        self._last_logged_homing_state = None

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
        self.node.create_subscription(Float32MultiArray, 'weapon_angle_state',
                                      self._weapon_angle_state_cb, qos)

    def _weapon_angle_state_cb(self, msg):
        # [0]=current_angle  [1]=target_angle  [2]=motor_power
        if len(msg.data) >= 1:
            self.weapon_angle_current = msg.data[0]

    def _wheel_state_cb(self, msg):
        # [7]  = Z position in cm
        # [8]  = sw_z_bottom (pin 25: 1=bottom limit hit)
        # [12] = sw_y_in     (pin 5:  1=Y-IN limit hit)
        if len(msg.data) >= 13:
            self.current_z_pos = msg.data[7]
            self.sw_z_bottom   = int(msg.data[8])
            self.sw_y_in       = int(msg.data[12])

    def update(self):
        joy = self.blackboard.joy_msg_button
        now = time.monotonic()
        prev_homing_state = self.homing_state

        # --- Zone entry detection (200ms gap = zone was inactive) ---
        if now - self.last_tick_time > 0.2:
            self.ps_neo_active = False
            if not self.has_homed_once:
                # First startup: run full homing sequence from scratch
                self.homing_state        = 'HOMING_Z'
                self.kw_state            = _KW_IDLE
                self.weapon_gripper      = 0
                self.weapon_target_angle = ZONE0_WEAPON_HOME_ANGLE
                self.kw_z_target         = None
                self.reentry_y_homing    = False
            else:
                # Re-entry after homing done: setup pose (no encoder reset, not homing)
                self.homing_state        = 'READY'
                self.weapon_gripper      = 0                        # weapon release
                self.weapon_target_angle = ZONE0_WEAPON_HOME_ANGLE  # 0°
                self.kw_state            = _KW_IDLE
                self.kw_z_target         = ZONE0_REENTRY_Z_TARGET   # Z → 30 cm (position)
                self.reentry_y_homing    = True                     # drive Y in to limit
                # Pre-seed edge detect to prevent spurious button triggers on entry
                self.pre_o_value  = joy[1]
                self.pre_ps_value = joy[13]
                self.pre_sq_value = joy[3]
        self.last_tick_time = now

        # ── Homing state machine ──────────────────────────────────────────────
        if self.homing_state == 'HOMING_Z':
            if self.sw_z_bottom == 1:
                self.kfs_gripper  = 1   # close box gripper before Y drive
                self.homing_state = 'HOMING_Y'
                arm_z_cmd = 0.0
            else:
                arm_z_cmd = ZONE0_Z_DOWN_SPEED
            arm_y = 0.0

        elif self.homing_state == 'HOMING_Y':
            if self.sw_y_in == 1:
                self.homing_state        = 'HOMING_WEAPON'
                self.homing_weapon_timer = now
                self.weapon_gripper      = 1
                arm_y = 0.0
            else:
                arm_y = ZONE0_KFS_HOMING_Y_SPEED
            arm_z_cmd = 0.0

        elif self.homing_state == 'HOMING_WEAPON':
            self.weapon_target_angle = ZONE0_WEAPON_HOME_ANGLE
            elapsed = now - self.homing_weapon_timer
            half    = ZONE0_HOMING_WEAPON_TIMEOUT / 5.0
            self.weapon_gripper = 1 if elapsed < half else 0
            if elapsed >= ZONE0_HOMING_WEAPON_TIMEOUT:
                # Homing complete: go READY, stay at 0° — do NOT auto-move to 200°
                self.homing_state        = 'READY'
                self.weapon_target_angle = ZONE0_WEAPON_HOME_ANGLE
                self.kw_state            = _KW_IDLE
                self.weapon_gripper      = 0
                self.kw_z_target         = None
                self.reentry_y_homing    = False
                self.has_homed_once      = True
                self.pre_o_value  = joy[1]
                self.pre_ps_value = joy[13]
                self.pre_sq_value = joy[3]
            arm_z_cmd = 0.0
            arm_y     = 0.0

        else:  # READY — normal Zone 0 manual control
            # --- Y control: re-entry drive to limit takes priority over manual ---
            if self.reentry_y_homing:
                if self.sw_y_in == 1:
                    self.reentry_y_homing = False
                    arm_y = 0.0
                else:
                    arm_y = ZONE0_KFS_HOMING_Y_SPEED   # inward
            elif joy[2] == 1:
                arm_y = float(self.y_speed)    # Triangle — Y outward
            elif joy[0] == 1:
                arm_y = -float(self.y_speed)   # X — Y inward
            else:
                arm_y = 0.0

            # --- Z control: velocity (R1/L1) OR KW position target ---
            if joy[4] == 1 and self.current_z_pos < self.max_z0:    # R1 — UP
                arm_z_cmd = 100.0
                self.kw_z_target = None   # velocity press clears position target
            elif joy[7] == 1 and self.current_z_pos > self.min_z0:  # L1 — DOWN
                arm_z_cmd = -100.0
                self.kw_z_target = None
            elif self.kw_z_target is not None:
                target    = max(self.min_z0 + 0.5, min(self.kw_z_target, self.max_z0))
                arm_z_cmd = target
            else:
                arm_z_cmd = 0.0

            # --- KeepWeapon 3-press staged sequence (O button, edge detect) ---
            if joy[1] == 1 and self.pre_o_value == 0:
                self.node.get_logger().info(
                    f'[Z0] O_EDGE joyO={joy[1]} preO={self.pre_o_value} '
                    f'kw={_KW_NAMES.get(self.kw_state, "?")}'
                )
                if self.kw_state == _KW_IDLE:
                    # O press 1: weapon → 200°, release gripper
                    self.weapon_target_angle = ZONE0_WEAPON_ENTRY_ANGLE
                    self.kw_z_target    = 29.9
                    self.weapon_gripper      = 0
                    self.kw_state            = _KW_ENTRY_200
                    self.node.get_logger().info(
                        f'[Z0] O1 → weapon target {self.weapon_target_angle:.1f}° wgrip=0 kw→ENTRY_200'
                    )
                elif self.kw_state == _KW_ENTRY_200:
                    # O press 2: grip weapon, Z → 20
                    self.weapon_gripper = 1
                    self.kw_z_target    = 31.9
                    self.kw_state       = _KW_GRIP_Z10
                    self.node.get_logger().info(
                        f'[Z0] O2 → wgrip=1 kw_z=20 kw→GRIP_Z10'
                    )
                elif self.kw_state == _KW_GRIP_Z10:
                    # O press 3: Z → 40, start 1s delay
                    self.kw_z_target = 43.7
                    self.kw_timer    = now
                    self.kw_state    = _KW_LIFT_Z40_WAIT
                    self.node.get_logger().info(
                        f'[Z0] O3 → kw_z=40 timer start kw→LIFT_Z40_WAIT'
                    )

            # KW timer: 1s after LIFT_Z40_WAIT → ARMED_135
            if self.kw_state == _KW_LIFT_Z40_WAIT:
                if now - self.kw_timer >= ZONE0_KW_GRIP_WAIT:
                    self.weapon_target_angle = ZONE0_WEAPON_ARMED_ANGLE
                    self.kw_state            = _KW_ARMED_135
                    self.node.get_logger().info(
                        f'[Z0] KW timer → weapon target {self.weapon_target_angle:.1f}° kw→ARMED_135'
                    )

            # --- PS logo: solid-red NeoPixel ---
            if joy[13] == 1 and self.pre_ps_value == 0:
                self.ps_neo_active = True
                self.ps_neo_timer  = now

            if self.ps_neo_active and (now - self.ps_neo_timer >= ZONE0_PS_NEO_DURATION):
                self.ps_neo_active = False

            # --- Box gripper toggle (Square=joy[3], edge detect) ---
            if joy[3] == 1 and self.pre_sq_value == 0:
                self.kfs_gripper ^= 1

        # Update edge detect (always, prevents false trigger on state transition)
        self.pre_o_value  = joy[1]
        self.pre_ps_value = joy[13]
        self.pre_sq_value = joy[3]

        # --- Publish arm command (box gripper INVERTED: send 1-kfs_gripper) ---
        arm_msg = Float32MultiArray()
        arm_msg.data = [arm_z_cmd, arm_y, float(1 - self.kfs_gripper), 0.0]
        self.arm_kfs_publisher.publish(arm_msg)

        # --- Debug logging (throttled 0.5s, plus immediate on state change) ---
        if self.homing_state != prev_homing_state:
            self.node.get_logger().info(
                f'[Z0] homing: {prev_homing_state} -> {self.homing_state} '
                f'(z_bot={self.sw_z_bottom}, y_in={self.sw_y_in}, z={self.current_z_pos:.1f})'
            )

        if self.homing_state != self._last_logged_homing_state or now - self._last_debug_time >= 0.5:
            self._last_debug_time = now
            self._last_logged_homing_state = self.homing_state
            self.node.get_logger().info(
                f'[Z0] state={self.homing_state} homed={self.has_homed_once} '
                f'kw={_KW_NAMES.get(self.kw_state, "?")} '
                f'wgrip={self.weapon_gripper} wang={self.weapon_target_angle:.1f} '
                f'wenc={self.weapon_angle_current:.1f} '
                f'kw_z={self.kw_z_target} arm_z={arm_z_cmd:.1f} '
                f'z_cur={self.current_z_pos:.1f} '
                f'reentry_y={self.reentry_y_homing} y_in={self.sw_y_in} '
                f'joyO={joy[1]} preO={self.pre_o_value}'
            )

        # --- Publish weapon command ---
        weapon_msg = Int8MultiArray()
        weapon_msg.data = [self.weapon_gripper, 0]
        self.weapon_cmd_publisher.publish(weapon_msg)

        # --- Publish weapon angle ---
        angle_msg = Float32()
        angle_msg.data = self.weapon_target_angle
        self.weapon_angle_publisher.publish(angle_msg)
        if self.weapon_target_angle != self._last_published_angle:
            self.node.get_logger().info(
                f'[Z0] /weapon_angle_cmd = {self.weapon_target_angle:.2f}'
            )
            self._last_published_angle = self.weapon_target_angle

        # --- Publish zone (PS override → zone 5 = solid-red NeoPixel) ---
        zone_msg = Int8()
        zone_msg.data = 5 if self.ps_neo_active else 0
        self.zone_publisher.publish(zone_msg)

        return Status.SUCCESS
