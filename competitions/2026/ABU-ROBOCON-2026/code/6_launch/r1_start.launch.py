import os
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node

def generate_launch_description():

    pkg_name_urdf = "r1_urdf"
    pkg_name_bringup = "r1_bringup"
    pkg_name_dashboard = "gui_dashboard"
    pkg_name_upper_base_control = "r1_upper_base_control_py"
    pkg_name_lidar = "ydlidar_ros2_driver"

    default_robot_name = "r1"

    # set path 
    #pkg_share_urdf = FindPackageShare(package=pkg_name_urdf).find(pkg_name_urdf)
    #pkg_share_bringup = FindPackageShare(package=pkg_name_bringup).find(pkg_name_bringup)
    #pkg_share_dashboard = FindPackageShare(package=pkg_name_dashboard).find(pkg_name_dashboard)
    
    pkg_share_urdf = get_package_share_directory(pkg_name_urdf)
    pkg_share_bringup = get_package_share_directory(pkg_name_bringup)
    # pkg_share_dashboard = get_package_share_directory(pkg_name_dashboard)
    pkg_share_r1_upper_base_control = get_package_share_directory(pkg_name_upper_base_control)
    #pkg_share_r1_lidar = get_package_share_directory(pkg_name_lidar)

    default_riviz_config_path = PathJoinSubstitution(
        [pkg_share_urdf, 'config', 'r1_run.rviz']
    )
    # Launch configuration variables
    enable_odom_tf = LaunchConfiguration('enable_odom_tf')
    jsp_gui = LaunchConfiguration('jsp_gui')
    load_ros_controller = LaunchConfiguration('load_ros_controller')
    rviz_config_file = LaunchConfiguration('rviz_config_file')
    robot_name = LaunchConfiguration('robot_name')
    use_rzviz = LaunchConfiguration('use_rviz')
    use_robot_state_publisher = LaunchConfiguration('use_robot_state_publisher')
    use_sim_time = LaunchConfiguration('use_sim_time')

    # declare launch arguments
    delcare_enable_odom_tf_cmd = DeclareLaunchArgument(
        name='enable_odom_tf',
        default_value='true',
        choices=['true', 'false'],
        description='Whether to enable odometry transform broadcasting via ROS 2 Control')

    declare_jsp_gui_cmd = DeclareLaunchArgument(
        name='jsp_gui',
        default_value='false',
        choices=['true', 'false'],
        description='Whether to enable the Joint State Publisher GUI')
    
    declare_load_ros_controller_cmd = DeclareLaunchArgument(
        name='load_ros_controller',
        default_value='true',
        description='Whether to load ROS 2 Control controllers')
    
    declare_rviz_config_file_cmd = DeclareLaunchArgument(
        name='rviz_config_file',
        default_value=default_riviz_config_path,
        description='Full path to the RVIZ config file to use')
    
    declare_robot_name_cmd = DeclareLaunchArgument(
        name='robot_name',
        default_value=default_robot_name,
        description='Name of the robot to be used in TF frames and topics')
    
    declare_use_rviz_cmd = DeclareLaunchArgument(
        name='use_rviz',
        default_value='true',
        choices=['true', 'false'],
        description='Whether to start RVIZ')
    
    declare_use_robot_state_publisher_cmd = DeclareLaunchArgument(
        name='use_robot_state_publisher',
        default_value='true',
        choices=['true', 'false'],
        description='Whether to start the Robot State Publisher')
    
    declare_use_sim_time_cmd = DeclareLaunchArgument(
        name='use_sim_time',
        default_value='false',
        choices=['true', 'false'],
        description='Whether to use simulation time')
    
    # Include the robot state publisher launch file
    robot_state_publisher_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_share_urdf, 'launch', 'robot_state_publisher.launch.py')
        ]),
        launch_arguments={
            'enable_odom_tf': enable_odom_tf,
            'jsp_gui': jsp_gui,
            'rviz_config_file': rviz_config_file,
            'use_rviz': use_rzviz,
            'use_sim_time': use_sim_time,
        }.items(),
        condition=IfCondition(use_robot_state_publisher)
    )

    # Include the ROS 2 controller launch file
    load_ros2_controller_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_share_bringup, 'launch', 'load_ros2_controller.launch.py')
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
        }.items(),
        condition=IfCondition(load_ros_controller)
    )

    #load_lidar_launch = IncludeLaunchDescription(
    #    PythonLaunchDescriptionSource([
    #        os.path.join(pkg_share_r1_lidar,'launch', 'ydlidar_launch.py')
    #    ]),
    #    launch_arguments={
    #        'use_sim_time': use_sim_time,
    #    }.items(),
    #)

    bt_node = Node(
        package='r1_bt',
        executable='main_r1_bt',
        name='main_r1_bt',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time}
        ]
    )

    joy = Node(
        package='r1_upper_base_control_py',
        executable='get_joy_value',
        name='get_joy_value',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time}
        ]
    )

    arm_kfs = Node(
        package='r1_upper_base_control_py',
        executable='arm_kfs_controller',
        name='arm_kfs_controller',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time}
        ]
    )

    lidar_ob = Node(
        package='r1_upper_base_control_py',
        executable='lidar_object_detect',
        name='lidar_object_detect',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time}
        ]
    )

    weapon_control = Node(
        package='r1_upper_base_control_py',
        executable='weapon_control',
        name='weapon_control',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time}
        ]
    )

    micro_ros_agent_udp = Node(
        package='micro_ros_agent',
        executable='micro_ros_agent',
        name='micro_ros_agent',
        arguments=['upd4','--port','8888'], # config teensy port
        output='screen'
    )

    micro_ros_agent_serial = Node(
        package='micro_ros_agent',
        executable='micro_ros_agent',
        name='micro_ros_agent',
        arguments=['serial','--dev','/dev/ttyACM0'], # config teensy port
        output='screen'
    )
    

    ld = LaunchDescription()

    # Declare the launch options
    ld.add_action(delcare_enable_odom_tf_cmd)
    ld.add_action(declare_jsp_gui_cmd)
    ld.add_action(declare_load_ros_controller_cmd)
    ld.add_action(declare_rviz_config_file_cmd)
    ld.add_action(declare_robot_name_cmd)
    ld.add_action(declare_use_rviz_cmd)
    ld.add_action(declare_use_robot_state_publisher_cmd)
    ld.add_action(declare_use_sim_time_cmd)

    # Add the actions to launch all of the nodes
    ld.add_action(joy)
    
    #ld.add_action(load_lidar_launch)
    ld.add_action(robot_state_publisher_cmd)
    ld.add_action(load_ros2_controller_cmd)
    
    ld.add_action(lidar_ob)
    ld.add_action(bt_node)
    ld.add_action(weapon_control)
    ld.add_action(arm_kfs)

    # uncomment to select protocal
    #ld.add_action(micro_ros_agent_udp)
    ld.add_action(micro_ros_agent_serial)
    

    return ld