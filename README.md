# MicroDuck HD1910 复刻与 Sim-to-Real 工作区

> 2026-10-14 起以 **飞特 HD1910 + Radxa ZERO 3W (RK3566)** 为目标硬件。此仓库是个人实验记录，不代表官方或第三方固件已经适配你的实物。

## 现在先做什么

**2026-10-27 实况：整机已在运行。** 鸭子（duck-a437）完成组装与调零标定（15 关节全部 `calibrated = true`、`motion_enabled = true`），运行 kissqy R5 镜像派生系统，已部署 6 个 2026-10-01 自训策略（行走/坐站/捡物/踢球/翻滚），语音控制在研（讯飞 ASR + 意图解析常驻）。2026-10-27 起原 S0–S3 形式化验收证据（断电测量、单舵机台架读回等）**经决定豁免**，以 [duck/ 实况快照](duck/README.md) 作为新证据基线；安全边界从"上电前防错"转为"运行中防事故"。

**推荐阅读与操作路径（2026-10-27 起）：**

1. **新人第一天：从 [docs/manual 实用手册](docs/manual/README.md) 入手**——14 连接鸭子、15 状态巡检、16 网页操控、17 多人协作与优化清单。
2. 想了解鸭子当前物理/网络/运行时状态：[duck/README.md 一页纸状态](duck/README.md) 与 [duck/network.md 网络身份证](duck/network.md)；日常用 `scripts/duck/status-duck.sh` 只读巡检。
3. 硬件文档（00–13）保留为**参考资料**：供电边界、IMU 协议、零位/关节映射的方法论仍然有效，但其"验收闸门"状态已被上面的豁免决定取代。
4. **自有训练线（S4）继续**：从 [04 · 循序渐进仿真与强化学习教程](docs/04_SIM_TRAINING.md) 的 S4-0、S4-2 CPU 检查开始；2026-10-15 已验证 ONNX CPU 数值 rollout、完成 BAM M1–M6 CPU 敏感性对比；当前没有可用 CUDA GPU，GUI 回放和训练 Smoke 仍未完成（详见[脱敏记录](records/field/s4-simulation/2026-10-15_s4-bam-evaluation.md)）。板上现有 6 个策略出自 kissqy training-console，尚非本仓库 S4 管线产物。

**当前优先级**（详见[手册 17 优化清单](docs/manual/17-team-workflow.md)）：P0 处理 mediad 崩溃循环、板上无版本代码收进本仓库、评审低电保护开关（鸭子本体装 Tailscale 已于 2026-10-28 完成，tailnet IP `100.64.0.12`）；P1 语音进程 systemd 化、SSH 收敛纯密钥；P2 本地 sherpa-onnx ASR。

项目管理：[Roadmap](ROADMAP.md) · [逐项 Checklist](CHECKLIST.md) · [实物硬件档案](hardware/observed-2026-10-14.json) · [照片与协议审查记录](records/2026-10-14_hardware-photo-review.md)。

## 实况手册与鸭子运维（2026-10-27 新增）

鸭子已完成组装、调零标定并能运行策略与语音控制。日常操作看 **[docs/manual/ 实用手册系列](docs/manual/README.md)**（14 连接 · 15 状态巡检 · 16 网页与策略 · 17 协作与优化），
当前实况看 **[duck/ 鸭子实况档案](duck/README.md)**（一页纸状态 + 网络身份证 + 每日快照），
一键工具在 **[scripts/duck/](scripts/duck/README.md)**（`status-duck.sh` 只读巡检、`pull-duck.sh` 快照回仓、`push-duck.sh` 白名单上板、`tunnel-duck.sh` 异地隧道）。
标定与运行时配置的最新存档：[duck/snapshots/2026-10-27_runtime/](duck/snapshots/2026-10-27_runtime/README.md)。

## 完整文档导航（docs/ 00–13，共 14 篇）

> **文件编号是主题编号，不是强制执行顺序**。日常操作看 **docs/manual（14–17）**；00–13 是硬件/仿真专题参考。

