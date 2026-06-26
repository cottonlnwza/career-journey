import py_trees
from py_trees.common import Status, Access
from sensor_msgs.msg import Imu
from geometry_msgs.msg import TwistStamped
import math


class MecanumDrive(py_trees.behaviour.Behaviour):
    def __init__(self,name="MecanumDrive"):
        super(MecanumDrive, self).__init__(name)

        # get value from blackboard
        self.blackboard = self.attach_blackboard_client(name=self.name)
        self.blackboard.register_key(key='joy_msg_analog', access=Access.READ)
        self.blackboard.register_key(key='joy_msg_state', access=Access.READ)
        self.blackboard.register_key(key='joy_msg_button', access=Access.READ)
        self.blackboard.register_key(key='In_Zone',        access=Access.READ)
        
        self.kp = 1.0
        self.ki = 0.0
        self.kd = 0.0


        self.prev_error = 0.0
        self.integral = 0.0
        self.tolerance = math.radians(1.5)  # degree tolerance for turning


        self.imu_z_degree = 0.0
        self.last_time = None

        self.is_turn_pid = False
        self.set_pid_degree = [math.radians(0), 
                               math.radians(90), 
                               math.radians(180), 
                               math.radians(270)]
        self.degree_semi_set = 0

    def setup(self, **kwargs):
        try:
            self.node = kwargs['node']
        except KeyError:
            raise KeyError("Not found 'node' in kwargs. Please provide a ROS node to the behaviour.")

        self.publisher = self.node.create_subscription(Imu, 'Imu_robot', self.get_imu,10)
        self.publisher_cmd_vel = self.node.create_publisher(TwistStamped, 'mecanum_drive_controller/cmd_vel', 10)


    def get_imu(self, msg):
        q = msg.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        self.imu_z_degree = math.atan2(siny_cosp, cosy_cosp) # in radians


    def cal_turn_pid(self, target_degree):
        now = self.node.get_clock().now()
        if self.last_time is None:
            self.last_time = now
            return 0.0
        
        dt = (now - self.last_time).nanoseconds / 1e9
        if dt <= 0:
            return 0.0
        
        error = target_degree - self.imu_z_degree
        error = math.atan2(math.sin(error), math.cos(error))  # Normalize error to [-pi, pi]


        self.integral += error * dt
        derivative = (error - self.prev_error) / dt

        if abs(error) < self.tolerance:
            self.integral = 0.0  # Reset integral when within tolerance

        output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)

        self.prev_error = error
        self.last_time = now
        return output

    def map_range(self,value,in_min,in_max,out_min,out_max):
        return float(out_min + (value - in_min) * (out_max - out_min)/(in_max-in_min))

    def turn_in_semi(self,joy_zx, joy_zy):
        # Map joystick input to motor speeds
        joy_zx = self.map_range(joy_zx, -1.0, 1.0, -255.0, 255.0)
        joy_zy = self.map_range(joy_zy, -1.0, 1.0, -255.0, 255.0)

        if joy_zy >= 0.7:
            self.degree_semi_set = 0
        elif joy_zx >= 0.7:
            self.degree_semi_set = 1
        elif joy_zy <= -0.7:
            self.degree_semi_set = 2
        elif joy_zx <= -0.7:
            self.degree_semi_set = 3

        turn_v = self.cal_turn_pid(self.set_pid_degree[self.degree_semi_set])
       
        return turn_v
    
    def drive_in_semi(self,joy_x, joy_y):
        # Map joystick input to motor speeds
        joy_x = self.map_range(joy_x, -1.0, 1.0, -255.0, 255.0)
        joy_y = self.map_range(joy_y, -1.0, 1.0, -255.0, 255.0)

        x_v = joy_x * math.cos(self.imu_z_degree) - joy_y * math.sin(self.imu_z_degree)
        y_v = joy_x * math.sin(self.imu_z_degree) + joy_y * math.cos(self.imu_z_degree)

        return x_v, y_v
    
    def turn_in_manual(self, joy_z):
        # Map joystick input to motor speeds
        turn_v = self.map_range(joy_z, -255.0, 255.0, -10.0, 10.0)

        return turn_v
    
    def drive_in_manual(self,joy_x, joy_y):
        # Map joystick input to motor speeds
        x_v = self.map_range(joy_x, -255.0, 255.0, -10.0, 10.0)
        y_v = self.map_range(joy_y, -255.0, 255.0, -10.0, 10.0)

        return x_v, y_v


    def update(self):
        joy_msg_analog = self.blackboard.joy_msg_analog
        joy_msg_state = self.blackboard.joy_msg_state
        joy_msg_button = self.blackboard.joy_msg_button

        turn_v = self.turn_in_manual(joy_msg_analog[2])
        x_v, y_v = self.drive_in_manual(joy_msg_analog[1], joy_msg_analog[0])

        # Zone 1: invert forward/backward only (strafe and rotation unchanged)
        try:
            if self.blackboard.In_Zone == 1:
                y_v = -y_v
                x_v = -x_v
        except KeyError:
            pass

        # Slowmode: hold L2[8] → divide all drive speeds by 3
        if joy_msg_button[8] == 1:
            x_v /= 3.0
            y_v /= 3.0
            turn_v /= 3.0

        msg = TwistStamped()
        msg.header.stamp = self.node.get_clock().now().to_msg()
        msg.header.frame_id = "base_link"

        msg.twist.linear.x = x_v
        msg.twist.linear.y = y_v
        msg.twist.angular.z = turn_v
        self.publisher_cmd_vel.publish(msg)
        return Status.SUCCESS