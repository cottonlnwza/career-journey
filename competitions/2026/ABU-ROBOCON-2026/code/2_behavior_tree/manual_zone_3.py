import py_trees
from py_trees.common import Status,Access
from std_msgs.msg import Int8MultiArray, Float32MultiArray, Int8

class manual_zone3(py_trees.behaviour.Behaviour):
    def __init__(self, name= 'manual_zone3'):
        super(manual_zone3,self).__init__(name)

        self.weapon_L = 0

        self.min_j1 = 0.0 # in meter
        self.max_j1 = 45.0 

        self.min_j2 = 0.0
        self.max_j2 = 0.5

        self.arm_j1 = 0.0
        self.arm_j2 = 0.0

        self.arm_j1_speed = 0.05
        self.arm_j2_speed = 0.05

        self.kfs_gripper = 0

        self.joy_value_button = [0 for _ in range(15)]
        self.pre_L2_value = self.joy_value_button[5]

        self.blackboard = self.attach_blackboard_client(name=self.name)
        self.blackboard.register_key(key='joy_msg_button', access=Access.READ)

    def setup(self, **kwargs):
        self.node = kwargs.get('node')
        if not self.node:
            raise KeyError("ROS node not found in kwargs")
        
        self.weapon_cmd_publisher = self.node.create_publisher(Int8MultiArray, 'weapon_cmd', 10)
        self.arm_kfs_pubblisher = self.node.create_publisher(Float32MultiArray,'arm_kfs_cmd',10)
        self.zone_publisher = self.node.create_publisher(Int8, 'r1_current_zone', 10)

    def limit_arm_joint(self,value,min,max):
        if value < min:
            return float(min)
        elif value > max:
            return float(max)
        return float(value)
    
    def update(self):
        self.joy_value_button = self.blackboard.joy_msg_button

        if self.joy_value_button[12] == 1:  # Touchpad → release weapon L
            self.weapon_L = 0

        msg = Int8MultiArray()
        msg.data = [self.weapon_L, 0]  # motor=0: no motor control in zone 3
        self.weapon_cmd_publisher.publish(msg)

        if self.joy_value_button[2] == 1: # tri press to j1++
            self.arm_j1 += self.arm_j1_speed
        if self.joy_value_button[0] == 1:
            self.arm_j1 -= self.arm_j1_speed # X press to j1--

        if self.joy_value_button[3] == 1: # sq press to j2--
            self.arm_j2 -= self.arm_j2_speed
        if self.joy_value_button[1] == 1: # cir prees to j2++
            self.arm_j2 += self.arm_j2_speed

        if self.joy_value_button[5] == 1 and self.pre_L2_value == 0:  # L2 toggle kfs gripper
            self.kfs_gripper ^= 1

        self.arm_j1 = self.limit_arm_joint(self.arm_j1,self.min_j1,self.max_j1)
        self.arm_j2 = self.limit_arm_joint(self.arm_j2,self.min_j2,self.max_j2)

        msg = Float32MultiArray()
        msg.data = [self.arm_j1, self.arm_j2, float(self.kfs_gripper), 0.0]
        self.arm_kfs_pubblisher.publish(msg)

        ms = Int8()
        ms.data = 3
        self.zone_publisher.publish(ms)

        self.pre_L2_value = self.joy_value_button[5]

        return Status.SUCCESS