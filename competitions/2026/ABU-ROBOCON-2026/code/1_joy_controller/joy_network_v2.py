import socket
import json

class JoyNetwork_connection:
    def __init__(self, robot_ip, port_cmd=5001, port_recv=5002):
        self.robot_ip = robot_ip
        self.port_cmd = port_cmd
        self.port_recv = port_recv

        self.sock_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_recv.bind((self.robot_ip, self.port_recv))
        self.sock_recv.settimeout(1.0)

        self.sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def setn_data(self,data_list):
        try:
            payload = json.dumps(data_list).encode('utf-8')
            self.sock_send.sendto(payload, (self.robot_ip, self.port_cmd))
        except Exception as e:
            print(f"Error sending data: {e}")

    def receive_data(self):
        try: 
            data, addr = self.sock_recv.recvfrom(1024)
            return json.loads(data.decode('utf-8'))
        except socket.timeout:
            return None
        except Exception as e:
            print(f"Error receiving data: {e}")
            return None
        
    def close(self):
        self.sock_recv.close()
        self.sock_send.close()