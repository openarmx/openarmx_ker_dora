# OpenArmX KER Dora 遥操作系统

[English](README.md) | 简体中文

OpenArmX KER 双臂外骨骼主手的 Dora 遥操作系统。基于 Dora-rs 高性能数据流框架与 ROS 2，实现毫秒级零拷贝低延迟遥操作，将外骨骼设备采集、平滑安全控制与机械臂执行层解耦。

## 目录内容

- `src/openflex_ker_dora/` - 外骨骼硬件通信、姿态滤波处理、遥操作安全控制器及 ROS 2 桥接节点。
- `config/` - 外骨骼通信参数配置 (`openflex_ker.yaml`) 与机械臂 URDF 关节物理限位表 (`openarmx_robot.yaml`)。
- `tests/` - 通信协议、滤波算法、关节限位与控制状态机单元测试。
- `dataflow.yml` - Dora-rs 数据流拓扑描述文件。

## 环境要求

- OpenArmX KER 双臂外骨骼主手（支持 WiFi TCP 或 USB Direct 传输）。
- OpenArmX 双臂机器人或基于 ROS 2 Humble 的仿真环境。
- Ubuntu 22.04 LTS。
- Python 3.11。
- ROS 2 Humble。
- Dora-rs 0.5.0 与 uv 包管理工具。

## 获取仓库

```bash
git clone https://github.com/openarmx/openflex_ker_dora.git
cd openflex_ker_dora
uv sync
source .venv/bin/activate
```

## 配置说明

配置文件位于 `config/` 目录：

- `config/openflex_ker.yaml`：外骨骼硬件通信方式（默认 `wifi`，可选 `usb`）、外骨骼局域网地址（默认 `openarm-ker.local:19090`）、低通滤波系数、角速度限制与超时熔断阈值。
- `config/openarmx_robot.yaml`：定义左右臂各 8 个关节名称以及来自 URDF 的软限位区间（`lower` / `upper`），用于实时截断并防止机械臂超限。

## 启动与运行

### 1. 启动机械臂控制器（真机或仿真）

在终端中启动 OpenArmX 双臂控制器（示例为 fake hardware 仿真模式）：

```bash
source /opt/ros/humble/setup.bash
source <your_openarmx_ws>/install/setup.bash
ros2 launch openarmx_bringup openarmx.bimanual.launch.py \
  use_fake_hardware:=true \
  robot_controller:=forward_position_controller \
  control_mode:=mit
```

### 2. 启动 Dora 遥操数据流

确保外骨骼已开机并处于同一局域网（或已插入 USB）：

```bash
source /opt/ros/humble/setup.bash
source <your_openarmx_ws>/install/setup.bash
source .venv/bin/activate
dora run dataflow.yml
```

按 `Ctrl+C` 即可平稳停止。

## 通信测试

```bash
# 探测外骨骼 WiFi 网络连通性
ping -c 3 openarm-ker.local

# 探测 M5 WiFi 端口连通性
nc -zv openarm-ker.local 19090

# 运行单元测试套件（25 项测试）
source .venv/bin/activate
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -v
```

## 许可证

本项目采用知识共享署名-非商业性使用-相同方式共享 4.0 国际许可证（CC BY-NC-SA 4.0）。

版权所有 (c) 2026 成都长数机器人有限公司。

详细信息请查看 [LICENSE](LICENSE)，或访问：http://creativecommons.org/licenses/by-nc-sa/4.0/

## 作者

- **张力** (Zhang Li)
- 公司：成都长数机器人有限公司
- 网站：https://openarmx.com/

## 版本

**当前版本**：0.1.0

## 致谢

本系统属于 OpenArmX 机器人平台生态，并包含基于 OpenArm KER 项目通信协议的衍生工作。

---

## 联系我们

### 成都长数机器人有限公司

| 联系方式 | 信息 |
|---|---|
| 邮箱 | [openarmrobot@gmail.com](mailto:openarmrobot@gmail.com) |
| 电话 / 微信 | +86-17746530375 |
| 官方网站 | [https://openarmx.com/](https://openarmx.com/) |
| 在线文档 | [http://docs.openarmx.com/](http://docs.openarmx.com/) |
| 地址 | 天津经济技术开发区西区新业八街 11 号华城机械厂 |
| 联系人 | 王先生 |
