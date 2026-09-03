import numpy as np

from openflex_ker_dora.ros2_interface_node import reorder_joint_state


def test_ros_joint_state_is_reordered_by_name():
    message = {"name": ["joint_b", "joint_a"], "position": [2.0, 1.0]}
    np.testing.assert_array_equal(
        reorder_joint_state(message, ("joint_a", "joint_b")), [1.0, 2.0]
    )
