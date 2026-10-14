# MicroDuck 实机实验记录 · 分阶段证据索引

**用途**：本目录只存放适合公开 GitHub 仓库、经过操作者审查和脱敏的**真实实验记录**，不是原始数据倾倒区；不代表目录存在就已完成任何 S0–S9 验收。

## 统一执行顺序

```text
A. Codex（现在即可）: 原理图与固件研究 → 兼容性静态检查 → 离线测试、教程与验收模板
B. 操作者（现在可并行）: 按 docs/07 做 S0、S1、S2 的独立硬件实验
C. 操作者：原始数据放 .evidence/ 或 local/（Git 忽略）→ 在 records/field/ 提交脱敏小结
D. Codex / ChatGPT：核对小结及提供的材料 → 标出 PASS/FAIL/BLOCKED 与未验证项 → 规划下一步
E. 只有物理与软件前置安全 Gate 均通过，才执行 S3/S5 的供电/使能/运动
```

**A 不依赖 B 完成。** Codex 缺少实物时不得伪造硬件实测，也不应停掉可独立完成的代码研究。B 的 S1 单板独立启动、S2 单舵机只读可以在安全前提下并行；C/D 必须依赖真实采集数据；E 有独立硬门槛。

## 两层存储（仓库公开，请谨慎分享）

| 层次 | 推荐目录 | 内容 | GitHub / 云端 Agent 是否能看到 |
|---|---|---|---|
| **原始私有** | `/.evidence/<阶段>/<run-id>/` | `summary.json`、`raw/`、串口日志、照片、视频、设备地址、原始表格、诊断报告 | **不会自动同步**：已在 `.gitignore`。只有本机同目录的 Agent 或显式提供的附件可以访问 |
| **个人工作配置** | `/local/` | 尚未脱敏的舵机 CSV、关节映射、配置草稿 | **不会自动同步**：已在 `.gitignore` |
| **共享审查记录** | `/records/field/<阶段>/YYYY-MM-DD_<实验>.md` | 脱敏的测量值、设备版本、采集条件、原始文件 SHA256、结果状态与限制 | 审查后明确 `git add` / commit / push，远端 Agent 才能读取 |
| **自动软件证据** | `/.evidence/software/<run-id>/` | 测试输出、模拟夹具和上游 HEAD 对比 | 仅软件，不属于实机通过；可在审查后写入脱敏 Markdown 摘要 |

> 原始证据留在 Git 忽略目录，不等于备份完成。应自行另行备份在可信的本地/私有存储；为安全审查而上传到公开 GitHub 的日志/照片并不安全。GitHub 公共历史即使后来删除文件，之前的提交仍可能被人取得。

### 当前可用的阶段目录

| 阶段 | 提交脱敏摘要到这里 | 操作者任务 |
|---|---|---|
| S0 | [s0-hardware/](s0-hardware/README.md) | 实物、型号、C1 原理图、供电路径、断电通断测量 |
| S1 | [s1-radxa/](s1-radxa/README.md) | ZERO 3W V1.12 独立启动、系统日志、SSH |
| S2 | [s2-servos/](s2-servos/README.md) | 15 个 HD1910 唯一 ID 与 2048 机械零位只读复核 |
| S3 供电 | [s3-hat-power/](s3-hat-power/README.md) | HAT C1、电池座、稳压、极性、保护与隔离 |
| S3 IMU | [s3-imu/](s3-imu/README.md) | 第三方 ID200 IMU 额定电压、身份、姿态和角速度比例 |
| S4 | [s4-simulation/](s4-simulation/README.md) | CPU 回放、GPU Smoke Test、checkpoint、ONNX |
| S5–S9 | [s5-s9-motion/](s5-s9-motion/README.md) | 分级上力、HOME、行走、Sim-to-Real 及迭代记录 |

## 首次怎么保存：完整例子

**开发电脑 Linux/WSL，在本仓库根目录执行**，以下不会连接硬件：

