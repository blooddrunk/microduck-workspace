# 13 · 飞特 HD1910 BAM 模型研究与兼容性实验方案

> 截至 2026-10-15 静态审查；**没有在本机运行训练或连接实物舵机**。本文件是 [04 仿真入门教程](04_SIM_TRAINING.md) 的可选研究支线（S4-6）。

## 1. 来源与已核实事实

用户发现 [Gitee: ftservo/ftservo-bam](https://gitee.com/ftservo/ftservo-bam)。本轮 Gitee 无法直接取得仓库内容，**不能证明 Gitee 与 GitHub 的提交相同**。但 GitHub 存在 [ftservo/ftservo-bam](https://github.com/ftservo/ftservo-bam)，账户名为 `ftservo`，主分支 `main` 在本轮取得的 commit 是：

`4f7c0b0de3debf9c1ab254fc9654676e8aab9317`（2026-09-30）。

在该固定提交下查到：

- [M1–M6 参数目录](https://github.com/ftservo/ftservo-bam/tree/main/bam/params/feetech_hd1910_7_4V)：`m1.json` 至 `m6.json` 六套 HD1910、7.4V 模型。
- [专用执行器](https://github.com/ftservo/ftservo-bam/blob/main/bam/feetech/actuator.py)：`HD1910Actuator`，默认 `vin=7.4`、`kp=32`、`error_gain=0.163`、`max_pwm=0.97`，初始 `kt=0.61`、`R=5`、`armature=0.001`（被参数 JSON 覆盖时除外）。
- [BAM 模型及载入器](https://github.com/ftservo/ftservo-bam/blob/main/bam/model.py)：六种逐级复杂摩擦模型；`load_model` 从 `params/<motor_name>/<model>.json` 载入，再由参数里的 `actuator` 字段构造电机对象。
- [mjlab 集成](https://github.com/ftservo/ftservo-bam/blob/main/bam/mjlab.py)：`BamActuatorCfg`、`bam_init`、`frictionloss` / `damping` 写回与可选电压/摩擦随机化。
- [辨识采集脚本](https://github.com/ftservo/ftservo-bam/blob/main/bam/feetech/record.py)：经 `scservo_sdk` 发送舵机**读写命令**，包含真实位置目标、使能等副作用；**本轮绝不执行**。
- `pyproject.toml` 的 mjlab extra 约束：`mjlab>=1.3,<1.4`、`mujoco-warp>=3.7,<3.8`、`mujoco>=3.7,<3.8`、`warp-lang>=1.12,<1.13`；与既有 HD1910 fork 版本必须逐项评估，不能在其 `uv.lock` 上直接安装覆盖。

以上说明存在厂商账号发布的辨识成果，但不自动证明你的 **HD-1910-C001 固件/模式/P 增益/电压/负载**与采集条件一致，也没有本轮对厂商身份独立法律验证。

## 2. 已发现的重要兼容性风险（先解决再跑）

**风险 A：大小写与注册不一致。** [actuators.py](https://github.com/ftservo/ftservo-bam/blob/main/bam/actuators.py) 注册的是大写 `"HD1910"`，M6 JSON 的 `"actuator"` 为小写 `"hd1910"`，目录名是 `feetech_hd1910_7_4V`。因此以下是**待验证示例**，不要直接宣称一定可用：

```python
from bam.model import load_model
model = load_model(motor_name="feetech_hd1910_7_4V", model="m6")
```

在不修改原文件的前提下做负向测试与注册表单元测试：加载失败时记录精确异常、定位调用链。修复应优先在**隔离 fork/适配层**通过显式别名或规范化处理，补齐双大小写和负向测试；不要悄悄改源 JSON 并冒充厂商原版。必须对 `bam/feetech/actuator.py`、`bam/model.py`、`bam/actuators.py` 实际版本做逐项核查。

**风险 B：不是同一种执行器动力学。** [qiaosiyi HD1910 fork](https://github.com/qiaosiyi/microduck_rl_hd1910/blob/hd1910/docs/hd1910_adaptation.md) 是基于 datasheet 的 **provisional PD/DC motor**，保留 61D → 14D Policy 接口；HD1910 fork 的 15–30ms 延迟等未标定。飞特 BAM 是电压控制 + 电机反电动势 + 速度/负载相关摩擦预算；其 M6 JSON `command_delay≈0.000978s` 是辨识模型中的命令延迟参数，**不能未经统一观测/通信/固件延迟定义，就替代 fork 的 15–30ms 端到端假设**。两者的 torque/friction、限流与重置机制都不同。

**风险 C：参数数字是条件性的。** 厂商 M6 JSON 中：`kt≈0.564499`、`R≈2.966476`、`armature≈0.00182739`、`friction_base≈0.0119507`、`friction_viscous≈0.0047672`、`model=m6`、`actuator=hd1910`。这些是文件值，不能断言对所有 HD1910/固件模式/电池电压成立。不同模型中的 `kt`、`R`、摩擦系数不可当作 datasheet 上的 7.4V 输出额定扭矩；不应再额外乘齿轮比。关键原文件 [m6.json](https://github.com/ftservo/ftservo-bam/blob/main/bam/params/feetech_hd1910_7_4V/m6.json)。

**风险 D：GPU API/解算器依赖。** `bam.mjlab` 每环境写动态 frictionloss/damping，涉及 `bam_init` startup event、per-world model expansion、BAM actuator reset、MuJoCo Warp 的静摩擦约束近似。不能直接在 qiaosiyi fork 中替换 `Hd1910Actuator`，否则可能出现双重摩擦、双重限速、错误的模型字段或 GPU 版本不兼容。

**风险 E：其它社区模型不能直接等同。** LuwuDynamics 和 JoyandAI 也有 HD1910/BAM 方向的工作，但固件、供电、采样条件、参数标定与质量/物理配置不同。可以做对比，不可以当成同一标定结果或混用 checkpoint。

## 3. 从安全静态核验到 A/B 对比的执行顺序

### 3.1 B0：安全静态审查（无 GPU、无硬件）

在本工作区根目录：

```bash
# 上游目录彼此隔离；审核仓库来源后再运行仓库内任何代码
git clone --filter=blob:none https://github.com/ftservo/ftservo-bam.git .upstreams/ftservo-bam
git -C .upstreams/ftservo-bam checkout --detach 4f7c0b0de3debf9c1ab254fc9654676e8aab9317
git -C .upstreams/ftservo-bam rev-parse HEAD
python3 -m json.tool .upstreams/ftservo-bam/bam/params/feetech_hd1910_7_4V/m6.json >/dev/null
git -C .upstreams/ftservo-bam status --short
```

记录 `HEAD`、六份 JSON 的 SHA256、`pyproject.toml`，检查许可证（Apache-2.0）以及 Gitee 来源映射；若远端提交不可获得，**保持 BLOCKED**，不自动使用 HEAD 顶替版本。首次导入第三方代码先审查安装脚本、依赖和实际调用副作用。

### 3.2 B1：独立 Python 3.12 环境做 CPU Model Load（不触碰 fork）

```bash
cd .upstreams/ftservo-bam
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e .
.venv/bin/python - <<'PY'
from bam.model import load_model
print("Attempting stock vendor m6 load...")
m = load_model(motor_name="feetech_hd1910_7_4V", model="m6")
print(type(m.actuator).__name__, m.kt.value, m.R.value)
PY
```

**这是一条故意验证原版是否能加载的测试，不承诺 PASS。** 失败（尤其 `KeyError: 'hd1910'`）应保存错误并标记为 *vendor stock load failed*；然后由 Codex 在独立实验分支修复大小写/注册问题并跑回归，不修改保存的厂商快照。本命令不会主动连接舵机；但安装及运行第三方 Python 仍应先审查。

若需要更复杂的 MuJoCo CPU 单摆模型，必须先查明和复用 vendor `bam.mujoco` 官方入口与例子，保证相同 `dt`、电压、目标轨迹、初始角、重力、负载，不可用不同动力学偷偷替换评估目标。

### 3.3 B2：先模拟单舵机，再谈机器人 A/B

从低到高依次验证：

1. JSON 可载入、参数有限值、`M1–M6` 每组可分别构造、reset 状态正确。
2. 在相同初始化/负载/轨迹中比较 **M1 与 M6** 的位置曲线、稳态误差、延迟、峰值速度、输出扭矩、动态摩擦与数值稳定性。
3. 对旧 provisional PD 模型跑**同条件**对照。注明两边控制器定义差异；若需要改信号合同，先保留不同实现而非强制数值一致。
4. 有真实台架数据之前，只能得出**两个仿真模型存在的行为差异**，不能说哪个更符合你手中的 HD1910；有实测后比较位置/速度轨迹 MAE、RMSE 和触发饱和的时段。
5. 最后才尝试在**单独 feature 分支和独立 lock 环境**挂载 BAM GPU backend，运行 1 env / reset → 64 env × 5 iteration → CPU/GPU 轨迹一致性 → 长训。**默认实现仍保留 provisional backend**。

### 3.4 B3：避免虚假优胜者的实验设计

| 固定量 | 记录 |
|---|---|
| 机器人 geometry / mass / CoM / inertia | 完整文件 SHA、15 颗舵机质量假设 |
| Policy/任务/命令 | 61→14、HOME、action scale、关节顺序、seed、command 序列 |
| 执行器 | 模型类型、JSON SHA、实际 P 增益/firmware mode（未知就写未知） |
| 供电/延迟 | 输入电压、电压下跌假设、command_delay vs observation delay |
| 评测 | 平地静止、低速正反向、转弯、扰动、掉落后重置；指标、截图和日志 |

对比同一 Policy 在不同执行器模型下的行为是**敏感性分析**；对两个模型分别重训后再对比是**训练设计实验**，二者结论不能混为一谈。

## 4. 当前推荐技术决策

**立即使用：** 把 ftservo-bam 的 HD1910 M1–M6 作为重要的独立参数与物理模型来源，开展静态核查和隔离 CPU 研究。

**暂不使用：** 不直接覆盖 qiaosiyi fork 的 `Hd1910Actuator`、BAM 依赖锁、历史 ONNX / PT 或任何实机寄存器。

**后续是否迁移的 Gate：** vendor stock load 问题及测试修复 → 依赖/API 可运行 → 单摆稳定且对照可复现 → CPU/GPU 模型合同 → 64×5 Smoke → 训练/评估改善有证据 → 才考虑在 HD1910 分支默认启用。实机验证还需要单独的电气和零位闸门，完全不属于本轮。

## 5. 记录与移交

- 本地原始：`.evidence/s4-simulation/<run-id>/`、被忽略的 `.upstreams/` 下的日志、视频、模型；仅脱敏 Markdown 摘要提交 `records/field/s4-simulation/`。
- 每份报告注明实际是否运行（**本轮为未执行**）、HEAD/hash、Python/uv/CUDA 版本、命令、stdout/stderr、PASS/FAIL/BLOCKED、模型误差及限制。
- Gitee 与 GitHub 一致性若无法证明，写“GitHub 同名 ftservo 发布源已核实，Gitee 镜像身份/提交一致性待确认”，不要写“官方完全证实”。
