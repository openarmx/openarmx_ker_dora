from __future__ import annotations

from dataclasses import dataclass
from queue import Empty, Queue
import threading
import time
from typing import Any

import numpy as np

from .config import AppConfig
from .ker_stream import CMD_STREAM, KERStream


@dataclass(frozen=True)
class DeviceSample:
    sequence: int
    received_monotonic_ns: int
    angles: tuple[float, ...]
    error_mask: int


def parse_device_packet(packet: dict[str, Any], sequence: int) -> DeviceSample:
    angles = np.asarray(packet.get("angles"), dtype=np.float64).reshape(-1)
    if angles.size != 16:
        raise ValueError(f"KER packet must contain 16 angles, got {angles.size}")
    if not np.all(np.isfinite(angles)):
        raise ValueError("KER angles must contain only finite values")
    errors = list(packet.get("errors", [False] * 16))
    if len(errors) != 16:
        raise ValueError(f"KER packet must contain 16 error flags, got {len(errors)}")
    error_mask = sum(1 << index for index, error in enumerate(errors) if bool(error))
    return DeviceSample(
        sequence=sequence,
        received_monotonic_ns=time.monotonic_ns(),
        angles=tuple(float(value) for value in angles),
        error_mask=error_mask,
    )


class HardwareReceiver:
    """Own the blocking KER lifecycle outside the Dora event loop."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.samples: Queue[DeviceSample] = Queue(maxsize=2)
        self.status: Queue[dict[str, Any]] = Queue(maxsize=2)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._stream: KERStream | None = None

    def start(self) -> None:
        self._thread.start()

    def _make_stream(self) -> KERStream:
        device = self.config.device
        return KERStream(
            transport=device.transport,
            vid=device.usb_vid,
            pid=device.usb_pid,
            wifi_host=device.wifi_host,
            wifi_port=device.wifi_port,
            connect_timeout=device.wifi_connect_timeout_s,
            socket_timeout=device.wifi_socket_timeout_s,
        )

    @staticmethod
    def _replace(queue: Queue, value: Any) -> None:
        if queue.full():
            try:
                queue.get_nowait()
            except Empty:
                pass
        queue.put_nowait(value)

    def _set_status(self, **status: Any) -> None:
        self._replace(self.status, status)

    def _run(self) -> None:
        sequence = 0
        reconnects = 0
        while not self._stop.is_set():
            try:
                self._stream = self._make_stream()
                self._stream.connect()
                self._stream.send_command(CMD_STREAM)
                self._set_status(
                    connected=True,
                    transport=self._stream.transport,
                    endpoint=self._stream.endpoint,
                    metadata=dict(self._stream.metadata),
                    reconnect_count=reconnects,
                )
                while not self._stop.is_set() and self._stream.is_connected:
                    packet = self._stream.recv()
                    if packet is None:
                        self._stop.wait(0.001)
                        continue
                    sequence += 1
                    self._replace(self.samples, parse_device_packet(packet, sequence))
                if not self._stop.is_set():
                    raise ConnectionError("KER receive loop stopped")
            except Exception as error:
                reconnects += 1
                self._set_status(
                    connected=False,
                    transport=self.config.device.transport,
                    error=str(error),
                    reconnect_count=reconnects,
                )
            finally:
                if self._stream is not None:
                    self._stream.close()
                    self._stream = None
            self._stop.wait(self.config.device.reconnect_interval_s)

    def latest_sample(self) -> DeviceSample | None:
        latest = None
        while True:
            try:
                latest = self.samples.get_nowait()
            except Empty:
                return latest

    def latest_status(self) -> dict[str, Any] | None:
        latest = None
        while True:
            try:
                latest = self.status.get_nowait()
            except Empty:
                return latest

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=4.0)
