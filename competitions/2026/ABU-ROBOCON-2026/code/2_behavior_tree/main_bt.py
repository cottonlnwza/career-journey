import rclpy
import py_trees
import py_trees_ros.trees
from py_trees.common import Status

from r1_bt.get_joy_value import get_joy_value
from r1_bt.check_condition import CheckCondition
from r1_bt.base_mecanum_drive import MecanumDrive
from r1_bt.stop_robot import Stop_Robot
from r1_bt.manual_zone_0 import manual_zone0
from r1_bt.manual_zone_1_v2 import manual_zone1_v2
from r1_bt.manual_zone_2_v2 import manual_zone2_v2
from r1_bt.manual_zone_3_v2 import manual_zone3_v2

def create_root():
    # create root node
    root = py_trees.composites.Sequence(name="Main_Sequence",memory=False)

    # ==========================================
    # Update Joy Values
    # ==========================================
    joy = get_joy_value("GetJoyValue")


    # emergency stop branch
    e_stop_mode = py_trees.composites.Sequence(name="E-Stop_Sequence", memory=False)

    e_stop_mode.add_children([
        CheckCondition(name="Is_E_Stop_Activate", blackboard_key_name="Is_E_Stop_Activate", condtion_value=True),
        Stop_Robot("Stop_Robot"),
    ])

    # manual mode branch
    manual_zone_0_seq = py_trees.composites.Sequence(name="Manual_Zone_0_Sequence", memory=False)
    manual_zone_0_seq.add_children([
        CheckCondition(name="Is_Zone_0", blackboard_key_name="In_Zone", condtion_value=0),
        manual_zone0("manual_setup_control"),
    ])

    manual_zone_1_seq = py_trees.composites.Sequence(name="Manual_Zone_1_Sequence", memory=False)
    manual_zone_1_seq.add_children([
        CheckCondition(name="Is_Zone_1", blackboard_key_name="In_Zone", condtion_value=1),
        manual_zone1_v2("manual_staff_arm_control"),
    ])

    manual_zone_2_seq = py_trees.composites.Sequence(name="Manual_Zone_2_Sequence", memory=False)
    manual_zone_2_seq.add_children([
        CheckCondition(name="Is_Zone_2", blackboard_key_name="In_Zone", condtion_value=2),
        manual_zone2_v2("manual_kfs_arm_control"),
    ])

    manual_zone_3_seq = py_trees.composites.Sequence(name="Manual_Zone_3_Sequence", memory=False)
    manual_zone_3_seq.add_children([
        CheckCondition(name="Is_Zone_3", blackboard_key_name="In_Zone", condtion_value=3),
        manual_zone3_v2("put_KFS_weapon_manual_control")
    ])

    manual_select_zone = py_trees.composites.Selector(name="Manual_Mode_Selector", memory=False)
    manual_select_zone.add_children([
        manual_zone_0_seq,
        manual_zone_1_seq,
        manual_zone_2_seq,
        manual_zone_3_seq
    ])

    manual_mode = py_trees.composites.Sequence(name="Manual_Mode_Sequence", memory=False)
    manual_mode.add_children([
        manual_select_zone,
        MecanumDrive("base_drive_control_manual_mode")
    ])

    # ==========================================
    # Seclect semi, manual, emergency stop
    # ==========================================
    mode_selection = py_trees.composites.Selector(name="Mode_Selection", memory=False)
    mode_selection.add_children([
        e_stop_mode,
        manual_mode
    ])

    # ==========================================
    root.add_children([joy,
                       mode_selection
    ])

    return root

def main():
    rclpy.init()

    root = create_root()

    tree = py_trees_ros.trees.BehaviourTree(
        root=root,
        unicode_tree_debug=False)
    
    try:
        tree.setup(timeout=15.0)
        tree.tick_tock(period_ms=30)
        rclpy.spin(tree.node)
    except KeyboardInterrupt:
        tree.node.get_logger().info("Keyboard Interrupt")
    finally:
        tree.shutdown()
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()