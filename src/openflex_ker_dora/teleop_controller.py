from __future__ import annotations

import numpy as np

from .config import AppConfig
from .messages import KerFrame, finite_vector


class TeleopController:
    def __init__(self, config: AppConfig):
        self.config = config
        self.robot_state: np.ndarray | None = None
        self.robot_state_at: float | None = None
        self.target: np.ndarray | None = None
        self.target_at: float | None = None
        self.command: np.ndarray | None = None
        self.last_tick_at: float | None = None
        self.active = False
        self.fault_reason: str | None = None
        self.last_sequence: int | None = None

    def update_robot_state(self, value: object, *, now: float) -> None:
        self.robot_state = finite_vector(value, 16, "robot state")
        self.robot_state_at = now
        self._try_activate(now)

    @staticmethod
    def _ordered_target(
        names: tuple[str, ...], positions: np.ndarray, expected: tuple[str, ...]
    ) -> np.ndarray:
        by_name = dict(zip(names, positions))
        missing = [name for name in expected if name not in by_name]
        if missing:
            raise ValueError(f"KER target missing joints: {', '.join(missing)}")
        return finite_vector([by_name[name] for name in expected], 8, "KER target")

    def update_frame(self, frame: KerFrame, *, now: float) -> None:
        if self.last_sequence is not None and frame.sequence <= self.last_sequence:
            return
        self.last_sequence = frame.sequence
        self.target_at = frame.received_monotonic_ns / 1e9
        if self.config.safety.drop_command_on_sensor_error and frame.error_mask:
            self.active = False
            self.fault_reason = f"sensor_error:0x{frame.error_mask:04x}"
            return
        left = self._ordered_target(
            frame.left_names, frame.left_position, self.config.robot.left_names
        )
        right = self._ordered_target(
            frame.right_names, frame.right_position, self.config.robot.right_names
        )
        self.target = np.concatenate([left, right])
        if self.config.safety.clamp_to_joint_limits:
            self.target = np.clip(
                self.target, self.config.robot.lower, self.config.robot.upper
            )
        self.fault_reason = None
        self._try_activate(now)

    def _try_activate(self, now: float) -> None:
        if self.active or self.robot_state is None or self.target is None:
            return
        self.command = self.robot_state.copy()
        self.last_tick_at = now
        self.active = True

    def tick(self, *, now: float) -> tuple[np.ndarray, np.ndarray] | None:
        if not self.active or self.command is None or self.target is None:
            return None
        assert self.target_at is not None and self.robot_state_at is not None
        if now - self.target_at > self.config.safety.target_timeout_s:
            self.active = False
            self.fault_reason = "target_timeout"
            return None
        if now - self.robot_state_at > self.config.safety.robot_state_timeout_s:
            self.active = False
            self.fault_reason = "robot_state_timeout"
            return None

        previous_tick = self.last_tick_at if self.last_tick_at is not None else now
        elapsed = min(0.1, max(0.0, now - previous_tick))
        self.last_tick_at = now
        max_step = np.asarray(
            ([self.config.safety.max_joint_velocity_rad_s] * 7
             + [self.config.safety.max_gripper_velocity_m_s])
            * 2,
            dtype=np.float64,
        ) * elapsed
        self.command += np.clip(self.target - self.command, -max_step, max_step)
        self.command = np.clip(
            self.command, self.config.robot.lower, self.config.robot.upper
        )
        return self.command[:8].copy(), self.command[8:].copy()
