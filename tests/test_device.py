import math

import pytest

from openflex_ker_dora.device import parse_device_packet


def test_device_packet_encodes_error_bits_with_same_sample():
    errors = [False] * 16
    errors[2] = True
    errors[15] = True
    sample = parse_device_packet({"angles": [0.0] * 16, "errors": errors}, 3)
    assert sample.sequence == 3
    assert sample.error_mask == (1 << 2) | (1 << 15)


def test_device_packet_rejects_non_finite_angle():
    with pytest.raises(ValueError, match="finite"):
        parse_device_packet({"angles": [0.0] * 15 + [math.inf]}, 1)
