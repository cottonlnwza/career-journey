import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped
from rclpy.qos import QoSProfile, ReliabilityPolicy
import math

class LidarObjectDetector(Node):
    def __init__(self):
        super().__init__('lidar_object_dectect')

        self.flip_lidar = False
        self.max_distance = 2.0 # max_dis_to_detect
        self.jump_threadshold = 0.41 # value jump (m)

        self.box_min_w = 0.20
        self.box_max_w = 0.80

        self.r2_min_w = 0.2
        self.r2_max_w = 0.80

        self.divisor = 4.0

        

        qos_profile = QoSProfile(
            reliability= ReliabilityPolicy.BEST_EFFORT,
            depth=10
        )

        self.create_subscription(LaserScan,'/scan',self.scan_call_back,qos_profile)

        self.pub_scan = self.create_publisher(LaserScan,'clean_scan',qos_profile)
        self.tf_broadcaster = TransformBroadcaster(self)


    def get_xy(self, index, radius, angle_min, angle_increment):
        angle = angle_min + index * angle_increment
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        return x,y
    
    def publish_tf(self,cluster, child_frame_id, msg):
        mid = len(cluster) // 2
        tx, ty = self.get_xy(cluster[mid][0], cluster[mid][1] ,msg.angle_min, msg.angle_increment)

        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = msg.header.frame_id
        t.child_frame_id = child_frame_id
        t.transform.translation.x = tx
        t.transform.translation.y = ty
        t.transform.rotation.y = 1.0
        self.tf_broadcaster.sendTransform(t)

    def scan_call_back(self,msg):
        # 1. Calculate Index Ranges
        # Box Zone: -20 to -160 degrees
        idx_box_start = int((math.radians(-20.0) - msg.angle_min) / msg.angle_increment)
        idx_box_end = int((math.radians(-160.0) - msg.angle_min) / msg.angle_increment)
        
        # Robot Zone: 40 to 140 degrees
        idx_robot_start = int((math.radians(40.0) - msg.angle_min) / msg.angle_increment)
        idx_robot_end = int((math.radians(140.0) - msg.angle_min) / msg.angle_increment)

        # Sort indices to ensure start < end for the range logic
        box_indices = sorted([idx_box_start, idx_box_end])
        robot_indices = sorted([idx_robot_start, idx_robot_end])

        # 2. Divide and Clean Scan (Visualizing)
        new_scan = msg
        new_scan.ranges = [
            (r / self.divisor) if (0.0 < r < float('inf')) else r 
            for r in msg.ranges
        ]
        self.pub_scan.publish(new_scan)
        
        ranges = new_scan.ranges[::-1] if self.flip_lidar else new_scan.ranges

        # 3. Clustering Logic
        clusters = []
        current_cluster = []

        for i, r in enumerate(ranges):
            # Check validity and distance
            if math.isinf(r) or math.isnan(r) or r < msg.range_min or r > msg.range_max or r > self.max_distance:
                if len(current_cluster) >= 3:
                    clusters.append(current_cluster)
                current_cluster = []
                continue

            # Clustering by jump threshold
            if not current_cluster:
                current_cluster.append((i, r))
            else:
                _, last_r = current_cluster[-1]
                if abs(r - last_r) < self.jump_threadshold:
                    current_cluster.append((i, r))
                else:
                    if len(current_cluster) >= 3:
                        clusters.append(current_cluster)
                    current_cluster = [(i, r)]

        if len(current_cluster) >= 3:
            clusters.append(current_cluster)

        # 4. Filter Clusters by Zone and Width
        best_box = None
        min_dist_box = float('inf')
        best_robot = None
        min_dist_robot = float('inf')

        for c in clusters:
            mid_idx = c[len(c)//2][0] # Use middle point of cluster to determine its zone
            
            x1, y1 = self.get_xy(c[0][0], c[0][1], msg.angle_min, msg.angle_increment)
            x2, y2 = self.get_xy(c[-1][0], c[-1][1], msg.angle_min, msg.angle_increment)
            width = math.sqrt((x2-x1)**2 + (y2-y1)**2)
            avg_dist = sum(pt[1] for pt in c) / len(c)

            # --- Zone 1: Box Detection ---
            if box_indices[0] <= mid_idx <= box_indices[1]:
                if self.box_min_w <= width <= self.box_max_w:
                    if avg_dist < min_dist_box:
                        min_dist_box = avg_dist
                        best_box = c

            # --- Zone 2: Robot Detection ---
            elif robot_indices[0] <= mid_idx <= robot_indices[1]:
                if self.r2_min_w <= width <= self.r2_max_w:
                    if avg_dist < min_dist_robot:
                        min_dist_robot = avg_dist
                        best_robot = c
        
        # 5. Publish Transforms
        if best_box:
            self.publish_tf(best_box, 'target_box', msg)
        
        if best_robot:
            self.publish_tf(best_robot, 'target_r2', msg)

def main(args=None):
    rclpy.init(args=args)
    node = LidarObjectDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()