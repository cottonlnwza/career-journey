import rclpy
from rclpy.node import Node
from std_msgs.msg import Int8MultiArray,Float32MultiArray,Bool
from sensor_msgs.msg import JointState

class arm_kfs_controller(Node):
    def __init__(self):
        super().__init__('arm_kfs_controller')

        self.declare_parameter('arm_kfs_speed',1.0)

        self.arm_cmd = [0.0,1.0,0,0]
        #self.cmd = [0,0,0,0,0,0]

        # [pose_y, pose_z, kfs_griper, conveyer_status]
        self.create_subscription(Float32MultiArray,'arm_kfs_cmd',self.get_arm_kfs_cmd,10)

        self.create_publisher(Float32MultiArray,'arm_kfs_pos',10)
        self.publisher_ = self.create_publisher(JointState,'joint_states',10)
        self.publisher_kfs_gripper = self.create_publisher(Int8MultiArray,'kfs_gripper_conveyer_state',10)
        self.publisher_kfs_arm = self.create_publisher(Float32MultiArray,'kfs_arm_pose',10)
        self.timer = self.create_timer(0.05, self.broadcast_timer_callback)


    def get_arm_kfs_cmd(self,msg):
        self.arm_cmd = msg.data


    def broadcast_timer_callback(self):

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
    
        # List ALL joints in the chain here
        msg.name = ['joint_arm_kfs_j1', 'joint_arm_kfs_j2']
    
        # Provide positions for both joints
        # Note: Ensure these names match the 'joint name' in your arm_kfs.xacro
        msg.position = [float(self.arm_cmd[0]), float(self.arm_cmd[1])] 

        # Only publish ONCE per cycle
        self.publisher_.publish(msg)

        #arm_msg = Float32MultiArray()
        #arm_msg.data = [float(self.arm_cmd[0]), float(self.arm_cmd[1])]
        #self.publisher_kfs_arm.publish(arm_msg)

        #ms = Int8MultiArray()
        #ms.data = [int(self.arm_cmd[2]),int(self.arm_cmd[3])]
        #self.publisher_kfs_gripper.publish(ms)

def main():
    rclpy.init()
    node = arm_kfs_controller()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()