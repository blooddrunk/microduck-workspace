# MicroDuck HD1910 复刻 Roadmap（滚动更新）

**基线日期：2026-10-27** · 硬件：飞特 HD1910 × 15 + Radxa ZERO 3W V1.12（rk3566）+ Pollen C1 HAT + 总线 ID200 IMU + 唯卓仕 F550。
**当前实况：整机已组装、标定并运行**（kissqy R5 派生系统；机器人名 duck-a437），详见 [duck/README.md](duck/README.md)。

> **2026-10-27 门禁豁免决定**：S0–S3 的形式化验收证据（断电测量、备用卡、单舵机台架读回、IMU 四方向实测等）
> 不再补做——整机已由团队线下完成装配/标定/通电并长期运行，继续要求这些证据没有意义。
> 新的证据基线是 [duck/snapshots/ 实况快照](duck/snapshots/2026-10-27_runtime/README.md)（只读巡检、
> 标定档案、运行时配置、策略 provenance）。豁免不等于"验证过"：下列历史风险（供电反灌、IMU 协议分支、
> 第三方镜像标定）在**换件/换镜像/重新接线时重新生效**，届时必须重走对应检查。

## 阶段总览（2026-10-27 重估）

```text
S0 盘点 ─ S1 主板 ─ S2 舵机 ─ S3 电控/IMU ─ S5 整机上电 ─ S6 HOME ─ S7 站立/低速
   └─（以上各阶段实践中已完成，形式化证据豁免，见上）─┘
S4 仿真/训练 ═════════════════▶ S8 Sim-to-Real 对比 ──▶ S9 自有 Policy 闭环
   （进行中：CPU 回放已通；      （未开始）            （部分达成：板上 6 个策略
    CUDA/GPU 训练未开始）                              出自 kissqy 训练台，非本仓库管线）
```

| 阶段 | 状态（2026-10-27） | 依据 |
|---|---|---|
| S0 盘点与风险隔离 | **实践完成**（型号齐全入 [hardware 档案](hardware/observed-2026-10-14.json)；断电测量等证据豁免） | 2026-10-14 照片审查 |
| S1 主板独立 Bring-up | **实践完成**（Armbian 26.2.1 常驻运行，SSH/密钥体系就绪） | [快照 system/services](duck/snapshots/2026-10-27_runtime/) |
| S2 单舵机台架 | **豁免**（标定经 kissqy 运行时整机完成，无逐只台架读回；标定档案已存 [snapshots/calibration](duck/snapshots/2026-10-27_runtime/calibration/)） | 本页豁免决定 |
| S3 电控与 IMU | **实践完成**（整机供电长期运行，IMU `imu_mount_verified=true`，总线 IMU 正常上报） | robotd 日志/标定 |
| S4 HD1910 仿真 | **进行中**：S4-2 CPU 数值回放通过、BAM M1–M6 CPU 对比完成；CUDA/GPU 训练与 GUI 回放未开始 | [S4 记录](records/field/s4-simulation/) |
| S5 整机卸力上电 | **实践完成**（团队线下完成；形式化健康报告以 2026-10-27 快照补录） | duck/snapshots |
| S6 受限 HOME | **实践完成**（15 关节零位标定，`calibrated=true`，含 .previous/.saved 历史档） | calibration 快照 |
| S7 站立与低速 | **实践完成**（行走/坐站/翻滚/踢球/捡物可运行；安全 deadman 实测在工作） | 部署策略 + 手册 16 |
| S8 Sim-to-Real 对比 | **未开始**（有价值：现有 6 策略出自社区训练台，与本仓库仿真可互相对照） | — |
| S9 自有 Policy 迭代 | **部分达成**（已有自训策略部署闭环，但训练出自 kissqy training-console；本仓库自有 S4 管线到 ONNX 上机的闭环未打通） | provenance 快照 |

## 当前工作流（代替原"最短路径"）

三条并行线，优先级从高到低（与 [手册 17 优化清单](docs/manual/17-team-workflow.md) 一致）：

1. **运维加固线（P0）**：处理 mediad 崩溃循环（NRestarts 497→重启后 17min +123）；
   鸭子本体装 Tailscale 根治异地连通；板上无版本代码（zhangtong/shishaodong/voice 各目录）收进本仓库 `apps/`；
   评审低电保护（`battery_empty_shutdown`/`limp_fall` 均 false）与 powerlog 数据。
   P1：语音进程 systemd 化（`duck-voice.service` 已有未启用）、SSH 收敛纯密钥、journald 限容。
2. **自有训练线（S4）**：等 GPU 条件完成 S4-3～S4-5（64×5 smoke → 长训 → ONNX 导出契约），
   之后按手册 16 §5 流程上机，形成本仓库自己的 Policy 闭环（S9 完全体）。
3. **语音线**：本地 ASR（sherpa-onnx int8）替代云端讯飞——密钥不再上板、断网可用；
   唤醒词本地化；intent 规则库扩充。代码正本迁入仓库后一起版本化。

## 不做的事（2026-10-27 修订）

- 不把官方 XL330 的 10 份 ONNX 当作 HD1910 "开箱即可运动"的 Policy（板上是自训 + kissqy 系，不是官方权重）。
- 不把 kissqy 镜像的**示例标定**当作本机标定——现在有自己的标定档案（snapshots/calibration），换镜像/换件后必须重新标定并存档。
- 不绕过白名单直写鸭子系统路径（`/etc`、`/opt`）；推送只走 `push-duck.sh` 的 `~/microduck-tools/`。
- 不在无人监护时远程触发行走/翻滚等策略动作；重启服务/鸭子前不打招呼。
- 不把"脚本能连上""仿真回放正常"当作实机安全结论；实机安全以现场监护与急停为准。
- 不以 Issues 驱动个人研发；优先持续维护本 Roadmap、CHECKLIST、duck/ 快照和小批次 commit。

**维护方式**：每次巡检后更新 [duck/README.md](duck/README.md) 一页纸状态并生成新快照；
阶段状态变化更新本页与 [CHECKLIST.md](CHECKLIST.md)；第三方变动先
`python3 scripts/sync_upstreams.py check`，完成自动审查后才引入。

## 历史记录（保留存档）

- [2026-10-14 S0–S2 自动化准备](records/2026-10-14_s0-s2-automation.md)：只读采集工具、台账模板、证据包格式。
- [2026-10-14 实物照片审查](records/2026-10-14_hardware-photo-review.md)：V1.12 / C1 HAT / HD-1910-C001 / ID200 型号确认。
- [2026-10-14 S1–S3 兼容性审查](records/2026-10-14_s1-s3-review.md)：C1 电气候选表、QinmoTech IMU 差异、15→14 合同、V1.12 引导回退。
- [2026-10-15 上游同步](records/2026-10-15_upstream-sync.md) · [S4 BAM 评估](records/field/s4-simulation/2026-10-15_s4-bam-evaluation.md) · [社区策略筛选](records/field/s4-simulation/2026-10-16_community-policy-evaluation.md)。
- [2026-10-27 实况同步与手册](records/2026-10-27_duck-sync-and-manuals.md)：豁免决定的原始背景与本页依据。