| 编号 | 文档 | 适用阶段 / 主要用途 |
|---|---|---|
| 00 | [实物盘点与安全闸门](docs/00_START_HERE.md) | S0：硬件型号、供电拓扑、引脚与上电安全 |
| 01 | [ZERO 3W 刷机、开机与 SSH](docs/01_BOARD_BOOT.md) | S1：主板脱离外设的 5V 独立启动 |
| 02 | [HD1910 单舵机、总线与 IMU](docs/02_SERVO_IMU.md) | S2：FE-URT2 只读扫描、ID / 方向 / 参考姿态 |
| 03 | [HAT、IMU 与整机分级通电](docs/03_POWER_INTEGRATION.md) | S3、S5–S7：硬件验收后按 G0–G5 分阶段上电、运动 |
| 04 | [HD1910 仿真、PPO 训练与 ONNX](docs/04_SIM_TRAINING.md) | S4、S8–S9：CPU 回放、GPU Smoke Test、模型导出 |
| 05 | [上游同步与验证证据](docs/05_EVIDENCE_AND_SOURCES.md) | 全阶段：来源可信度、固定 commit、更新审查 |
| 06 | [S0–S2 自动诊断与现场验收卡](docs/06_S0_S2_AUTOMATION.md) | S0–S2：只读脚本、舵机台账、自动验证与证据采集 |
| 07 | [当前实物专用第一轮教程](docs/07_MY_HARDWARE_FIRST_STEPS.md) | 历史参考：V1.12 + C1 HAT + HD1910 的首轮路径 |
| 08 | [第三方 ID200 IMU 协议与 FT6 兼容](docs/08_VENDOR_IMU_COMPATIBILITY.md) | S3 前置：供电、身份、帧数据、角速度比例 |
| 09 | [HD1910 的 2048 中位校准复核](docs/09_HD1910_ZERO_REVIEW.md) | S2 前置：机械零位、编码器中位、训练 HOME 的区别 |
| 10 | [C1 电气审查](docs/10_C1_ELECTRICAL_REVIEW.md) | 源码候选引脚与断电测量卡 |
| 11 | [V1.12 引导审查](docs/11_ZERO_V112_BOOT_REVIEW.md) | 备用卡、完整备份与恢复合同 |
| 12 | [本轮最小操作教程](docs/12_MINIMAL_OPERATOR_STEPS.md) | 人工实验前提、命令、停止与证据 |
| 13 | [飞特 HD1910 BAM 厂商模型评估](docs/13_FTSERVO_BAM_RESEARCH.md) | 7.4V M1–M6、注册表大小写与隔离对比，不直接替代已有模型 |

## 协作与证据流程（2026-10-27 起）

多人异地同时开发，鸭子是共享实机。流程：代码正本放本仓库（新应用一律放 [apps/](apps/README.md)，
从 `apps/_template/` 起步），经 `scripts/duck/push-duck.sh` 白名单上板；板上改动收工前 `scripts/duck/pull-duck.sh` 存档到
`duck/snapshots/`。**对运行时做任何动作（重启服务、robotctl 控制、重启鸭子）前先在群里打招呼**，
重启前 `w` 看谁在线。

**统一证据入口**：实况以 [duck/](duck/README.md) 快照为准；原始诊断/照片和个人台账仍保存到被
Git 忽略的 `/.evidence/`、`/local/`，**人工脱敏核对后**把实验 Markdown 摘要提交 `records/field/`。
本仓库是公开仓库——凭据、WiFi 密码、`.env`、私钥永不入库。

## 目录与继承关系

| 内容 | 目录 / 命令 | 作用 |
|---|---|---|
| 本仓库文档与工具 | `docs/`、`scripts/`、`upstreams/` | 版本化、可审核 |
| 实用手册（新人入口） | `docs/manual/14–17` | 连接/巡检/操控/协作的日常操作层 |
| 鸭子实况档案 | `duck/` | 一页纸状态、网络身份证、sanitized 快照 |
| 鸭子运维工具 | `scripts/duck/*.sh` | 只读巡检、拉取/推送白名单、隧道 |
| 应用正本 | `apps/<名字>/` | 上板应用（语音/视觉等）的版本化正本；板上只留部署副本（2026-10-28 起，见 [apps/README](apps/README.md)） |
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

## 必须遵循的边界（运行中的实机版）

- Radxa ZERO 3W **仅能输入 5V**。HD1910 的 2S 电池母线不能直接接板子；改接供电前必须实测 HAT 的 5V 输出。
- **`motion_enabled = true`：一上电、给指令鸭子就会动。** 拿起/搬运前先在网页中控松开使能；测试时现场有人、周围清空、急停可达。
- HAT、舵机、IMU 存在**不同硬件/协议分支**。换件/换镜像是新的电气事件，不能默认沿用现有标定与配置。
- 改标定/robotd 配置/换策略属于**高危操作**：备份 toml、现场扶鸭、低增益先行，完成后 `pull-duck.sh` 重新存档。
- 低电自动关机与 limp_fall 目前为**关闭**状态（见 `duck/snapshots/` 的 robotd 配置）：人离开前手动关机。
- AI、CI、Coding Agent 可以做代码、文档、协议模拟和日志分析，**不能代替现场监护、急停与万用表**。

本工作区以"自动审查优先、必须人手操作时逐项说明、每个阶段形成可复核证据"为原则。

硬件阶段历史（S0–S3 形式化验收于 2026-10-27 决定豁免，整机已实际运行）：[S0–S2 自动准备记录](records/2026-10-14_s0-s2-automation.md) · [S1–S3 兼容性审查](records/2026-10-14_s1-s3-review.md) · [实况同步记录](records/2026-10-27_duck-sync-and-manuals.md)。

## 2026-10-14 S1–S3 兼容性审查交付

新增：[C1电气候选表](docs/10_C1_ELECTRICAL_REVIEW.md) · [V1.12备用卡与引导回退](docs/11_ZERO_V112_BOOT_REVIEW.md) · **[可执行最小教程](docs/12_MINIMAL_OPERATOR_STEPS.md)** · [本轮记录](records/2026-10-14_s1-s3-review.md)。C1原件及hash固定；QinmoTech文档作为第八个上游。IMU比例/年龄合同不兼容，vendor仅离线诊断；主机校准增加来源/hash只读检查。没有部署或硬件动作。
