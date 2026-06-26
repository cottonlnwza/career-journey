import py_trees
from py_trees.common import Status, Access
from std_msgs.msg import Int8MultiArray, Int8, Float32MultiArray

# Button index map (evdev → Joy.buttons[], verified from joy_main.py button_keys order):
# [0]=Circle  [1]=Triangle  [2]=Square   [3]=L1       [4]=R1
# [5]=L2      [6]=R2        [7]=Share    [8]=Options  [9]=PS logo
# [10]=L3     [11]=R3       [12]=Touchpad
# Note: X/Cross (evdev 304) is absent from button_keys — not available in Joy.buttons

class manual_zone1(py_trees.behaviour.Behaviour):
    def __init__(self, name='manual_zone1'):
        super(manual_zone1, self).__init__(name)
        self.joy_value_button = [0 for _ in range(15)]

        self.min_j1 = 0.0
        self.max_j1 = 45.0
        self.min_j2 = -2.0
        self.max_j2 = 2.5

        self.arm_j1 = 0.0
        self.arm_j2 = 0.0

        self.arm_j1_speed = 0.05
        self.arm_j2_speed = 0.05

        self.output_L = 0  # L gripper state (0=open, 1=closed)

        self.blackboard = self.attach_blackboard_client(name=self.name)
        self.blackboard.register_key(key='joy_msg_button', access=Access.READ)

    def setup(self, **kwargs):
        self.node = kwargs.get('node')
        if not self.node:
            raise KeyError("ROS node not found in kwargs")
        self.weapon_cmd_publisher = self.node.create_publisher(Int8MultiArray, 'weapon_cmd', 10)
        self.zone_publisher = self.node.create_publisher(Int8, 'r1_current_zone', 10)
        self.arm_kfs_pubblisher = self.node.create_publisher(Float32MultiArray, 'arm_kfs_cmd', 10)

    def update(self):
        joy_buttons = self.blackboard.joy_msg_button

        # --- L weapon gripper ---
        if joy_buttons[5] == 1:    # L2 → activate gripper
            self.output_L = 1
        elif joy_buttons[9] == 1:  # PS logo → release gripper
            self.output_L = 0

        # --- L weapon motor (manual directional) ---
        if joy_buttons[0] == 1:    # Circle → motor CCW
            motor_L = -1
        elif joy_buttons[2] == 1:  # Square → motor CW
            motor_L = 1
        else:
            motor_L = 0

        # --- Arm J1 (linear extension) ---
        if joy_buttons[4] == 1:    # R1 → arm_j1++
            self.arm_j1 += self.arm_j1_speed
        if joy_buttons[7] == 1:    # Share/Create → arm_j1--
            self.arm_j1 -= self.arm_j1_speed

        # --- Arm J2 (rotation) ---
        if joy_buttons[3] == 1:    # L1 → arm_j2--
            self.arm_j2 = -1.5
        elif joy_buttons[1] == 1:  # Triangle → arm_j2++
            self.arm_j2 = 1.5
        else:
            self.arm_j2 = 0.0

        # --- Publish weapon_cmd: [L_gripper, L_motor] ---
        msg = Int8MultiArray()
        msg.data = [int(self.output_L), motor_L]
        self.weapon_cmd_publisher.publish(msg)

        # --- Publish arm ---
        arm = Float32MultiArray()
        arm.data = [float(self.arm_j1), float(self.arm_j2), 0.0, 0.0]
        self.arm_kfs_pubblisher.publish(arm)

        # --- Publish zone ---
        ms = Int8()
        ms.data = 1
        self.zone_publisher.publish(ms)

        return Status.SUCCESS

    def limit_arm_joint(self, value, min, max):
        if value < min:
            return float(min)
        elif value > max:
            return float(max)
        return float(value)
