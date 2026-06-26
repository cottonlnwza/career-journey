import evdev
from evdev import InputDevice, ecodes
import time
import threading
import sys

from joy_network_v2 import JoyNetwork_connection

class JoyController:
    def __init__(self):
        self.robot_ip = '192.168.0.2'
        self.robot_port = 12345
        self.joy_port = 12346

        self.axis_keys = [0, 1, 3, 4, 2, 5, 16, 17]
        self.button_keys = [305, 307, 308, 310, 311, 312, 313, 314, 315, 316, 317, 318, 554]

        self.joy_value = {key: 0 for key in self.axis_keys + self.button_keys}
        self.pre_joy_value = self.joy_value.copy()
        self.button_toggle_state = {key: 0 for key in self.button_keys}

        self.network = JoyNetwork_connection(robot_ip=self.robot_ip, port_cmd=self.robot_port, port_recv=self.joy_port)

        self.joy = None
        self.running = True

        read_thread = threading.Thread(target=self.read_joystick_value, daemon=True)
        send_thread = threading.Thread(target=self.send_data_loop, daemon=True)
        recv_thread = threading.Thread(target=self.receive_data_loop, daemon=True)

        read_thread.start()
        send_thread.start()
        recv_thread.start()

        print("🎮 JoyController is running. Press Ctrl+C to exit.")

    def find_joystick(self):
        devices = [InputDevice(path) for path in evdev.list_devices()]
        for dev in devices:
            cap = dev.capabilities()
            if ecodes.EV_ABS in cap and ecodes.EV_KEY in cap:
                print(f"\n🎮 Joystick connected: {dev.name} at {dev.path}")
                return dev
        print("\n❌ No joystick found. Retrying in 1 second...")
        return None
    
    def _reset_joy_value(self):
        for key in self.joy_value.keys():
            self.joy_value[key] = 0

    def map_range(self, value, in_min, in_max, out_min, out_max):
        return float(out_min + (value - in_min) * (out_max - out_min) / (in_max - in_min))
    
    def read_joystick_value(self):
        while self.running:
            if self.joy is None:
                self.joy = self.find_joystick()
                if self.joy is None:
                    time.sleep(0.5)
                continue

            try:
                for event in self.joy.read_loop():
                    if event.type == ecodes.EV_ABS:
                        if event.code in self.joy_value:
                            if event.code in [1, 4]:
                                self.joy_value[event.code] = self.map_range(event.value, 0, 255, 255, -255)
                            elif event.code in [0, 3]:
                                self.joy_value[event.code] = self.map_range(event.value, 0, 255, -255, 255)
                            else:
                                self.joy_value[event.code] = float(event.value)
                                
                    elif event.type == ecodes.EV_KEY:
                        if event.code in self.joy_value:
                            self.joy_value[event.code] = 1 if event.value else 0
                            
            except OSError:
                print("\n❌ Joystick disconnected!")
                self.joy = None
                self._reset_joy_value()

    def send_data_loop(self):
        while self.running:
            if self.joy is not None:
                for k in self.button_keys:
                    if self.joy_value[k] == 1 and self.pre_joy_value[k] == 0:
                        self.button_toggle_state[k] ^= 1  # XOR
                
                data_list = [self.joy_value[k] for k in self.axis_keys] + \
                            [self.joy_value[k] for k in self.button_keys] + \
                            [self.button_toggle_state[k] for k in self.button_keys]
                
                self.network.setn_data(data_list)
            
            self.pre_joy_value = self.joy_value.copy()
            time.sleep(0.05)

    def receive_data_loop(self):
        while self.running:
            data = self.network.receive_data()
            if data:
                print(f"\n Received from robot: {data}")
            else:
                print("\n No response from robot.")

    def close(self):
        self.running = False
        self.network.close()

if __name__ == "__main__":
    controller = JoyController()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🚪 Exiting JoyController...")
        controller.close()