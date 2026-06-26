import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from std_msgs.msg import Float32MultiArray,Bool
from tf2_ros import Buffer, TransformListener
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException

import socket
import struct
import threading

class command_and_get_teensy(Node):
    def __init__(self):
        super().__init__('command_and_get_teensy')

        self.robot_ip = '192.168.1.1'
        self.robot_port = 9988

        self.teensy_ip = '192.168.1.2'
        self.teensy_port = 9989

        self.struct_format_recv = '<10f'
        self.expected_sized_recv = struct.calcsize(self.struct_format)

        self.struct_format_sent = '<8f'
        
        
        self.arm_kfs = [0 for i in range(4)]
        self.arm_weapon = [0 for i in range(4)]

        self.arm_x = 0.0
        self.arm_z = 0.0

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        
        
        self.imu_pub = self.create_publisher(Imu,'Imu_robot',10)
        self.is_emer_press = self.create_publisher(Bool,'is_emergency_pressed',10)
        
        
        
        self.arm_kfs_sub = self.create_subscription(Float32MultiArray,'arm_kfs_pos',self.get_arm_kfs,10)
        self.arm_weapon_sub = self.create_subscription(Float32MultiArray, 'arm_weapon_pos', self.get_arm_weapon, 10)

        self.sent_data = [0 for i in range(10)]
        # get sensor from teensy
        self.sock_recv = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.sock_recv.bind((self.robot_ip,self.robot_port))

        self.rx_thread = threading.Thread(target=self.get_teensy, daemon=True)
        self.rx_thread.start()

    def get_arm_kfs(self,msg):
        self.arm_kfs = msg.data

    def get_arm_weapon(self,msg):
        self.arm_weapon = msg.data

    def get_arm_tf(self):
        try:
            now = rclpy.time.Time()
            trans = self.tf_buffer.lookup_transform(
                'body_link',
                'arm_kfs_j2',
                now,
                timeout=rclpy.duration.Duration(seconds=0.2)
            )

            self.arm_x = trans._transform.translation.x
            self.arm_z = trans._transform.translation.z

        except (LookupException, ConnectivityException, ExtrapolationException) as e:
            self.get_logger().info(f'Could not transform: {e}')


    def get_teensy(self):
        while rclpy.ok():
            try:
                data,addr = self.sock_recv.recv(1024)

                if addr[0] != self.teensy_ip:
                    continue

                if len(data) == self.expected_sized_recv:

                    sensor_value = struct.unpack(self.struct_format_recv, data)

                    print(sensor_value)
                
                else:
                    self.get_logger().warn('sensor packet size error!!')
            except Exception as e:
                self.get_logger().error(f'teensy rx error : {e}')

    
    def cmd_actuator(self):
        try:
            packed_bytes = struct.pack(self.struct_format_sent,self.sent_data[0],self.sent_data[1])

            self.sock_recv.sendto(packed_bytes, (self.teensy_ip,self.teensy_port))

        except Exception as e:
            self.get_logger().error(f'teensy tx error : {e}')


def main(args=None):
    rclpy.init(args=args)
    node = command_and_get_teensy()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
                

