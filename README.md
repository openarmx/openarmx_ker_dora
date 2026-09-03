# OpenArmX KER Dora Teleoperation

English | [简体中文](README_CN.md)

Dora teleoperation system for the OpenArmX KER bimanual leader exoskeleton. Built on the [Dora-rs](https://github.com/dora-rs/dora) high-performance dataflow framework and ROS 2, it delivers microsecond-level zero-copy low-latency teleoperation, decoupling exoskeleton acquisition, safety control, and robot execution.

## Contents

- `src/openarmx_ker_dora/` - Exoskeleton hardware transport, pose processing/filtering, safety controller, and ROS 2 bridge nodes.
- `config/` - Exoskeleton device configuration (`openarmx_ker.yaml`) and robot URDF joint limit tables (`openarmx_robot.yaml`).
- `tests/` - Unit tests for stream protocol, filtering, joint limits, and controller state machines.
- `dataflow.yml` - Dora-rs dataflow graph descriptor.

## Requirements

- OpenArmX KER bimanual leader device (supports WiFi TCP or USB Direct transport).
- OpenArmX bimanual robot or ROS 2 Humble simulation environment.
- Ubuntu 22.04 LTS.
- Python 3.11.
- ROS 2 Humble.
- Dora-rs 0.5.0 and the uv package manager.

## Repository Setup

```bash
git clone https://github.com/openarmx/openarmx_ker_dora.git
cd openarmx_ker_dora
uv sync
source .venv/bin/activate
```

## Configuration

Configuration files are located in the `config/` directory:

- `config/openarmx_ker.yaml`: Exoskeleton transport mode (`wifi` by default, or `usb`), LAN endpoint (`openarm-ker.local:19090`), low-pass filter coefficient, joint velocity limits, and timeout trip thresholds.
- `config/openarmx_robot.yaml`: Joint names and URDF joint soft limits (`lower` / `upper`) for 8 DOF per arm (7 revolute + 1 gripper), used for real-time safety clamping.

## Running

### 1. Launch Robot Controller (Hardware or Simulation)

Launch the OpenArmX bimanual controller in a terminal (example shown in fake hardware simulation mode):

```bash
source /opt/ros/humble/setup.bash
source <your_openarmx_ws>/install/setup.bash
ros2 launch openarmx_bringup openarmx.bimanual.launch.py \
  use_fake_hardware:=true \
  robot_controller:=forward_position_controller \
  control_mode:=mit
```

### 2. Launch Dora Teleoperation Dataflow

Ensure the KER exoskeleton is powered on and connected to the same network (or plugged in via USB):

```bash
source /opt/ros/humble/setup.bash
source <your_openarmx_ws>/install/setup.bash
source .venv/bin/activate
dora run dataflow.yml
```

Press `Ctrl+C` to cleanly stop all nodes.

## Test

```bash
# Ping the exoskeleton WiFi endpoint
ping -c 3 openarm-ker.local

# Probe M5 WiFi TCP streaming port
nc -zv openarm-ker.local 19090

# Run full unit test suite (25 tests)
source .venv/bin/activate
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -v
```

## License

This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC BY-NC-SA 4.0).

Copyright (c) 2026 Chengdu Changshu Robot Co., Ltd. (成都长数机器人有限公司)

For details, see the [LICENSE](LICENSE) file or visit: http://creativecommons.org/licenses/by-nc-sa/4.0/

## Author

- **Zhang Li** (张力)
- Company: Chengdu Changshu Robot Co., Ltd. (成都长数机器人有限公司)
- Website: https://openarmx.com/

## Version

**Current Version**: 0.1.0

## Acknowledgments

This system is part of the OpenArmX robotic platform ecosystem and includes work derived from the OpenArm KER project communication protocol.

---

## Contact Us

### Chengdu Changshu Robot Co., Ltd.

| Contact | Information |
|---|---|
| Email | [openarmrobot@gmail.com](mailto:openarmrobot@gmail.com) |
| Phone / WeChat | +86-17746530375 |
| Website | [https://openarmx.com/](https://openarmx.com/) |
| Documentation | [http://docs.openarmx.com/](http://docs.openarmx.com/) |
| Address | Huacheng Machinery Plant, No.11 Xinye 8th Street, West Area, Tianjin Economic-Technological Development Area |
| Contact Person | Mr. Wang |
