# 04 · MicroDuck 仿真训练实验线（与电控调试并行）

**目标：** 建立“官方 XL330 基线 → HD1910 专用 CPU 回放 → HD1910 GPU Smoke Test → 完整训练 → ONNX 导出 → 真机对齐”的完整可复现链路。CPU 回放不需要 CUDA；训练需要 NVIDIA CUDA GPU 或经验证的云方案。

## 两套仿真不能混成一套

- 本工作区 `microduck_rl/` 和 `./play.sh`：本机已有的官方 **XL330** 基线，不要直接拿它验证 HD1910 动力学。
- [qiaosiyi/microduck_rl_hd1910](https://github.com/qiaosiyi/microduck_rl_hd1910/tree/hd1910)：HD1910 分支，有独立的 provisional actuator、训练任务和带归一化的 2000-iter ONNX **快照**。
- [LuwuDynamics/xgoduck_rl](https://github.com/LuwuDynamics/xgoduck_rl)：含已公开的 1910 M6 参数研究，适合做交叉核对；不同项目的参数识别来源、舵机固件/增益/模型结构未必相同。
- [kissqy/Microduck-kissqy](https://github.com/kissqy/Microduck-kissqy)：还包含 HD1910 runtime/控制台/训练界面及真实运行视频；其 Policy 必须和随包部署合同匹配，不能直接拷进另一种 runtime。

上游快照按 [同步说明](05_EVIDENCE_AND_SOURCES.md) 使用 `python3 scripts/sync_upstreams.py check` / `fetch --name hd1910-rl`；所有引用必须记录 SHA。以下路径假设已执行 fetch，代码位于 `.upstreams/hd1910-rl/`。切换不同 fork 时不要覆盖当前 `microduck_rl/`。

## A. 在现有电脑做 CPU 仿真：先验官方，再验 HD1910

```bash
# 从此仓库根目录；如果本机原有官方环境尚在
./play.sh walk
```

这是**官方 XL330 回放**。请记录运行日期、`git -C microduck_rl rev-parse HEAD`、屏幕是否出现窗口及异常日志。旧笔记 2026-10-12 的成功记录不应当作今天已经重测。

```bash
python3 scripts/sync_upstreams.py fetch --name hd1910-rl
cd .upstreams/hd1910-rl
uv sync --locked --python 3.12

# Linux/WSLg 带 GUI 的终端；初次下载依赖可较慢
MUJOCO_GL=glfw uv run --locked scripts/infer_policy.py \
  --motor-profile hd1910 --vin 7.4 \
  --walking models/hd1910-walking-iter-2000/policy.onnx
```

检查：画面加载成功、指令响应、有稳定的 observation/action、日志无 NaN/Inf；注意它是**初步适配模型上的 CPU 回放**，不能据此承诺实物站立。

模型目录内有 `SHA256SUMS` 和 `verification.json`，先检查文件完整性（Linux / WSL）：

```bash
cd models/hd1910-walking-iter-2000
sha256sum -c SHA256SUMS
cd ../..
```

记录下载 commit、验证输出、ONNX 的 SHA256、视频/回放异常。**切勿把 fork ONNX 和官方 XL330 runtime 任意混用。**

## B. 有 CUDA GPU 后，只跑 5 次迭代（不是训练完成）

在 HD1910 分支根目录：

```bash
nvidia-smi
uv run --locked list-envs
uv run --locked train Mjlab-Velocity-Flat-MicroDuck-HD1910 \
  --env.scene.num-envs 64 \
  --agent.max-iterations 5 \
  --agent.save-interval 5 \
  --agent.logger tensorboard \
  --agent.run-name hd1910_smoke \
  --agent.resume False
```

这套命令来自 HD1910 分支 README；先核对当前 CLI `--help`，如果选项已改变则依据 pinned 源码修正并记录。一个常见配置是 24 rollout steps/env；**如果源码仍使用这个值**，64×24×5 = 7680 条 transition（不是 7680 个 episode）。

自动检查清单：进程成功结束、没有 NaN/Inf、loss 有限、reward 非零、重置计数合理、有 `model_*.pt` 的真实文件且可用于回放。对失败项保存错误堆栈和环境版本，不得写“训练已完成”。

观察：mean reward、mean episode length、velocity tracking、upright、air time、fell over、action rate、value loss、surrogate loss、mean action std、curriculum。**5 iterations 只用于验证训练循环**，获得的 Policy 通常不能走路。

如果本机只有 AMD 核显/无 NVIDIA CUDA，跳过 B 的本机执行，改为 CPU 回放与软硬件调试；**不要执行 CPU 硬撑 4096 env**。云端 GPU 是否可用、费用、HF Jobs 对这个 HD1910 fork 是否兼容都需独立确认；官方 RL 支持 `--hf-jobs` 不代表 fork 必然支持同样的云流程。

## C. 完整训练（延后，基于验收进行）

满足 B 且有 GPU 资源后，参考 [HD1910 作者训练指南](https://github.com/qiaosiyi/microduck_rl_hd1910/blob/hd1910/README.zh-CN.md) 的 4096 env/6000 iterations 示例，按显存、日志和步态质量调整。开训练前固定 seed、commit、`uv.lock`、环境任务、所有舵机模型参数、实验名和预期停止条件。

至少保存：训练曲线、`agent.yaml`、`env.yaml`、多个 checkpoint、模型评估视频。**高 reward 不意味着能走**；结合持续时间、速度跟随、跌倒/重启、抖动和姿态判定。如果接触/电机参数不可信，先做系统辨识，不要靠增加训练轮数补偿硬件误差。

## D. 导出并验证 ONNX

不要自己裸转 checkpoint；使用 fork `scripts/export.py`，让 Observation Normalizer 烘焙到 ONNX。示例：

```bash
uv run --locked scripts/export.py Mjlab-Velocity-Flat-MicroDuck-HD1910 \
  --checkpoint-file 'logs/rsl_rl/velocity_hd1910_provisional/<你的实验目录>/model_XXXX.pt' \
  --num-envs 1 \
  --onnx-file artifacts/hd1910_walking.onnx
```

先确认 `artifacts/` 存在、把示例占位符替换为真实路径。验证输入形状 **float32 [1,61]**，输出 **float32 [1,14]**，与真实 actor 对同一原始 Observation 输出数值一致。还要审核 joint order、HOME、action scale、命令槽位、IMU 坐标、角速度单位、旧动作和延迟；ONNX 结构正确不代表这些语义正确。导出后只进入“待 S6/S7 验证”状态。

## E. Sim-to-Real 的实验账本

一次改一个因素：总质量/质心/惯量、执行器输出曲线、P/D（真机固件值与仿真 PD 参数不能混为一谈）、齿隙、命令/观测延迟、IMU 安装误差、供电掉压及摩擦。每次实验保留 `records/TEMPLATE.md` 要求的“配置 hash + 测量条件 + 数值 + 视频 + 结论局限”，而不是仅写“效果有提升”。

**不可自动执行的环节**：GPU 训练没有真实可用 GPU 时标记阻塞；实机加载任何 Policy 必须先过 [03 分级上电](03_POWER_INTEGRATION.md) 的硬件闸门。
