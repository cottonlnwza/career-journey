import py_trees
from py_trees.common import Status,Access
from std_msgs.msg import Float32MultiArray, Int8

class manual_zone2(py_trees.behaviour.Behaviour):
    def __init__(self, name='manual_zone2_control'):
        super(manual_zone2, self).__init__(name)

        self.joy_value_button = [0 for _ in range(15)]

        self.min_j1 = 0.0 # in meter
        self.max_j1 = 47.5

        self.min_j2 = -2.0
        self.max_j2 = 2.5

        self.arm_j1 = 0.0
        self.arm_j2 = 0.0

        self.arm_j1_speed = 0.25
        self.arm_j2_speed = 0.25

        self.kfs_gripper = 0

        self.pre_L2_value = self.joy_value_button[5]

        self.blackboard = self.attach_blackboard_client(name=self.name)
        self.blackboard.register_key(key='joy_msg_button', access=Access.READ)

    def setup(self, **kwargs):
        try:
            self.node = kwargs['node']
        except KeyError:
           raise KeyError("Not found 'node' in kwargs. Please provide a ROS node to the behaviour.")
    
        self.arm_kfs_pubblisher = self.node.create_publisher(Float32MultiArray,'arm_kfs_cmd',10)
        self.zone_publisher = self.node.create_publisher(Int8, 'r1_current_zone', 10)

    def get_joy_value(self):
        
        self.joy_value_button = self.blackboard.joy_msg_button

        #print(self.joy_value_button)

    def limit_arm_joint(self,value,min,max):
        if value < min:
            return float(min)
        elif value > max:
            return float(max)
        return float(value)

    def update(self):
        self.get_joy_value()

        if self.joy_value_button[4] == 1: # tri press to j1++
            self.arm_j1 += self.arm_j1_speed
        if self.joy_value_button[7] == 1:
            self.arm_j1 -= self.arm_j1_speed # X press to j1--

        if self.joy_value_button[3] == 1: # sq press to j2--
            self.arm_j2 = -1.5#-= self.arm_j2_speed
        elif self.joy_value_button[1] == 1: # cir prees to j2++
            self.arm_j2 = 1.5#self.arm_j2_speed
        else:
            self.arm_j2 = 0.0

        if self.joy_value_button[5] == 1 and self.pre_L2_value == 0:
            self.kfs_gripper ^= 1

        self.arm_j1 = self.limit_arm_joint(self.arm_j1,self.min_j1,self.max_j1)
        self.arm_j2 = self.limit_arm_joint(self.arm_j2,self.min_j2,self.max_j2)

        msg = Float32MultiArray()
        msg.data = [self.arm_j1, self.arm_j2, float(self.kfs_gripper), 0.0]
        self.arm_kfs_pubblisher.publish(msg)

        ms = Int8()
        ms.data = 2
        self.zone_publisher.publish(ms)

        self.pre_L2_value = self.joy_value_button[5]
        return Status.SUCCESS