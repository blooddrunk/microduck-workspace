# MicroDuck HD1910 复刻与 Sim-to-Real 工作区

> 2026-10-14 起以 **飞特 HD1910 + Radxa ZERO 3W (RK3566)** 为目标硬件。此仓库是个人实验记录，不代表官方或第三方固件已经适配你的实物。

## 现在先做什么

**当前阶段：S0 → S1（机械已装、初步连线；HAT / IMU / 电源未最终接入）。**
不要直接整机通电、使能全部舵机或运行行走 Policy。

1. [00 · 实物盘点与安全闸门](docs/00_START_HERE.md)：先确认每块板的具体版本、引脚、额定电压和电源拓扑。
2. [01 · ZERO 3W 单板刷机与 SSH](docs/01_BOARD_BOOT.md)：**只给 Radxa USB-C 供 5V**，先独立启动。
3. [02 · HD1910 单舵机、总线与 IMU](docs/02_SERVO_IMU.md)：每次只推进一个可测、可断电的步骤。
4. [03 · 整机分级通电与首次运动](docs/03_POWER_INTEGRATION.md)：必须通过独立供电/映射/IMU/支架验收。
5. [04 · 仿真、HD1910 训练与导出](docs/04_SIM_TRAINING.md)：CPU 回放、GPU 冒烟、训练、ONNX 验证；**仿真通过不等于真机可用**。

项目管理入口：[Roadmap](ROADMAP.md) · [逐项 Checklist](CHECKLIST.md) · [上游来源、同步与证据](docs/05_EVIDENCE_AND_SOURCES.md)。

## 目录与继承关系

| 内容 | 目录 / 命令 | 作用 |
|---|---|---|
| 本仓库文档与工具 | `docs/`、`scripts/`、`upstreams/` | 版本化、可审核 |
| 官方 RL（本机已有，忽略 Git） | `microduck_rl/` | **XL330 官方基线**；不要当作 HD1910 实机驱动 |
| 官方 Rust runtime（本机已有，忽略 Git） | `microduck/` | 官方 Dynamixel 路径；飞特需要匹配的总线适配 |
| 官方 ONNX（本机已有，忽略 Git） | `policies/official/` | 对齐 61→14 观测/动作接口，不是 HD1910 上机许可 |
| 原有便捷回放 | `./play.sh walk`、`./play.sh velstand` | **官方 XL330 仿真**，不是 HD1910 仿真 |
| 原有官方同步 | `./update.sh` | 同步本机的官方仓库与 HF Policy；会移动本地依赖版本 |
| 新增社区上游追踪 | `python3 scripts/sync_upstreams.py check` | 只检查远端 SHA；默认不合并、不运行第三方代码 |

S0–S2 新工具：[自动化教程与三张现场验收卡](docs/06_S0_S2_AUTOMATION.md) · [空白舵机台账](templates/hd1910_inventory.csv) · [独立映射模板](templates/hd1910_mapping.json)。`diagnose_radxa.py` 仅采集；`validate_servos.py` 仅静态检查；均不写串口/寄存器。原始证据默认本地保存，分享前人工脱敏。

在 **Linux/WSL 开发电脑仓库根目录**执行 `python3 scripts/run_checks.py --output .evidence/acceptance-first` 保存测试与上游查询结果；预期软件检查 PASS，模拟夹具不代表实机。也可单独执行 `python3 scripts/verify_workspace.py` 验证本仓库文档与清单；上游同步工具用法见 [来源说明](docs/05_EVIDENCE_AND_SOURCES.md)。

保留原有学习笔记：[快速上手](notes/00_快速上手.md) · [2026-10-12 官方同步记录](notes/01_同步记录_2026-10-12.md)。
这些记录是**历史实测**，不代表 2026-10-14 已重新测试过本机环境。

## 必须遵循的边界

- Radxa ZERO 3W **仅能输入 5V**。HD1910 的 2S 电池母线不能直接接板子；HAT 的 5V 输出必须先实测。
- HAT、舵机、IMU 存在**不同硬件/协议分支**。无实物版本、可信原理图与引脚核对，不能照抄他人三针线序。
- 初次启动不要同时给 HAT 和 USB-C 两路电源，除非确证该 HAT 的电源路径允许，且已测无反灌。
- 没有实际电气测量、各舵机 ID/方向/限位和 IMU 的通过记录，不允许把软件健康状态等同于真机安全。
- AI、CI、Coding Agent 可以做代码、文档、协议模拟和日志分析，**不能代替万用表测量/断电检查/现场急停**。

本工作区以“自动审查优先、必须人手操作时逐项说明、每个阶段形成可复核证据”为原则。

本轮结果与限制：[2026-10-14 S0–S2 自动准备记录](records/2026-10-14_s0-s2-automation.md)。硬件阶段保持 S0 进行中，S1/S2 未验收。
