import rclpy
from rclpy.node import Node
from std_msgs.msg import Int8MultiArray, Int8
import time

class WeaponController(Node):
    def __init__(self):
        super().__init__('weapon_controller')

        self.new_L = False
        self.keeper_L_have_staff = False

        # 0: standby, 1: keep, 2: release
        self.mode_L = 0

        self.output_L = [0, 0]  # [gripper(0/1), motor(-1/0/1)]
        self.motor_cmd_L = 0    # passthrough from weapon_cmd[1]

        self.current_zone = 1

        # weapon_cmd format: [L_gripper(0/1), L_motor(-1/0/1)]
        self.create_subscription(Int8MultiArray, 'weapon_cmd', self.get_weapon_cmd, 10)
        self.create_subscription(Int8, 'r1_current_zone', self.get_zone, 10)

        # weapon_pos format: [0]=L_gripper(0/1), [1]=L_motor(-1/0/1)
        self.weapon_publisher = self.create_publisher(Int8MultiArray, 'weapon_pos', 10)
        self.create_timer(0.05, self.timer_callback)

    def get_weapon_cmd(self, msg):
        if len(msg.data) >= 1:
            self.new_L = bool(msg.data[0])
        if len(msg.data) >= 2:
            self.motor_cmd_L = int(msg.data[1])

    def get_zone(self, msg):
        self.current_zone = msg.data

    def keep_sequence(self, side):
        setattr(self, f'output_{side}', [1, self.motor_cmd_L])
        setattr(self, f'mode_{side}', 0)

    def release_sequence(self, side):
        # Deactivate gripper immediately.
        setattr(self, f'output_{side}', [0, self.motor_cmd_L])
        setattr(self, f'mode_{side}', 0)

    def timer_callback(self):
        # Motor is always a passthrough — updates every tick regardless of gripper state.
        self.output_L[1] = self.motor_cmd_L

        # Gripper state machine: trigger on rising/falling edge of new_L
        if self.new_L and not self.keeper_L_have_staff:
            self.mode_L = 1
        elif not self.new_L and self.keeper_L_have_staff:
            self.mode_L = 2

        if self.mode_L == 1:
            self.keep_sequence('L')
        elif self.mode_L == 2:
            self.release_sequence('L')

        msg = Int8MultiArray()
        msg.data = list(self.output_L)
        self.weapon_publisher.publish(msg)

        self.keeper_L_have_staff = self.new_L


def main(args=None):
    rclpy.init(args=args)
    node = WeaponController()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Node stopping... (Keyboard Interrupt)')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
