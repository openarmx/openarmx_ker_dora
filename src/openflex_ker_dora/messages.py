from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
import pyarrow as pa


KER_FRAME_TYPE = pa.struct(
    [
        pa.field("sequence", pa.uint64()),
        pa.field("received_monotonic_ns", pa.uint64()),
        pa.field("error_mask", pa.uint16()),
        pa.field("left_names", pa.list_(pa.string())),
        pa.field("left_position", pa.list_(pa.float64())),
        pa.field("right_names", pa.list_(pa.string())),
        pa.field("right_position", pa.list_(pa.float64())),
    ]
)


@dataclass(frozen=True)
class KerFrame:
    sequence: int
    received_monotonic_ns: int
    error_mask: int
    left_names: tuple[str, ...]
    left_position: np.ndarray
    right_names: tuple[str, ...]
    right_position: np.ndarray


def finite_vector(value: Any, length: int, label: str) -> np.ndarray:
    if isinstance(value, pa.Array):
        value = value.to_numpy(zero_copy_only=False)
    result = np.asarray(value, dtype=np.float64).reshape(-1)
    if result.size != length:
        raise ValueError(f"{label} must contain {length} values, got {result.size}")
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must contain only finite values")
    return result


def _names(value: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(str(item) for item in value)
    if len(result) != 8 or len(set(result)) != 8:
        raise ValueError(f"{label} must contain 8 unique names")
    return result


def make_ker_frame(
    *,
    sequence: int,
    received_monotonic_ns: int,
    error_mask: int,
    left_names: Sequence[str],
    left_position: Sequence[float],
    right_names: Sequence[str],
    right_position: Sequence[float],
) -> pa.StructArray:
    left_names = _names(left_names, "left_names")
    right_names = _names(right_names, "right_names")
    left = finite_vector(left_position, 8, "left_position")
    right = finite_vector(right_position, 8, "right_position")
    if not 0 <= int(error_mask) <= 0xFFFF:
        raise ValueError("error_mask must fit uint16")
    return pa.array(
        [
            {
                "sequence": int(sequence),
                "received_monotonic_ns": int(received_monotonic_ns),
                "error_mask": int(error_mask),
                "left_names": list(left_names),
                "left_position": left.tolist(),
                "right_names": list(right_names),
                "right_position": right.tolist(),
            }
        ],
        type=KER_FRAME_TYPE,
    )


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, pa.StructArray):
        if len(value) != 1:
            raise ValueError(f"expected one KER frame, got {len(value)}")
        return value[0].as_py()
    if isinstance(value, pa.StructScalar):
        return value.as_py()
    if isinstance(value, dict):
        return value
    raise TypeError(f"unsupported KER frame type: {type(value).__name__}")


def parse_ker_frame(value: Any) -> KerFrame:
    raw = _as_dict(value)
    return KerFrame(
        sequence=int(raw["sequence"]),
        received_monotonic_ns=int(raw["received_monotonic_ns"]),
        error_mask=int(raw["error_mask"]),
        left_names=_names(raw["left_names"], "left_names"),
        left_position=finite_vector(raw["left_position"], 8, "left_position"),
        right_names=_names(raw["right_names"], "right_names"),
        right_position=finite_vector(raw["right_position"], 8, "right_position"),
    )


def float64_multi_array(values: Sequence[float]) -> pa.StructArray:
    command = finite_vector(values, 8, "controller command")
    dim_type = pa.list_(
        pa.struct(
            [
                pa.field("label", pa.string()),
                pa.field("size", pa.uint32()),
                pa.field("stride", pa.uint32()),
            ]
        )
    )
    message_type = pa.struct(
        [
            pa.field(
                "layout",
                pa.struct(
                    [pa.field("dim", dim_type), pa.field("data_offset", pa.uint32())]
                ),
            ),
            pa.field("data", pa.list_(pa.float64())),
        ]
    )
    return pa.array(
        [{"layout": {"dim": [], "data_offset": 0}, "data": command.tolist()}],
        type=message_type,
    )


def arrow_struct_to_dict(value: Any) -> dict[str, Any]:
    return _as_dict(value)
