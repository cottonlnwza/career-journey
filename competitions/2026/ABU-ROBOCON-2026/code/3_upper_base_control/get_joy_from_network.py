import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import Bool
import threading
import socket
import time
import json


class JoyReceiver(Node):
    def __init__(self):
        super().__init__('get_joy_value')

        # =========================
        # Network settings
        # =========================
        self.host = '0.0.0.0'      # รับจากทุก interface
        self.port_recv = 12345     # port ที่ Pi ส่งเข้ามา
        self.port_send = 12346     # port สำหรับส่ง ack กลับ Pi

        self.get_logger().info(f"Starting JoyReceiver on {self.host}:{self.port_recv}")

        # =========================
        # UDP sockets
        # =========================
        self.sock_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_recv.bind((self.host, self.port_recv))
        self.sock_recv.settimeout(0.2)   # สั้นลง เพื่อให้ loop responsive ขึ้น

        self.sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # =========================
        # Connection / timeout
        # =========================
        self.last_sender_ip = None
        self.last_sender_port = None

        # ใช้ monotonic สำหรับ timeout จะนิ่งกว่า time.time()
        self.last_received_time = time.monotonic()
        self.connection_timeout = 2.0   # เริ่มจาก 2.0 ก่อน เพื่อลดอาการหลุด

        self.is_connected = False

        # =========================
        # Joy message layout
        # =========================
        self.num_axes = 8

        # สำหรับ debug
        self.last_seq = -1
        self.last_debug_time = time.monotonic()

        # =========================
        # ROS publishers
        # =========================
        self.joy_pub = self.create_publisher(Joy, 'joy_controller_value', 10)
        self.joy_is_connection = self.create_publisher(Bool, 'joy_is_connection', 10)

        # timer ตรวจการเชื่อมต่อ
        self.timer_check_connection = self.create_timer(0.2, self.timer_connection_check)

        # thread รับ UDP
        self.receive_thread = threading.Thread(target=self.receive_joy_data, daemon=True)
        self.receive_thread.start()

        self.get_logger().info("Ready JoyReceiver")

    def receive_joy_data(self):
        while rclpy.ok():
            try:
                data, addr = self.sock_recv.recvfrom(4096)

                now = time.monotonic()
                self.last_received_time = now
                self.last_sender_ip = addr[0]
                self.last_sender_port = addr[1]

                if not self.is_connected:
                    self.get_logger().info(f"Connected to {addr}")
                    self.is_connected = True

                raw_data = json.loads(data.decode('utf-8'))

                # =========================
                # รองรับ payload แบบใหม่จาก Pi:
                # {"seq": ..., "t": ..., "data": [...]}
                # =========================
                if isinstance(raw_data, dict) and "data" in raw_data:
                    packet = raw_data["data"]
                    seq = raw_data.get("seq", -1)
                    sender_time = raw_data.get("t", None)

                    # debug ว่ามี packet ข้ามหรือไม่
                    if self.last_seq != -1 and seq != self.last_seq + 1:
                        self.get_logger().warning(
                            f"Packet jump detected: prev_seq={self.last_seq}, new_seq={seq}"
                        )

                    self.last_seq = seq

                    if isinstance(packet, list):
                        msg = Joy()
                        msg.header.stamp = self.get_clock().now().to_msg()
                        msg.axes = [float(val) for val in packet[:self.num_axes]]
                        msg.buttons = [int(val) for val in packet[self.num_axes:]]
                        self.joy_pub.publish(msg)

                        # debug เป็นระยะ ๆ ไม่พิมพ์ทุก packet
                        if now - self.last_debug_time >= 1.0:
                            self.get_logger().info(
                                f"Receiving seq={seq}, sender={addr[0]}:{addr[1]}"
                            )
                            self.last_debug_time = now

                # =========================
                # เผื่อยังใช้ format เก่า (list ตรง ๆ)
                # =========================
                elif isinstance(raw_data, list):
                    msg = Joy()
                    msg.header.stamp = self.get_clock().now().to_msg()
                    msg.axes = [float(val) for val in raw_data[:self.num_axes]]
                    msg.buttons = [int(val) for val in raw_data[self.num_axes:]]
                    self.joy_pub.publish(msg)

                    if now - self.last_debug_time >= 1.0:
                        self.get_logger().info(
                            f"Receiving legacy list from {addr[0]}:{addr[1]}"
                        )
                        self.last_debug_time = now

                else:
                    self.get_logger().warning(f"Unknown payload format: {type(raw_data)}")

            except socket.timeout:
                continue
            except json.JSONDecodeError as e:
                self.get_logger().error(f"JSON decode error: {e}")
            except Exception as e:
                self.get_logger().error(f"Error receiving data: {e}")

    def timer_connection_check(self):
        current_time = time.monotonic()
        gap = current_time - self.last_received_time
        alive = gap < self.connection_timeout

        if alive:
            # ส่ง ack กลับไปยัง IP ที่ส่ง packet เข้ามาจริง
            if self.last_sender_ip is not None:
                try:
                    payload = json.dumps("connected").encode('utf-8')
                    self.sock_send.sendto(payload, (self.last_sender_ip, self.port_send))
                except Exception as e:
                    self.get_logger().warning(f"ACK send failed: {e}")
        else:
            if self.is_connected:
                self.get_logger().warning(f"Joy connection lost, gap={gap:.3f}s")
                self.is_connected = False

        msg = Bool()
        msg.data = self.is_connected
        self.joy_is_connection.publish(msg)

    def destroy_node(self):
        try:
            self.sock_recv.close()
        except Exception:
            pass

        try:
            self.sock_send.close()
        except Exception:
            pass

        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    joy_receiver = JoyReceiver()

    try:
        rclpy.spin(joy_receiver)
    except KeyboardInterrupt:
        joy_receiver.get_logger().info("Keyboard Interrupt")
    finally:
        joy_receiver.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()