from __future__ import annotations

import logging

import pyarrow as pa
from dora import Node, Ros2Context, Ros2NodeOptions, Ros2QosPolicies

from openarmx_ker_dora.config import load_config
from openarmx_ker_dora.messages import (
    arrow_struct_to_dict,
    finite_vector,
    float64_multi_array,
)


LOG = logging.getLogger("openarmx_ker_dora.ros2_interface")


def reorder_joint_state(message: dict, expected: tuple[str, ...]):
    names = message["name"]
    positions = message["position"]
    if len(names) != len(positions):
        raise ValueError("JointState name and position lengths differ")
    by_name = dict(zip(names, positions))
    missing = [name for name in expected if name not in by_name]
    if missing:
        raise ValueError(f"JointState missing joints: {', '.join(missing)}")
    return finite_vector([by_name[name] for name in expected], len(expected), "robot state")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load_config()
    node = Node()
    context = Ros2Context()
    ros_node = context.new_node(
        "openarmx_ker_dora_bridge", "/", Ros2NodeOptions(rosout=True)
    )
    qos = Ros2QosPolicies(reliable=True, keep_last=10)
    left_topic = ros_node.create_topic(
        config.ros2.left_controller_topic, "std_msgs/Float64MultiArray", qos
    )
    right_topic = ros_node.create_topic(
        config.ros2.right_controller_topic, "std_msgs/Float64MultiArray", qos
    )
    state_topic = ros_node.create_topic(
        config.ros2.joint_states_topic, "sensor_msgs/JointState", qos
    )
    left_publisher = ros_node.create_publisher(left_topic)
    right_publisher = ros_node.create_publisher(right_topic)
    subscription = ros_node.create_subscription(state_topic)
    node.merge_external_events(subscription)
    LOG.info("ROS 2 边界已连接，等待 /joint_states")

    for event in node:
        if event.get("kind") == "external":
            try:
                message = arrow_struct_to_dict(event["value"])
                state = reorder_joint_state(message, config.robot.names)
                node.send_output("robot_state", pa.array(state, type=pa.float64()))
            except (KeyError, TypeError, ValueError) as error:
                LOG.warning("忽略不完整机器人状态: %s", error)
            continue
        if event.get("type") == "STOP":
            break
        if event.get("type") != "INPUT":
            continue
        try:
            if event["id"] == "left_command":
                left_publisher.publish(float64_multi_array(event["value"]))
            elif event["id"] == "right_command":
                right_publisher.publish(float64_multi_array(event["value"]))
        except (TypeError, ValueError) as error:
            LOG.error("拒绝 ROS 2 控制命令: %s", error)
    LOG.info("ROS 2 边界节点已停止")


if __name__ == "__main__":
    main()
