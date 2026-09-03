from pathlib import Path

import pytest
import yaml

from openarmx_ker_dora.config import load_config


CONFIG = Path(__file__).parents[1] / "config" / "openarmx_ker.yaml"
ROBOT = Path(__file__).parents[1] / "config" / "openarmx_robot.yaml"


def test_default_configuration_is_real_wifi():
    config = load_config(CONFIG, ROBOT)
    assert config.mode == "real"
    assert config.device.transport == "wifi"
    assert config.device.wifi_host == "openarm-ker.local"
    assert len(config.robot.names) == 16


def test_usb_transport_is_accepted(tmp_path):
    raw = yaml.safe_load(CONFIG.read_text())
    raw["device"]["transport"] = "usb"
    candidate = tmp_path / "usb.yaml"
    candidate.write_text(yaml.safe_dump(raw))

    config = load_config(candidate, ROBOT)
    assert config.device.transport == "usb"


def test_rejects_unsupported_transports(tmp_path):
    raw = yaml.safe_load(CONFIG.read_text())
    raw["device"]["transport"] = "serial"
    candidate = tmp_path / "serial.yaml"
    candidate.write_text(yaml.safe_dump(raw))

    with pytest.raises(ValueError, match="must be 'wifi' or 'usb'"):
        load_config(candidate, ROBOT)

    raw["device"]["transport"] = "replay"
    candidate.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError, match="must be 'wifi' or 'usb'"):
        load_config(candidate, ROBOT)


def test_environment_selects_explicit_real_configuration(tmp_path, monkeypatch):
    raw = yaml.safe_load(CONFIG.read_text())
    raw["mode"] = "real"
    raw["device"]["transport"] = "wifi"
    raw["device"]["wifi_host"] = "192.168.10.50"
    candidate = tmp_path / "real.yaml"
    candidate.write_text(yaml.safe_dump(raw))
    monkeypatch.setenv("OPENARMX_KER_CONFIG", str(candidate))

    config = load_config(robot_path=ROBOT)
    assert config.mode == "real"
    assert config.device.transport == "wifi"
    assert config.device.wifi_host == "192.168.10.50"
