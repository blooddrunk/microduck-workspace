# MicroDuck HD1910 复刻与 Sim-to-Real 工作区

> 2026-10-14 起以 **飞特 HD1910 + Radxa ZERO 3W (RK3566)** 为目标硬件。此仓库是个人实验记录，不代表官方或第三方固件已经适配你的实物。

## 现在先做什么

**当前硬件阶段：S0 实物型号部分确认 → S1 主板独立启动 / S2 舵机只读复核；当前软件优先：S4 CPU 仿真与 PPO 分阶段学习。** 已有 ZERO 3W V1.12、Pollen C1 HAT、HD-1910-C001、FE-URT2-C001、第三方 ID200 IMU；**HAT、IMU、电源尚未完成电气验收。** 不要直接整机通电、使能全部舵机或执行行走 Policy。

**推荐阅读与操作路径（以当前这套实物为起点）：**

1. **先看 [07 · 我的硬件第一轮实操](docs/07_MY_HARDWARE_FIRST_STEPS.md)**：针对 ZERO 3W V1.12、C1 HAT、HD1910 和第三方 IMU 的当前任务与阻塞点。
2. 对照 [00 · 实物盘点与安全](docs/00_START_HERE.md)，补齐供电、线序、PCB 版本等尚未确认的信息。
3. 按 [01 · ZERO 3W 独立启动](docs/01_BOARD_BOOT.md) 刷机 / SSH；此时**不接 HAT、舵机、IMU 或 F550 电池**。
4. 使用 [09 · 2048 中位复核](docs/09_HD1910_ZERO_REVIEW.md) 核查已有校准，再按 [02 · HD1910 舵机与 IMU](docs/02_SERVO_IMU.md) 补充单舵机只读台账；不要立即重写零位。
5. 阅读 [08 · 第三方 IMU 兼容性](docs/08_VENDOR_IMU_COMPATIBILITY.md)，先确认供电范围、身份寄存器和角速度比例；用 [06 · S0–S2 自动化工具](docs/06_S0_S2_AUTOMATION.md) 保存诊断证据。

**软件先行（无需实物）：** 从 [04 · 循序渐进仿真与强化学习教程](docs/04_SIM_TRAINING.md) 的 S4-0、S4-2 CPU 检查开始，再单独研究 [13 · 厂商 HD1910 BAM](docs/13_FTSERVO_BAM_RESEARCH.md)。2026-10-15 已验证 ONNX CPU 数值 rollout、发现静止姿态测试失败并完成 BAM M1–M6 CPU 敏感性对比；当前没有可用 CUDA GPU，GUI 回放和训练 Smoke 仍未完成。详见[本轮脱敏记录](records/field/s4-simulation/2026-10-15_s4-bam-evaluation.md)。

**后续阶段**：仅在前置电气验收通过后进入 [03 · 整机分级通电](docs/03_POWER_INTEGRATION.md)；[04 · HD1910 仿真与训练](docs/04_SIM_TRAINING.md) 可以作为独立软件工作流并行学习，不代表实机可安全运行 Policy。

项目管理：[Roadmap](ROADMAP.md) · [逐项 Checklist](CHECKLIST.md) · [实物硬件档案](hardware/observed-2026-10-14.json) · [照片与协议审查记录](records/2026-10-14_hardware-photo-review.md)。

## 实况手册与鸭子运维（2026-10-27 新增）

鸭子已完成组装、调零标定并能运行策略与语音控制。日常操作看 **[docs/manual/ 实用手册系列](docs/manual/README.md)**（14 连接 · 15 状态巡检 · 16 网页与策略 · 17 协作与优化），
当前实况看 **[duck/ 鸭子实况档案](duck/README.md)**（一页纸状态 + 网络身份证 + 每日快照），
一键工具在 **[scripts/duck/](scripts/duck/README.md)**（`status-duck.sh` 只读巡检、`pull-duck.sh` 快照回仓、`push-duck.sh` 白名单上板、`tunnel-duck.sh` 异地隧道）。
标定与运行时配置的最新存档：[duck/snapshots/2026-10-27_runtime/](duck/snapshots/2026-10-27_runtime/README.md)。

## 完整文档导航（docs/ 00–13，共 14 篇）

> **文件编号是主题编号，不是强制执行顺序**。当前应从 **07** 入手；03 的通电操作需要先通过安全闸门。

