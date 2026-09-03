from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

import numpy as np
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class DeviceConfig:
    transport: str
    usb_vid: int
    usb_pid: int
    wifi_host: str
    wifi_port: int
    wifi_connect_timeout_s: float
    wifi_socket_timeout_s: float
    publish_rate_hz: float
    reconnect_interval_s: float


@dataclass(frozen=True)
class ProcessingConfig:
    use_hampel_filter: bool
    use_low_pass_filter: bool
    low_pass_alpha: float
    gripper_min_position: float
    gripper_max_position: float
    joint_scales: tuple[float, ...]
    joint_offsets: tuple[float, ...]


@dataclass(frozen=True)
class SafetyConfig:
    drop_command_on_sensor_error: bool
    max_joint_velocity_rad_s: float
    max_gripper_velocity_m_s: float
    command_rate_hz: float
    target_timeout_s: float
    robot_state_timeout_s: float
    clamp_to_joint_limits: bool


@dataclass(frozen=True)
class RobotConfig:
    left_names: tuple[str, ...]
    right_names: tuple[str, ...]
    lower: np.ndarray
    upper: np.ndarray

    @property
    def names(self) -> tuple[str, ...]:
        return self.left_names + self.right_names


@dataclass(frozen=True)
class Ros2Config:
    joint_states_topic: str
    left_controller_topic: str
    right_controller_topic: str


@dataclass(frozen=True)
class AppConfig:
    mode: str
    device: DeviceConfig
    processing: ProcessingConfig
    safety: SafetyConfig
    robot: RobotConfig
    ros2: Ros2Config


def _positive(value: float, label: str) -> float:
    result = float(value)
    if result <= 0.0:
        raise ValueError(f"{label} must be greater than zero")
    return result


def load_config(
    config_path: Path | None = None, robot_path: Path | None = None
) -> AppConfig:
    if config_path is None:
        configured_path = os.environ.get("OPENFLEX_KER_CONFIG")
        config_path = (
            Path(configured_path)
            if configured_path
            else PROJECT_ROOT / "config" / "openflex_ker.yaml"
        )
    robot_path = robot_path or PROJECT_ROOT / "config" / "openarmx_robot.yaml"
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    robot_raw = yaml.safe_load(robot_path.read_text(encoding="utf-8"))

    mode = str(raw.get("mode", "real"))
    device_raw = raw["device"]
    transport = str(device_raw["transport"])
    if transport not in {"wifi", "usb"}:
        raise ValueError(f"unsupported KER transport: {transport}, must be 'wifi' or 'usb'")

    processing_raw = raw["processing"]
    scales = tuple(float(value) for value in processing_raw["joint_scales"])
    offsets = tuple(float(value) for value in processing_raw["joint_offsets"])
    if len(scales) != 14 or len(offsets) != 14:
        raise ValueError("joint_scales and joint_offsets must contain 14 values")

    safety_raw = raw["safety"]
    left = robot_raw["joints"]["left"]
    right = robot_raw["joints"]["right"]
    entries = left + right
    return AppConfig(
        mode=mode,
        device=DeviceConfig(
            transport=transport,
            usb_vid=int(device_raw.get("usb_vid", 12346)),
            usb_pid=int(device_raw.get("usb_pid", 16386)),
            wifi_host=str(device_raw.get("wifi_host", "openarm-ker.local")),
            wifi_port=int(device_raw.get("wifi_port", 19090)),
            wifi_connect_timeout_s=_positive(
                device_raw.get("wifi_connect_timeout_s", 3.0), "wifi_connect_timeout_s"
            ),
            wifi_socket_timeout_s=_positive(
                device_raw.get("wifi_socket_timeout_s", 0.02), "wifi_socket_timeout_s"
            ),
            publish_rate_hz=_positive(
                device_raw.get("publish_rate_hz", 100.0), "publish_rate_hz"
            ),
            reconnect_interval_s=_positive(
                device_raw.get("reconnect_interval_s", 2.0), "reconnect_interval_s"
            ),
        ),
        processing=ProcessingConfig(
            use_hampel_filter=bool(processing_raw["use_hampel_filter"]),
            use_low_pass_filter=bool(processing_raw["use_low_pass_filter"]),
            low_pass_alpha=float(processing_raw["low_pass_alpha"]),
            gripper_min_position=float(processing_raw["gripper_min_position"]),
            gripper_max_position=float(processing_raw["gripper_max_position"]),
            joint_scales=scales,
            joint_offsets=offsets,
        ),
        safety=SafetyConfig(
            drop_command_on_sensor_error=bool(safety_raw["drop_command_on_sensor_error"]),
            max_joint_velocity_rad_s=_positive(
                safety_raw["max_joint_velocity_rad_s"], "max_joint_velocity_rad_s"
            ),
            max_gripper_velocity_m_s=_positive(
                safety_raw["max_gripper_velocity_m_s"], "max_gripper_velocity_m_s"
            ),
            command_rate_hz=_positive(safety_raw["command_rate_hz"], "command_rate_hz"),
            target_timeout_s=_positive(safety_raw["target_timeout_s"], "target_timeout_s"),
            robot_state_timeout_s=_positive(
                safety_raw["robot_state_timeout_s"], "robot_state_timeout_s"
            ),
            clamp_to_joint_limits=bool(safety_raw["clamp_to_joint_limits"]),
        ),
        robot=RobotConfig(
            left_names=tuple(item["name"] for item in left),
            right_names=tuple(item["name"] for item in right),
            lower=np.asarray([item["lower"] for item in entries], dtype=np.float64),
            upper=np.asarray([item["upper"] for item in entries], dtype=np.float64),
        ),
        ros2=Ros2Config(**raw["ros2"]),
    )
