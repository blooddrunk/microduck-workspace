# 04 · MicroDuck 仿真与强化学习：从零上手到可复现实验

> **当前主线是纯软件 S4，不要求 ZERO 3W、C1 HAT、IMU、HD1910 实物或电源通过验收。** 本教程对应 CHECKLIST.md 中的 S4 分阶段 Gate；硬件安全闸门仍遵守 03_POWER_INTEGRATION.md。命令在 **Linux / Ubuntu / WSL2 的 Linux 终端**运行，默认从本工作区根目录开始。2026-10-15 已自动完成部分固定来源、CPU ONNX 和 BAM 检查；实际结果见[本轮脱敏记录](../records/field/s4-simulation/2026-10-15_s4-bam-evaluation.md)。教程里的 GUI、CUDA 训练和用户自己训练的 Policy 仍需按各 Gate 实际执行。

## 0. 先看全貌：这次到底在学什么？

`机器人模型(MJCF) + 环境(Env) + 控制器/执行器(BAM 或 PD)` 定义“虚拟鸭子如何运动”；`Policy` 是读取观测后输出 14 个关节动作的神经网络；`PPO` 用并行仿真轨迹反复更新 Policy；`checkpoint (.pt)` 是训练过程状态；`ONNX` 是导出后的推理模型。CPU MuJoCo 回放使用**已有** Policy，不是在训练新 Policy；mjlab / MuJoCo Warp + PPO 训练通常需要 NVIDIA CUDA GPU。

`物理状态 → 61D Actor Observation → Policy → 14D Action → HOME + scale + 执行器模型 → 动力学/接触 → 下一帧`

- 控制频率：基线 50 Hz（每 20 ms 一次 Policy）；仿真物理步长参考 5 ms、decimation 4。**请以本次锁定的任务配置为准**，不能把历史数值当硬编码事实。
- 14 个策略关节 ≠ 15 颗舵机：嘴部舵机计入机器人质量，但不由行走 Policy 的 14D 输出驱动。
- Actor 使用能部署的观测；Critic 在训练阶段可能用额外特权信息，不能把 Critic 观测塞进 ONNX Actor。
- reward 是“希望学会什么”的训练信号，不等于真实可走路；domain randomization 是对质量、摩擦、延迟等做扰动来降低仿真与真实世界差距。
- **不要一次学习所有任务**：先只做 `Mjlab-Velocity-Flat-MicroDuck-HD1910` 平地速度跟踪，再考虑站起、复杂地形与动作切换。

术语自测：可以用自己的话区别 `模拟回放` / `训练`、`迭代 iteration` / `episode`、`checkpoint` / `ONNX`、`BAM` / `PPO`，再进入第 1 步。

## 1. 推荐路线与每关通过条件

| Gate | 你做的事 | 不需要 GPU？ | 必须亲自看到/保存什么 | 何时进入下一关 |
|---|---|---|---|---|
| S4-0 | 静态检查与固定来源 | 是 | 两套源码 SHA、版本锁、目录隔离 | 来源可信，命令与路径明确 |
| S4-1 | 官方 XL330 CPU 回放（可选） | 是 | 已有模型的 GUI 回放与截图 | 能解释“看的是已训练的策略” |
| S4-2 | HD1910 现成 ONNX CPU 回放（**第一目标**） | 是 | SHA256、窗口/日志、至少一次速度指令/重置 | 画面正常、数值有限 |
| S4-3 | HD1910 GPU 64 env × 5 iter Smoke | 否 | CUDA 证明、loss/日志、真实 checkpoint | 训练完整退出；不能以 5 iter 当训练成功 |
| S4-4 | 可控的长训与指标分析 | 否 | 固定配置、曲线、多个 checkpoint、A/B 记录 | 看到有意义的行为而非仅 reward 上升 |
| S4-5 | 单环境 play + 导出 ONNX | 导出/检查视依赖而定 | 回放视频、PT/ONNX 数值与 61→14 合同 | 导出正常；**仍不允许直接上真机** |
| S4-6 | 厂商 BAM 独立验证与对照 | 静态和 CPU 阶段不需要 | M1–M6 模型证据、兼容性差异、可复现 A/B | 只有通过一致性测试才考虑后续 GPU 重训 |

