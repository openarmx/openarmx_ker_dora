import numpy as np
import pytest

from openarmx_ker_dora.messages import make_ker_frame, parse_ker_frame
from openarmx_ker_dora.pose_processor import LEFT_TARGET_NAMES, RIGHT_TARGET_NAMES


def test_ker_frame_keeps_targets_and_error_mask_atomic():
    value = make_ker_frame(
        sequence=7,
        received_monotonic_ns=123,
        error_mask=0x20,
        left_names=LEFT_TARGET_NAMES,
        left_position=np.arange(8, dtype=float),
        right_names=RIGHT_TARGET_NAMES,
        right_position=np.arange(8, dtype=float) + 10,
    )
    frame = parse_ker_frame(value)
    assert frame.sequence == 7
    assert frame.error_mask == 0x20
    np.testing.assert_array_equal(frame.left_position, np.arange(8, dtype=float))
    np.testing.assert_array_equal(frame.right_position, np.arange(8, dtype=float) + 10)


def test_ker_frame_rejects_non_finite_target():
    with pytest.raises(ValueError, match="finite"):
        make_ker_frame(
            sequence=1,
            received_monotonic_ns=1,
            error_mask=0,
            left_names=LEFT_TARGET_NAMES,
            left_position=[0.0] * 7 + [float("nan")],
            right_names=RIGHT_TARGET_NAMES,
            right_position=[0.0] * 8,
        )