| 编号 | 文档 | 适用阶段 / 主要用途 |
|---|---|---|
| 00 | [实物盘点与安全闸门](docs/00_START_HERE.md) | S0：硬件型号、供电拓扑、引脚与上电安全 |
| 01 | [ZERO 3W 刷机、开机与 SSH](docs/01_BOARD_BOOT.md) | S1：主板脱离外设的 5V 独立启动 |
| 02 | [HD1910 单舵机、总线与 IMU](docs/02_SERVO_IMU.md) | S2：FE-URT2 只读扫描、ID / 方向 / 参考姿态 |
| 03 | [HAT、IMU 与整机分级通电](docs/03_POWER_INTEGRATION.md) | S3、S5–S7：硬件验收后按 G0–G5 分阶段上电、运动 |
| 04 | [HD1910 仿真、PPO 训练与 ONNX](docs/04_SIM_TRAINING.md) | S4、S8–S9：CPU 回放、GPU Smoke Test、模型导出 |
| 05 | [上游同步与验证证据](docs/05_EVIDENCE_AND_SOURCES.md) | 全阶段：来源可信度、固定 commit、更新审查 |
| 06 | [S0–S2 自动诊断与现场验收卡](docs/06_S0_S2_AUTOMATION.md) | S0–S2：只读脚本、舵机台账、自动验证与证据采集 |
| 07 | **[当前实物专用第一轮教程](docs/07_MY_HARDWARE_FIRST_STEPS.md)** | **当前优先**：V1.12 + C1 HAT + HD1910 的最短路径 |
| 08 | [第三方 ID200 IMU 协议与 FT6 兼容](docs/08_VENDOR_IMU_COMPATIBILITY.md) | S3 前置：供电、身份、帧数据、角速度比例 |
| 09 | [HD1910 的 2048 中位校准复核](docs/09_HD1910_ZERO_REVIEW.md) | S2 前置：机械零位、编码器中位、训练 HOME 的区别 |
| 10 | [C1 电气审查](docs/10_C1_ELECTRICAL_REVIEW.md) | 源码候选引脚与断电测量卡 |
| 11 | [V1.12 引导审查](docs/11_ZERO_V112_BOOT_REVIEW.md) | 备用卡、完整备份与恢复合同 |
| 12 | [本轮最小操作教程](docs/12_MINIMAL_OPERATOR_STEPS.md) | 人工实验前提、命令、停止与证据 |
| 13 | [飞特 HD1910 BAM 厂商模型评估](docs/13_FTSERVO_BAM_RESEARCH.md) | 7.4V M1–M6、注册表大小写与隔离对比，不直接替代已有模型 |

## Codex 与人工操作的顺序、证据在哪里

**不需要先完成三项硬件操作才能运行上一轮 Codex Goal。** Codex 现在先执行 C1 HAT 原理图、第三方 IMU / FT6 合同、HD1910 零位/关节映射、ZERO 3W V1.12 引导条件的**离线审查与工具准备**；你可并行按 [07 实物教程](docs/07_MY_HARDWARE_FIRST_STEPS.md) 完成 S1 单板和 S2 舵机只读。只有 S3 实机验收/最终接线/运动控制需要等现场证据，不得由模拟结果越级宣称通过。

**统一证据入口：[records/field/ 分阶段留存与交接](records/field/README.md)**。原始诊断/照片和个人舵机台账仍保存到被 Git 忽略的 `/.evidence/`、`/local/`；**本仓库是公开仓库**，仅在人工脱敏核对后把实验 Markdown 摘要提交 `records/field/<阶段>/`，以便云端 Codex/ChatGPT 可以审查。空目录或测试脚本 PASS 不是硬件 PASS。

## 目录与继承关系

| 内容 | 目录 / 命令 | 作用 |
|---|---|---|
| 本仓库文档与工具 | `docs/`、`scripts/`、`upstreams/` | 版本化、可审核 |
| 实用手册（新人入口） | `docs/manual/14–17` | 连接/巡检/操控/协作的日常操作层 |
| 鸭子实况档案 | `duck/` | 一页纸状态、网络身份证、sanitized 快照 |
| 鸭子运维工具 | `scripts/duck/*.sh` | 只读巡检、拉取/推送白名单、隧道 |
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

## 2026-10-14 S1–S3 兼容性审查交付

新增：[C1电气候选表](docs/10_C1_ELECTRICAL_REVIEW.md) · [V1.12备用卡与引导回退](docs/11_ZERO_V112_BOOT_REVIEW.md) · **[可执行最小教程](docs/12_MINIMAL_OPERATOR_STEPS.md)** · [本轮记录](records/2026-10-14_s1-s3-review.md)。C1原件及hash固定；QinmoTech文档作为第八个上游。IMU比例/年龄合同不兼容，vendor仅离线诊断；主机校准增加来源/hash只读检查。没有部署或硬件动作。
