import rclpy
import py_trees
from py_trees.common import Status,Access
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import Float32MultiArray

class Stop_Robot(py_trees.behaviour.Behaviour):
    def __init__(self,name="Stop_Robot"):
        super(Stop_Robot,self).__init__(name)

    def setup(self, **kwargs):
        try:
            self.node = kwargs['node']
        except KeyError:
            raise KeyError("Not found 'node' in kwargs. Please provide a ROS node to the behaviour.")

        self.publisher_cmd_vel = self.node.create_publisher(TwistStamped, 'mecanum_drive_controller/cmd_vel', 10)
        self.publisher_arm_kfs = self.node.create_publisher(Float32MultiArray, 'arm_kfs_pos',10)
        self.publisher_arm_weapon = self.node.create_publisher(Float32MultiArray, 'arm_weapon_pos',10)

    def update(self):
        msg = TwistStamped()
        msg.header.stamp = self.node.get_clock().now().to_msg()
        msg.header.frame_id = "base_link"
        msg.twist.linear.x = 0.0
        msg.twist.linear.y = 0.0
        msg.twist.angular.z = 0.0
        self.publisher_cmd_vel.publish(msg)

        
        return Status.SUCCESS
