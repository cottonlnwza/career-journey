# launch ros2 controllers for mecanum drive
""""
from launch import LaunchDescription
from launch.actions import ExecuteProcess, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit

def generate_launch_description():
    # start mecanum drive controller
    start_mecanum_drive_controller_cmd = ExecuteProcess(
        cmd=['ros2', 'control', 'load_start_controller', '--set-state', 'active',
             'mecanum_drive_controller'],
        output='screen'
    )

    # start joint state broadcaster
    start_joint_state_broadcaster_cmd = ExecuteProcess(
        cmd=['ros2', 'control', 'load_start_controller', '--set-state', 'active',
             'joint_state_broadcaster'],
        output='screen'
    )

    # delay to joint state broadcaster
    delayed_start = TimerAction(
        period=25.0,
        actions=[start_joint_state_broadcaster_cmd]
    )

    # register event handler to start mecanum drive controller after joint state broadcaster
    load_joint_state_broadcaster_cmd = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=start_joint_state_broadcaster_cmd,
            on_exit=[start_mecanum_drive_controller_cmd],
        )
    )

    # Create the launch description and populate
    ld = LaunchDescription()

    ld.add_action(delayed_start)
    ld.add_action(load_joint_state_broadcaster_cmd)
    return ld"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessStart

def generate_launch_description():

    # 1. Spawner สำหรับ Joint State Broadcaster
    # ตัว Spawner จะรอให้ /controller_manager service ขึ้นมาเองโดยอัตโนมัติ
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
    )

    # 2. Spawner สำหรับ Mecanum Drive Controller
    mecanum_drive_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["mecanum_drive_controller", "--controller-manager", "/controller_manager"],
    )

    #delay_mecanum_drive_controller_spawner = TimerAction(
    #    period=2.0,
    #    actions=[mecanum_drive_controller_spawner]
    #)
    delay_mecanum_drive_controller_spawner = RegisterEventHandler(
        event_handler=OnProcessStart(
            target_action=joint_state_broadcaster_spawner, # รอให้ตัวนี้เริ่มทำงานก่อน
            on_start=[mecanum_drive_controller_spawner],   # แล้วค่อยรันตัวขับ Mecanum
        )
    )

    return LaunchDescription([
        joint_state_broadcaster_spawner,
        delay_mecanum_drive_controller_spawner,
    ])