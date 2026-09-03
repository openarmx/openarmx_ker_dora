from __future__ import annotations

import json
import logging

import pyarrow as pa
from dora import Node

from openarmx_ker_dora.config import load_config
from openarmx_ker_dora.device import HardwareReceiver
from openarmx_ker_dora.messages import make_ker_frame
from openarmx_ker_dora.pose_processor import (
    LEFT_TARGET_NAMES,
    RIGHT_TARGET_NAMES,
    KerPoseProcessor,
)


LOG = logging.getLogger("openarmx_ker_dora.ker_device")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load_config()
    processor = KerPoseProcessor(
        use_hampel=config.processing.use_hampel_filter,
        use_low_pass=config.processing.use_low_pass_filter,
        low_pass_alpha=config.processing.low_pass_alpha,
        gripper_min=config.processing.gripper_min_position,
        gripper_max=config.processing.gripper_max_position,
        joint_scales=config.processing.joint_scales,
        joint_offsets=config.processing.joint_offsets,
    )
    node = Node()
    receiver = HardwareReceiver(config)
    receiver.start()
    LOG.info("已启动 KER 设备采集 (transport=%s, mode=%s)", config.device.transport, config.mode)

    try:
        for event in node:
            if event.get("type") == "STOP":
                break
            if event.get("type") != "INPUT" or event.get("id") != "tick":
                continue

            sample = receiver.latest_sample()
            status = receiver.latest_status()
            if status is not None:
                node.send_output("device_status", pa.array([json.dumps(status)]))

            if sample is None:
                continue

            pose = processor.process(sample.angles)
            node.send_output(
                "ker_frame",
                make_ker_frame(
                    sequence=sample.sequence,
                    received_monotonic_ns=sample.received_monotonic_ns,
                    error_mask=sample.error_mask,
                    left_names=LEFT_TARGET_NAMES,
                    left_position=pose.left_target,
                    right_names=RIGHT_TARGET_NAMES,
                    right_position=pose.right_target,
                ),
            )
            node.send_output("source_state", pa.array(pose.source_radians, type=pa.float64()))
    finally:
        receiver.close()
        LOG.info("KER device 节点已停止")


if __name__ == "__main__":
    main()
