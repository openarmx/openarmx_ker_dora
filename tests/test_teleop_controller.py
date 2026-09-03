import numpy as np

from openarmx_ker_dora.config import load_config
from openarmx_ker_dora.messages import KerFrame
from openarmx_ker_dora.pose_processor import LEFT_TARGET_NAMES, RIGHT_TARGET_NAMES
from openarmx_ker_dora.teleop_controller import TeleopController


def make_frame(config, *, sequence=1, error_mask=0, offset=0.5, now=10.0):
    state = np.maximum(config.robot.lower, np.minimum(config.robot.upper, 0.0))
    return KerFrame(
        sequence=sequence,
        received_monotonic_ns=int(now * 1e9),
        error_mask=error_mask,
        left_names=tuple(LEFT_TARGET_NAMES),
        left_position=state[:8] + offset,
        right_names=tuple(RIGHT_TARGET_NAMES),
        right_position=state[8:] + offset,
    )


def test_waits_for_complete_robot_state():
    config = load_config()
    controller = TeleopController(config)
    controller.update_frame(make_frame(config), now=10.0)
    assert controller.tick(now=10.02) is None


def test_takeover_starts_from_current_robot_state():
    config = load_config()
    controller = TeleopController(config)
    state = np.maximum(config.robot.lower, np.minimum(config.robot.upper, 0.0))
    controller.update_robot_state(state, now=10.0)
    controller.update_frame(make_frame(config), now=10.0)
    left, right = controller.tick(now=10.0)
    np.testing.assert_allclose(left, state[:8])
    np.testing.assert_allclose(right, state[8:])


def test_rate_limits_joint_and_gripper_commands():
    config = load_config()
    controller = TeleopController(config)
    state = np.maximum(config.robot.lower, np.minimum(config.robot.upper, 0.0))
    controller.update_robot_state(state, now=10.0)
    controller.update_frame(make_frame(config), now=10.0)
    left, _ = controller.tick(now=10.02)
    assert np.all(np.abs(left[:7] - state[:7]) <= 0.02 * config.safety.max_joint_velocity_rad_s)
    assert abs(left[7] - state[7]) <= 0.02 * config.safety.max_gripper_velocity_m_s


def test_sensor_error_and_stale_target_stop_output():
    config = load_config()
    state = np.maximum(config.robot.lower, np.minimum(config.robot.upper, 0.0))

    errored = TeleopController(config)
    errored.update_robot_state(state, now=10.0)
    errored.update_frame(make_frame(config, error_mask=1), now=10.0)
    assert errored.tick(now=10.01) is None

    stale = TeleopController(config)
    stale.update_robot_state(state, now=10.0)
    stale.update_frame(make_frame(config), now=10.0)
    assert stale.tick(now=10.0 + config.safety.target_timeout_s + 0.01) is None


def test_delayed_frame_uses_device_receive_time_for_timeout():
    config = load_config()
    state = np.maximum(config.robot.lower, np.minimum(config.robot.upper, 0.0))
    controller = TeleopController(config)
    controller.update_robot_state(state, now=20.0)
    controller.update_frame(make_frame(config, now=10.0), now=20.0)
    assert controller.tick(now=20.0) is None
    assert controller.fault_reason == "target_timeout"