```bash
# 仅在本机创建私有原始证据区域（所有原始文件默认不提交）
mkdir -p .evidence/s0-hardware .evidence/s1-radxa .evidence/s2-servos
mkdir -p .evidence/s3-hat-power .evidence/s3-imu .evidence/software

# 复制统一模板，日期和实验标识改成实际值
cp records/TEMPLATE.md records/field/s1-radxa/2026-10-14_H1_first-boot.md

# 只读/离线的软件检查：每次提供一个新的、尚不存在的 output 目录
python3 scripts/run_checks.py --output .evidence/software/check-first
```

`run_checks.py` 会检查本仓库的软件与上游，**不会代替 ZERO 3W 真机检测**。`--output` 已存在时脚本刻意拒绝覆盖，下一次换成新的 `check-second` 或带时间戳名称即可。

[06 · 自动化与现场验收卡](../../docs/06_S0_S2_AUTOMATION.md) 有 `diagnose_radxa.py` 和 `validate_servos.py` 的实际用法。板上 `diagnose_radxa.py` 若已保存 `~/microduck-diagnostic/.evidence/s1-first/`，**在开发电脑**确认 SSH 指纹后可按实际用户名/IP将整个目录复制回本机 `.evidence/s1-radxa/`，例如：

```bash
RADXA_TARGET='实际用户名@实际IP'
scp -r "${RADXA_TARGET}:microduck-diagnostic/.evidence/s1-first" .evidence/s1-radxa/
```

先在 H1 六要素卡里完成供电/隔离验收。以上 `scp` 是复制私有原始证据，**不是提交 GitHub**。

## 每份要提交的 Markdown 最少写什么？

从 [统一模板](../TEMPLATE.md) 复制，然后真实填写：**阶段与时间、被测实物型号/固件/PCB Rev、所用源码和镜像版本、实际命令和前置状态、原始记录本地相对路径及 SHA256、逐项预期和实测、PASS/FAIL/BLOCKED、失败停止/恢复动作、尚未验证的边界、下一步。**

- **只报告能证实的事情**。示例/模拟/文档推导/用户口述应写清来源类型，不能冒充现场读数。
- **硬件通过不等于机器人可动**：S1 成功 SSH ≠ HAT 供电通过；S2 FD 搜到一只舵机 ≠ 15 路 ID/中位都正确；S3 读到 IMU ≠ 可运行 Policy。
- **没有数据时用 BLOCKED，不写 PASS**；允许填入真实失败结果，不能覆盖或删除失败证据来“变绿”。
- 发布前逐项检查是否暴露 Wi-Fi 密码、IP/MAC、SSH 主机密钥/指纹、token、密码、个人/设备序列号、住址、包含二维码的图片或身份信息。
- 如需远程 Codex 自动检查，请提交**脱敏摘要**到此目录；需要详细轨迹时先清理并以安全的文件附件提供，**不要让 Agent 自动把 `.evidence/` 全量上传 GitHub**。

手动检查待提交文件（在开发电脑）：

```bash
git status --short
git add records/field/s1-radxa/2026-10-14_H1_first-boot.md
git diff --cached --check
git diff --cached
```

**确认内容已脱敏后**，再由操作者显式 commit/push；如果仍含私密数据则 `git restore --staged <文件路径>` 并回到本地修改。不要用 `git add -A` 意外纳入任何私有附件。

### 和 CHECKLIST 的关系

目录/空白模板存在 **不构成验收**。每次进入联合评审时，由人工或 Agent 将记录与 [CHECKLIST.md](../../CHECKLIST.md) 中同一条验收项目绑定；只有证据覆盖了检查项的全部前提，才允许把对应 `[ ]` 改为 `[x]`，且写明记录路径和仍未证明的部分。

本工作区是公开仓库，不是认证过的硬件实验室数据存储或自动化部署系统。

2026-10-14 软件准备交付见[本轮审查摘要](../2026-10-14_s1-s3-review.md)，人工最短路径见[docs12](../../docs/12_MINIMAL_OPERATOR_STEPS.md)。该摘要是软件记录，没有生成任何真实实验PASS；现场阶段仍需操作者按现有目录提交脱敏证据。