**默认按顺序 S4-0 → S4-2 → S4-3 → S4-4 → S4-5**。S4-1 是额外教学基线；S4-6 可在 CPU 阶段并行开展，但不能替换 S4-2 的现有暂定模型。飞特 BAM 调研与独立操作见 [13 · HD1910 厂商 BAM 评估](13_FTSERVO_BAM_RESEARCH.md)。

## 2. S4-0：软件环境与来源固定（先执行）

### 2.1 选机器，不先折腾硬件

| 你当前的环境 | 现在适合干什么 | 不适合承诺什么 |
|---|---|---|
| Windows 11 + AMD CPU/核显，无 NVIDIA | WSLg 中的 CPU 回放（前提是 WSL2 和图形环境正常），阅读代码、检查 ONNX、分析离线日志 | 官方 MuJoCo Warp 的 CUDA 训练 |
| Ubuntu Linux 桌面（无 NVIDIA） | CPU MuJoCo、ONNX 推理、BAM 参数研究 | 大规模 mjlab PPO |
| Ubuntu + NVIDIA CUDA GPU | 上述全部，先 64×5 Smoke | 不能未经 Smoke 直接上 4096 env |
| 有权限使用的云 Ubuntu + NVIDIA | GPU Smoke / 长训；日志和 checkpoint 拉回本地 | 不能默认官方 `--hf-jobs` 同时兼容 HD1910 fork |

如 Windows 的 WSL2 本身无法启动，**不要为本教程冒险修复/修改现有 VHDX 权限**；可改用独立 Ubuntu 机器或云端。所有训练使用 PC/GPU，**不在 ZERO 3W 上进行 PPO**。

### 2.2 开始前核对工具

S4-2 CPU 数值检查至少需要 Python 3.12、uv、锁定 HD1910 fork 的依赖与 ONNX 快照；可视化另需 Linux 图形窗口/GLFW。S4-3 还要求 NVIDIA GPU、可用驱动和 CUDA。不要把 WSLg 的 DISPLAY 变量当作 GUI 已可渲染，也不要把带 CUDA wheel 的 PyTorch 当作 GPU 已可用。

~~~bash
python3 --version
uv --version
nvidia-smi
~~~

如果没有 nvidia-smi，S4-3 记为 BLOCKED，可继续做 CPU/BAM 检查。锁定环境建好后运行自动预检；它会写一份本地 report.json，明确分列来源、Python 依赖、ONNX 数值、GUI 线索和 CUDA：

~~~bash
python3 scripts/check_s4_environment.py --output-dir .evidence/s4-simulation/<new-run-id>-preflight
~~~

预检中的 GUI 状态只是 DISPLAY/Wayland 环境提示，不是打开窗口的证据；ONNX 零向量有限值只证明推理数值路径可执行，不证明动作语义、站立或行走。

### 2.3 先保存软件基线

在本工作区根目录：

~~~bash
pwd
python3 --version
git --version
python3 scripts/verify_workspace.py
python3 scripts/sync_upstreams.py check
~~~

通过：本工作区的静态校验通过；`sync_upstreams check` 的 HEAD 漂移被审查。**注意：`fetch` 默认拉取远程最新 HEAD，不会自动 checkout sources.json 的 pinned SHA。** 若显示 UPDATE_AVAILABLE，必须记录差异并先审核，不应继续宣称正在复现旧版结果。

不要运行 `./update.sh` 来准备 HD1910；它针对本机原有官方克隆，会移动基线。不要覆盖本工作区中被 Git 忽略的 `microduck_rl/` 和 `policies/official/`。

### 2.4 单独获取 HD1910 研究分支

~~~bash
# 只对需要的上游做克隆；放入被忽略的 .upstreams/，不覆盖官方 baseline
python3 scripts/sync_upstreams.py fetch --name hd1910-rl
git -C .upstreams/hd1910-rl rev-parse HEAD

# 对照 sources.json 中 hd1910-rl 的 sha；版本不同，先停下检查
cd .upstreams/hd1910-rl

# Linux Ubuntu；必要系统包（有 sudo 权限时安装）
# sudo apt update && sudo apt install -y git curl build-essential libgl1 libegl1 libglfw3

# 需要 uv (Astral)：如未安装，先按 https://docs.astral.sh/uv/ 官方说明安装
uv --version
export UV_HTTP_TIMEOUT=600
uv python install 3.12
uv sync --locked --python 3.12
uv run --locked python - <<'PY'
import mjlab.tasks
from mjlab.tasks.registry import list_tasks
task = 'Mjlab-Velocity-Flat-MicroDuck-HD1910'
assert task in list_tasks(), task
print('PASS: registered', task)
PY
~~~

