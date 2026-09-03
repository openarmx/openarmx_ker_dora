from __future__ import annotations

import json
import logging
import time

import pyarrow as pa
from dora import Node

from openflex_ker_dora.config import load_config
from openflex_ker_dora.messages import parse_ker_frame
from openflex_ker_dora.teleop_controller import TeleopController


LOG = logging.getLogger("openflex_ker_dora.teleop_controller")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load_config()
    controller = TeleopController(config)
    node = Node()
    last_reason = None
    was_active = False
    command_ticks = 0

    for event in node:
        if event.get("type") == "STOP":
            break
        if event.get("type") != "INPUT":
            continue
        now = time.monotonic()
        try:
            if event["id"] == "robot_state":
                controller.update_robot_state(event["value"], now=now)
            elif event["id"] == "ker_frame":
                controller.update_frame(parse_ker_frame(event["value"]), now=now)
            elif event["id"] == "tick":
                command = controller.tick(now=now)
                if command is not None:
                    left, right = command
                    node.send_output("left_command", pa.array(left, type=pa.float64()))
                    node.send_output("right_command", pa.array(right, type=pa.float64()))
                    command_ticks += 1
                    if not was_active:
                        LOG.info("机器人状态和 KER 目标已就绪，开始限速接管")
                    if command_ticks % int(config.safety.command_rate_hz) == 0:
                        LOG.info(
                            "遥操命令持续发布，KER frame=%s",
                            controller.last_sequence,
                        )
                if controller.fault_reason != last_reason:
                    status = {
                        "active": controller.active,
                        "reason": controller.fault_reason or "active",
                        "last_sequence": controller.last_sequence,
                    }
                    node.send_output("teleop_status", pa.array([json.dumps(status)]))
                    if controller.fault_reason:
                        LOG.warning("遥操停止: %s", controller.fault_reason)
                    last_reason = controller.fault_reason
                was_active = controller.active
        except (KeyError, TypeError, ValueError) as error:
            controller.active = False
            controller.fault_reason = f"invalid_input:{error}"
            LOG.error("拒绝遥操输入: %s", error)

    LOG.info("遥操控制节点已停止")


if __name__ == "__main__":
    main()
