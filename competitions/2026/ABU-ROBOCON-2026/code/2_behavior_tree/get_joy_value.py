import rclpy
import py_trees
from py_trees.common import Status, Access
from sensor_msgs.msg import Joy
from std_msgs.msg import Bool

class get_joy_value(py_trees.behaviour.Behaviour):
    def __init__(self, name="GetJoyValue"):
        super(get_joy_value, self).__init__(name)
        self.joy_value_analog = [0 for _ in range(8)]
        self.joy_value_button = [0 for _ in range(15)]
        self.joy_value_button_state = [0 for _ in range(15)]
        self.is_emergency_pressed = False
        self.is_joy_connected = False
        self.current_zone = 0

        self.blackboard = self.attach_blackboard_client(name=self.name)
        self.blackboard.register_key(key='joy_msg_analog', access=Access.WRITE)
        self.blackboard.register_key(key='joy_msg_button', access=Access.WRITE)
        self.blackboard.register_key(key='joy_msg_state', access=Access.WRITE)
        self.blackboard.register_key(key='Is_E_Stop_Activate', access=Access.WRITE)
        self.blackboard.register_key(key='In_Zone', access=Access.WRITE)


    def setup(self, **kwargs):
        try:
            self.node = kwargs['node']
        except KeyError:
            raise KeyError("Not found 'node' in kwargs. Please provide a ROS node to the behaviour.")
        self.subscriber = self.node.create_subscription(Joy, 'joy_controller_value', self.joy_callback, 10)
        self.subscriber_emer = self.node.create_subscription(Bool, 'is_emergency_pressed', self.emergency_callback, 10)
        self.subscriber_joy_connection = self.node.create_subscription(Bool, 'joy_is_connection', self.joy_connection_callback, 10)

    def joy_callback(self, msg):
        self.joy_value_analog = self.filter_noise(msg.axes)
        self.joy_value_analog[7] = -self.joy_value_analog[7]
        self.joy_value_button = msg.buttons[:14]
        self.joy_value_button_state = msg.buttons[14:]

    def filter_noise(self,analog):
        low = 20
        for i in range(len(analog)-2):
            if analog[i] < low and analog[i] > -low:
                analog[i] = 0
        return analog
        
    def emergency_callback(self, msg):
        self.is_emergency_pressed = msg.data

    def joy_connection_callback(self, msg):
        self.is_joy_connected = msg.data

    def set_zone_robot(self):
        if self.joy_value_analog[7] == -1:
            self.current_zone = 0
        elif self.joy_value_analog[6] == 1:
            self.current_zone = 1
        elif self.joy_value_analog[7] == 1:
            self.current_zone = 2
        elif self.joy_value_analog[6] == -1:
            self.current_zone = 3
         

    def update(self):
        self.blackboard.joy_msg_analog = self.joy_value_analog
        self.blackboard.joy_msg_button = self.joy_value_button
        self.blackboard.joy_msg_state = self.joy_value_button_state
        self.blackboard.Is_E_Stop_Activate = self.is_emergency_pressed or not self.is_joy_connected
        self.set_zone_robot()
        self.blackboard.In_Zone = self.current_zone
        #print(self.blackboard.Is_E_Stop_Activate)

        return Status.SUCCESS