通过：uv.lock 未发生重解锁；任务注册断言输出 `PASS`。若安装出现 GPU/CUDA 依赖下载，**CPU 回放不代表一定不下载 CUDA wheel**；磁盘和网络空间要预留。不要运行 uv lock 或 pip install -U 来解决兼容问题后不留版本记录。

本节来源：锁定的 [qiaosiyi HD1910 fork](https://github.com/qiaosiyi/microduck_rl_hd1910/tree/hd1910) 与 [fork 中文 README](https://github.com/qiaosiyi/microduck_rl_hd1910/blob/hd1910/README.zh-CN.md)，而非官方 XL330 配置。

补充：固定 SHA 的 `list-envs` 会打印任务表但以退出码 46 结束，因为上游把任务数作为退出码返回。教程用上面的带断言检查，避免新手把这个上游行为误判为环境安装失败。

## 3. S4-1（可选）：先看官方 XL330 CPU 回放

如**此前本机**已有 `microduck_rl/`、`policies/official/`、`~/.local/bin/uv` 与可工作的 GUI，回到工作区根目录运行：

~~~bash
./play.sh walk
~~~

这只证明官方 **XL330** 基线的 Policy 在 CPU MuJoCo 中可以回放，**与 HD1910 执行器没有建立兼容性证明**。如果这些被忽略的目录并不存在，直接 **SKIP（缺少本机历史依赖）**，不必为完成 S4-2 而补齐。记录官方 clone 的 SHA、Policy SHA256、画面与控制是否响应；历史演示视频不能冒充自己的执行结果。

## 4. S4-2：第一次运行 HD1910 CPU MuJoCo（建议从这里开始）

下面从 `.upstreams/hd1910-rl/` 根目录执行。**不需要 NVIDIA GPU，不接任何实体舵机**。

### 4.1 先核对已发布的快照

~~~bash
cd models/hd1910-walking-iter-2000
sha256sum -c SHA256SUMS
cd ../..

# 检查 CPU 推理参数，确保用的是本次分支的 CLI
uv run --locked scripts/infer_policy.py --help
~~~

预期：哈希全部 PASS；能够看到 `--motor-profile`、`--walking` 和 `--vin`。如果快照不完整、指纹失败或文件不可读，STOP，不要从不明网站下载同名 ONNX 覆盖。

### 4.2 运行可视化回放

~~~bash
# Ubuntu 桌面 / WSLg 有显示窗口的 Linux 终端
MUJOCO_GL=glfw uv run --locked scripts/infer_policy.py \
  --motor-profile hd1910 \
  --vin 7.4 \
  --walking models/hd1910-walking-iter-2000/policy.onnx
~~~

观察顺序（每步都应实际操作）：窗口打开 → 模型加载 → 查看终端内的按键说明 → 发一次低速前进指令 → 停下 → 重置 / 再观察 → 正常退出。

| 你看到的现象 | 如何解释/处理 |
|---|---|
| 鸭子响应输入且继续仿真 | CPU 回放路径已跑通，但这不是自己训练的策略 |
| 数值出现 NaN / Inf、动作剧烈发散 | 失败；保存完整错误与输入条件，不能勾 PASS |
| 无 DISPLAY / GLFW 创建窗口失败 | 优先检查 WSLg、桌面 OpenGL 与终端 `DISPLAY`；这是渲染问题，不等同模型问题 |
| 原生 Windows 报 `termios` 找不到 | 当前脚本面向 Linux 终端；使用 Ubuntu/WSL，不要把安装包强行混装 |
| 站不稳或跌倒 | 如实记录；2000-iter 是中间快照，不能据此宣称完整步态或实机可靠 |

#### Windows 11 + WSL2/WSLg：OpenGL 画面卡顿时

MuJoCo 窗口在 WSLg 中仍由 Linux 进程创建；如果窗口卡顿，先确认 OpenGL 是否退回了 `llvmpipe` 软件渲染。WSLg 的 Mesa D3D12 路径可用 `glxinfo -B` 查看，硬件加速时 renderer 应显示 `D3D12 (<GPU 名称>)` 和 `Accelerated: yes`（GPU 字符串依机器而异）。参见 [Microsoft WSLg 的 GPU 选择说明](https://github.com/microsoft/wslg/wiki/GPU-selection-in-WSLg)。

~~~bash
# 若 glxinfo 尚未安装，仅安装这个诊断工具
command -v glxinfo >/dev/null || sudo apt install -y mesa-utils
GALLIUM_DRIVER=d3d12 glxinfo -B
~~~

如果输出仍为 `llvmpipe`，当前图形上下文仍在软件渲染。若显示 D3D12 和 GPU 名称，可在**同一个 WSL Linux 终端**用以下命令重启回放：

~~~bash
cd .upstreams/hd1910-rl
GALLIUM_DRIVER=d3d12 MUJOCO_GL=glfw uv run --locked scripts/infer_policy.py \
  --motor-profile hd1910 \
  --vin 7.4 \
  --walking models/hd1910-walking-iter-2000/policy.onnx
~~~

`GALLIUM_DRIVER=d3d12` 只对这次启动的进程生效；已打开的 viewer 需要退出后重开。若加上此设置后 `glxinfo` 仍报告 `llvmpipe`，将 GUI 渲染记为 BLOCKED/PARTIAL，并继续可执行的无窗口 CPU 检查，不要把它记成模型推理失败。该设置只影响图形渲染，不会启用 CUDA 训练。

这个脚本从**启动它的终端**读取方向键，而不是从 MuJoCo 窗口读取。让终端保持焦点后按 ↑，终端应打印 `Vel cmd: [...] [walking]`；按 Space 清零，按 Q 退出。如果速度命令已打印而鸭子动作仍弱或跌倒，应单独评估当前中间 Policy 的行为，不要把 renderer 已加速当成策略通过。

### 4.3 无图形界面时的退路

能运行纯 Python/依赖时，先完成静态模型检查与 fork 的 CPU 回归；在支持 EGL 的环境再运行数值验证。`MUJOCO_GL=egl` 依赖驱动与 OpenGL/EGL 实现，**不能保证所有纯 CPU 主机都能用**。

~~~bash
# 返回工作区根目录运行固定离线检查；结果写入被 Git 忽略的 .evidence/
cd ../..
python3 scripts/run_checks.py --output .evidence/s4-simulation/<new-run-id>-workspace-checks
cd .upstreams/hd1910-rl

# 可选：先运行 --help 检查，再执行真实校验
uv run --locked scripts/validate_hd1910.py --help
mkdir -p ../../.evidence/s4-simulation/<new-run-id>-cpu-validation
MUJOCO_GL=egl uv run --locked scripts/validate_hd1910.py \
  --onnx models/hd1910-walking-iter-2000/policy.onnx \
  --output ../../.evidence/s4-simulation/<new-run-id>-cpu-validation/cpu-validation.json
~~~

特别注意：`validate_hd1910.py` 的**进程退出成功不等于站姿/行为检查全部通过**；必须逐项打开 JSON，区分数值有限性、姿态稳定性与已知失败项目。`hd1910_validation.json` 可能进入上游工作目录：不应直接提交到公共仓库。

本机 2026-10-15 自动 CPU 验证中，发布 ONNX 的 float32 接口是 [1,61] → [1,14]；100 个 Policy 控制步/400 个物理步（2 秒）输出有限。另 8 组静止姿态都超过 82° 倾斜并跌倒。因此 CPU 数值 rollout 为 PASS，当前验证器的站姿行为检查为 FAIL；零速度短 rollout 不等于速度跟踪或走路成功，GUI 键盘响应也没有在本轮确认。

**S4-2 Gate**：记录 SHA、环境、实际运行命令、模型哈希、测试结果、至少一次 GUI 控制响应和观察结论；没有真实显示/日志时保持 BLOCKED 或 PARTIAL，不写“已完成 CPU 回放”。

### 4.4 按调用链读代码

建议沿着一次控制步阅读，而不是先读完整训练框架：

1. 任务 ID 与 provisional 执行器配置在锁定 fork 的 src/mjlab_microduck/tasks/__init__.py、microduck_hd1910_env_cfg.py 和 actuator/hd1910.py。
2. Hd1910ActuatorCfg 构造实际执行器；Policy 的 14 维 action 会经过任务 action scale/HOME 映射，再变成关节目标。执行器计算力矩并交给 MuJoCo，下一次 observation 才回到 Policy。
3. CPU 推理入口 scripts/infer_policy.py 加载已有 ONNX 与 normalizer，组装 61D observation、执行 inference session、输出 14D action。它是使用已有 Policy，不调用 PPO。
4. GPU 训练入口 train Mjlab-Velocity-Flat-MicroDuck-HD1910 按 task registry 构造并行环境；PPO 收集 rollout、算 advantage/loss、更新 Actor/Critic 并保存 checkpoint。Smoke 只验证训练闭环，不代表 Policy 已学会走。

## 5. S4-3：第一次 PPO 训练，只做 64 环境 × 5 次迭代

**只在 Ubuntu + 可用 NVIDIA CUDA GPU 执行。** 若你当前只有 AMD 核显，先完成 S4-2、S4-6 的 CPU 研究，等有 GPU 后再做本关，不推荐在 CPU 上硬跑 4096 个环境。

~~~bash
# 仍在 .upstreams/hd1910-rl/
nvidia-smi
uv run --locked python -c "import torch; print(torch.__version__, torch.version.cuda); assert torch.cuda.is_available(), 'CUDA unavailable'"
uv run --locked python - <<'PY'
import mjlab.tasks
from mjlab.tasks.registry import list_tasks
task = 'Mjlab-Velocity-Flat-MicroDuck-HD1910'
assert task in list_tasks(), task
print('PASS: registered', task)
PY

uv run --locked train Mjlab-Velocity-Flat-MicroDuck-HD1910 \
  --env.scene.num-envs 64 \
  --agent.max-iterations 5 \
  --agent.save-interval 5 \
  --agent.logger tensorboard \
  --agent.run-name hd1910_smoke \
  --agent.resume False
~~~

若参数被上游更改，先运行 `uv run --locked train --help` 并按锁定源码修正，不要凭猜测绕过报错。常见的 rollout 配置是每环境 24 steps，因此 64 × 24 × 5 = **7680 条 transition**；这不是 7680 个 episode，且必须先核对实际 rollout steps。

### Smoke 必查项

- [ ] 实际拿到 `nvidia-smi` + `torch.cuda.is_available() == True`；CUDA 版本与驱动可见。
- [ ] 5 个 iteration 完成并正常退出；无 NaN/Inf、CUDA OOM、Warp 初始化或梯度异常。
- [ ] 看到 reward、episode length、policy/value losses、action std，均为有限值；曲线“方向正确”不能凭 5 次断言。
- [ ] `find logs/rsl_rl -name 'model_*.pt' -type f` 确实能找到本次运行的 checkpoint；核对修改时间和 experiment 名。
- [ ] 保存任务 ID、环境数量、seed（从配置读取）、源码 SHA、`uv.lock` 哈希、GPU 型号、训练命令、日志路径及 checkpoint hash。
- [ ] 未宣称鸭子已经会走路、未尝试部署真机。

看 `logs/rsl_rl/velocity_hd1910_provisional/` 下的实际 run 子目录；可以使用：

~~~bash
find logs/rsl_rl -name 'model_*.pt' -type f
uv run --locked tensorboard --logdir logs/rsl_rl --host 127.0.0.1 --port 6006
~~~

浏览器打开 `http://127.0.0.1:6006`。远端 GPU 可用 `ssh -L 6006:127.0.0.1:6006 user@server` 转发，不要为了访问 TensorBoard 将端口无鉴权暴露到公网。

### Smoke 操作卡：前置、判定、停止、重试与回滚

从工作区根目录开始；不要从 ZERO 3W 或其他硬件上启动训练。

~~~bash
set -o pipefail
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE="$PWD/.evidence/s4-simulation/$RUN_ID"
mkdir -p "$EVIDENCE"
python3 scripts/check_s4_environment.py --output-dir "$EVIDENCE/preflight"
cd .upstreams/hd1910-rl

git rev-parse HEAD | tee "$EVIDENCE/source-sha.txt"
sha256sum uv.lock | tee "$EVIDENCE/uv-lock-sha.txt"
nvidia-smi | tee "$EVIDENCE/nvidia-smi.txt"
uv run --locked python -c 'import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available()); assert torch.cuda.is_available(), "CUDA unavailable"' 2>&1 | tee "$EVIDENCE/torch-cuda.txt"

uv run --locked python - <<'PY' 2>&1 | tee "$EVIDENCE/task-check.txt"
import mjlab.tasks
from mjlab.tasks.registry import list_tasks
task = 'Mjlab-Velocity-Flat-MicroDuck-HD1910'
assert task in list_tasks(), task
print('PASS: registered', task)
PY

RUN_NAME="hd1910_smoke_$RUN_ID"
touch "$EVIDENCE/train-start.marker"
uv run --locked train Mjlab-Velocity-Flat-MicroDuck-HD1910 \
  --env.scene.num-envs 64 \
  --agent.max-iterations 5 \
  --agent.save-interval 5 \
  --agent.logger tensorboard \
  --agent.run-name "$RUN_NAME" \
  --agent.resume False 2>&1 | tee "$EVIDENCE/train.log"

find logs/rsl_rl/velocity_hd1910_provisional -type f -path "*/${RUN_NAME}*/model_*.pt" \
  -newer "$EVIDENCE/train-start.marker" -size +0c -print | tee "$EVIDENCE/checkpoint-candidates.txt"
test -s "$EVIDENCE/checkpoint-candidates.txt"
while IFS= read -r checkpoint; do sha256sum "$checkpoint"; done \
  < "$EVIDENCE/checkpoint-candidates.txt" > "$EVIDENCE/checkpoint-sha256.txt"
~~~

**进入 PASS 的条件：** CUDA 预检为 true；任务注册断言通过；训练命令正常退出并有 5 次迭代的日志；loss、reward、episode length、action std 均为有限值；本次新 run 目录下至少有一个非空 checkpoint，保存其 SHA256。checkpoint 是“训练真的写出文件”的证据，不等于 Policy 行为评估通过。

**停止和判定：** 找不到 GPU、CUDA 不可用、task ID 不匹配时不启动训练，记 BLOCKED 并保留预检日志。CUDA OOM、Warp 初始化/编译异常、NaN/Inf、进程异常退出或没有 checkpoint 时停止本次，标 FAIL；如只执行了更少环境/迭代或日志/检查点不完整，记 PARTIAL。不要调低环境数后把它记作 64×5 PASS，不要用零向量 ONNX 测试替代训练。

**重试：** 先读 train.log 的第一条异常，确认磁盘空间、GPU 进程、驱动与锁定 SHA；不要运行 uv lock 或 pip install -U。使用新的 RUN_ID/RUN_NAME，保持相同的 64×5 参数，避免覆盖上一轮。若失败来自 GPU 资源不足，换可用 GPU 或标 BLOCKED；不同规模的新实验必须另起 Gate 和 run name。

**回滚：** 训练是软件写文件，不会驱动舵机。出现错误时 Ctrl-C 停止当前训练进程；保留 train.log 和 checkpoint 候选供复核。uv run --locked 不应改动 uv.lock；检查 git status，若出现源码修改，停止并单独审查，不要用 reset --hard 清理用户状态。确认需要丢弃产物时，只处理这次 RUN_NAME 对应的日志目录；先把证据备份到私有 .evidence/，不要删除其它运行或发布快照。

**提交证据：** 将 source SHA、uv.lock SHA256、GPU/driver、精确命令与退出状态、训练日志、实际环境数/迭代数、seed、TensorBoard 路径和 checkpoint SHA 放入私有 EVIDENCE 目录。公开记录只填写脱敏摘要；不提交原始大日志、checkpoint、凭据或带设备/网络标识的文件。

## 6. S4-4：开始长训前的 Gate 与第一个完整实验

只有 S4-3 **真实通过**，才考虑正式训练；先读 [HD1910 fork 的训练指南](https://github.com/qiaosiyi/microduck_rl_hd1910/blob/hd1910/README.zh-CN.md) 与锁定源码。下列示例是该 fork 的起点，不是必须训练的资源量：

~~~bash
uv run --locked train Mjlab-Velocity-Flat-MicroDuck-HD1910 \
  --env.scene.num-envs 4096 \
  --agent.max-iterations 6000 \
  --agent.save-interval 100 \
  --agent.logger tensorboard \
  --agent.run-name hd1910_walking_4096 \
  --agent.resume False
~~~

4096/6000 是实验预算示例，不是保证出好策略。显存不足按 64 → 256/512 → 1024 → 4096 梯度式提升，并记录 num_envs 改变可能影响采样统计；别未经评估修改 PPO 的超参数。要复现实验，固定环境 seed、配置、commit、依赖锁、质量惯量、控制频率、reward、randomization 和运行名称。

### 怎么读训练图表（每隔一定迭代复核）

| 指标 | 关心的问题 | 异常时的排查方向 |
|---|---|---|
| mean reward + 分项 reward | 是否只是靠某个奖励刷分 | 逐项看速度跟随、姿态、步态、能耗惩罚 |
| mean episode length / fall / reset | 是否站得更久、摔得更少 | 初始姿态、质量分布、终止条件、命令难度 |
| velocity tracking error | 是否真的按指令前/后/转 | command 范围、观察与 reward 定义 |
| action rate / torque / jitter | 是否疯狂抖关节刷分 | P/D、延迟、缩放、动作正则化 |
| value loss / surrogate loss / KL / entropy 或 action std | PPO 更新是否健康 | 更新幅度、学习率、归一化、探索方差 |
| curriculum stage | 难度增加时表现是否断崖下跌 | 课程阶段与数据覆盖是否匹配 |

要**同时看曲线和视频**：reward 变高仍可能是趴着不动、持续抖动或不跟命令。每次只修改一个因素，记录前后版本与同一组评测条件；不要以不同 reward 定义下的“总奖励更大”直接判胜负。

### Resume、warm start 和 checkpoint

- `resume` 是同一任务/实验继续训练，尽量保持全部配置、normalizer 与迭代计数一致；用 fork README 的 `--agent.load-run` / `--agent.load-checkpoint` 命令，不猜路径。
- `warm start` 把旧模型权重当新任务起点，不等于原实验续训，curriculum/step counter 可能需要重置；不能只把旧 checkpoint 路径换成新的就当同一个训练。
- 每次训练至少保留**多个** checkpoint（不是只保留“最好一次”），同时记录选取标准与回退路径。

## 7. S4-5：从 checkpoint 观察，再安全导出 ONNX

### 7.1 看一只鸭子的训练结果

在实际完成 S4-4 后，把路径替换成自己磁盘上**真实存在的**文件：

~~~bash
uv run --locked play Mjlab-Velocity-Flat-MicroDuck-HD1910 \
  --checkpoint-file 'logs/rsl_rl/velocity_hd1910_provisional/<run-directory>/model_XXXX.pt' \
  --num-envs 1 \
  --viewer viser
~~~

按终端提示访问 Viser（常用 8080 端口）；远端需做 SSH 转发。重复至少三组可比较的场景：零速站姿、低速前进与转向、可复现的扰动/重置。记录每组持续时间、命令、跌倒、身体姿态、抖动、是否恢复，不要只选好看的 3 秒。

### 7.2 使用 fork 自带 exporter（包含观察归一化）

~~~bash
mkdir -p artifacts
uv run --locked scripts/export.py Mjlab-Velocity-Flat-MicroDuck-HD1910 \
  --checkpoint-file 'logs/rsl_rl/velocity_hd1910_provisional/<run-directory>/model_XXXX.pt' \
  --num-envs 1 \
  --onnx-file artifacts/hd1910_walking.onnx
sha256sum artifacts/hd1910_walking.onnx
~~~

**切勿只把 PyTorch Actor 裸转换成 ONNX**：原训练使用的 observation normalizer 必须烘焙进输出模型。现成 ONNX 快照不属于你自己训练的成果。

### 7.3 检查形状、数值和语义

~~~bash
uv run --locked python - <<'PY'
import numpy as np
import onnxruntime as ort

p = "artifacts/hd1910_walking.onnx"
sess = ort.InferenceSession(p, providers=["CPUExecutionProvider"])
inp, out = sess.get_inputs(), sess.get_outputs()
assert len(inp) == len(out) == 1, (inp, out)
assert inp[0].shape[-1] == 61, inp[0].shape
assert out[0].shape[-1] == 14, out[0].shape
assert inp[0].type == out[0].type == "tensor(float)"
x = np.zeros((1, 61), dtype=np.float32)  # 仅做接口/有限性检查，不是有效真实观测
y = sess.run(None, {inp[0].name: x})[0]
assert y.shape == (1, 14) and np.isfinite(y).all(), y
print("PASS: float32 61 -> 14 interface and finite zero-vector inference")
PY

MUJOCO_GL=egl uv run --locked scripts/validate_hd1910.py \
  --onnx artifacts/hd1910_walking.onnx \
  --output artifacts/hd1910_validation.json
~~~

以上输入零向量只测**结构与有限性**，不是证明性能、normalizer 正确或与 checkpoint 数值等价；必须用 fork 的数值验证或针对**同一真实 Actor 观测**比较 PT/ONNX 输出。逐项审查：61D 字段顺序/单位、14D joint order、HOME、action scale、actor normalizer、上一动作、IMU 坐标、command 13D slot、动作与观测延迟。模型满足 61→14 不等于 HD1910 runtime 能驱动真机。

## 8. S4-6：厂商 BAM 模型现在怎么用？

阅读 [13 · 飞特 HD1910 BAM 证据、参数、风险与 A/B 计划](13_FTSERVO_BAM_RESEARCH.md)。推荐先仅下载 `ftservo/ftservo-bam` 的版本化快照、检查 m1–m6 JSON 与 Python 源码；然后在**与 HD1910 fork 隔离的 Python 3.12 环境**做 CPU 加载/验证；最后才给 Codex 研究“是否有必要在训练代码中做可选的 BAM backend”。

- **绝不覆盖** `.upstreams/hd1910-rl` 的默认执行器、`uv.lock` 或历史 checkpoint 来“快速验证”。
- 厂商的 7.4V 识别结果与暂定 PD 模型结构不同；不等同于“修一个参数”；尤其检查驱动固件/控制模式和 BAM 注册表大小写。
- 以后 A/B 必须用一致的 robot geometry、mass、joint order、command、随机种子、评测窗口和统计口径。先做 CPU 单舵机/单场景行为比较，GPU 长训属于下一阶段。
- 厂商 `bam/feetech/record.py` 包含**真实舵机读写/运动命令**；当前 S4 软件研究禁止运行这类采集脚本。

## 9. 固定证据目录与每次实验可复制模板

原始训练日志、视频、设备信息、本地路径与云端凭据只保留在工作区 **`.evidence/s4-simulation/<run-id>/`**（已被 Git 忽略）；训练 fork 的 `logs/` 和模型留在被 Git 忽略的 `.upstreams/` 内。对重要 checkpoint 自行异地备份；**Git 忽略并不等于备份**。

公开 GitHub 中只提交经人工脱敏的 `records/field/s4-simulation/YYYY-MM-DD_<实验名>.md` 摘要。按 [S4 证据模板说明](../records/field/s4-simulation/README.md) 与 [统一实验模板](../records/TEMPLATE.md) 填写，不向公共仓库提交 W&B API key、SSH 配置、原始家庭网络地址、云 token 或未经清理的大文件。

每条摘要至少包含：日期/平台/GPU、源码和 lock SHA、Policy/checkpoint SHA256、精确 CLI、`PASS/FAIL/PARTIAL/BLOCKED/SKIP`、预期与实际、关键指标、日志及视频**本地路径**、失败堆栈摘要、后续行动及未验证边界。**没有证据的步骤保持未完成**。

## 10. 常见错误速查

| 问题 | 优先排查 | 不要做 |
|---|---|---|
| `uv sync --locked` 失败 | Python 是否 3.12、torch/CUDA index、网络/磁盘、锁版本、上游 SHA | 悄悄重解锁并称“复现” |
| `nvidia-smi` 不存在 | 目前机器是否真的有 NVIDIA GPU、驱动/容器透传 | 认为 AMD 核显有 CUDA |
| `termios` / `glfw` 失败 | 是否使用 Linux 终端，WSLg/桌面/display/EGL | 把渲染失败算作训练失败 |
| GPU OOM / Warp import error | torch、warp、mjlab、mujoco-warp 约束；降低 num_envs | 混装厂商 BAM 的不兼容版本 |
| Loss 为 NaN 或动作发散 | 日志中第一处非有限值、奖励/obs、接触、dt、PD、归一化 | 继续长训直到“自然修复” |
| 有 checkpoint 却不会走 | Smoke 没有训练成熟；检查回放、长度和 reward 分项 | 只看 `model_*.pt` 存在就合格 |
| ONNX 形状正确但行为异常 | normalizer、HOME、关节顺序、控制律、IMU、延迟 | 直接把模型下发到真机 |

**本教程的完成定义**：至少亲自跑通 S4-2，获得明确的真实日志与画面；有 NVIDIA GPU 时再按 Gate 做训练、评估和导出。当前没有 GPU 时，`S4-3/S4-4` 保持 BLOCKED 是正确且可审核的结果。
