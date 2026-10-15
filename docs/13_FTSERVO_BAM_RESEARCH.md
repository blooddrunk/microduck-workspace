# 13 · 飞特 HD1910 BAM 模型研究与兼容性评估

> 审核日期：2026-10-15。已完成固定源码静态检查、M1–M6 CPU 加载与单舵机敏感性对照。**没有运行采集/标定脚本、没有连接实物舵机、没有做 BAM GPU 训练。** 本文是 [04 仿真入门教程](04_SIM_TRAINING.md) 中可选的 S4-6 支线，不改变默认 HD1910 provisional 执行器。

## 1. 来源、提交关系与许可

用户给出的 [Gitee 仓库](https://gitee.com/ftservo/ftservo-bam) 对应 Gitee 的 FTServo/@ftservo 账号；[GitHub 同名仓库](https://github.com/ftservo/ftservo-bam) 的 main 由 git ls-remote 读取的提交，均在 2026-10-15 指向 SHA 4f7c0b0de3debf9c1ab254fc9654676e8aab9317。这证明审核时两个远端公布了相同提交 ID；它不构成 Gitee 账号所有权、发布者法律身份或镜像签名的独立证明。

仓库 main 在本项目锁定为 [提交 4f7c0b0](https://github.com/ftservo/ftservo-bam/commit/4f7c0b0de3debf9c1ab254fc9654676e8aab9317)，作者/提交者显示为 ftservo。该提交的 [LICENSE](https://github.com/ftservo/ftservo-bam/blob/4f7c0b0de3debf9c1ab254fc9654676e8aab9317/LICENSE) 和 [pyproject.toml](https://github.com/ftservo/ftservo-bam/blob/4f7c0b0de3debf9c1ab254fc9654676e8aab9317/pyproject.toml) 声明 Apache-2.0。pyproject.toml 的发行包名是 better-actuator-models，作者字段为 Marc Duclusaud 与 Grégoire Passault，项目网址仍指向 Rhoban/bam。因此更准确的说法是：**FTServo 名下的仓库在 Rhoban BAM 项目基础上提供 HD1910 扩展；本次未对厂商身份或辨识结果做法律/实验室认证。** 使用时保留 Apache-2.0 许可和版权声明。

upstreams/sources.json 将 ftservo-bam 固定到上述 SHA，将 hd1910-rl 固定到 77286a243c849e04483c7cc8ff4c5f8bae4eea16。审核使用的两个 .upstreams checkout 均为干净工作树；没有将厂商代码复制进本仓库，也没有编辑官方 XL330 或 HD1910 已有基线。

## 2. M1–M6 模型、参数与控制律

厂商 BAM 的 M1–M6 是执行器传动摩擦模型的复杂度阶梯，不是六个 PPO 算法或六个步态 Policy。模型以 kt、R、转子折算惯量、零位偏移、命令延迟和摩擦参数描述一个电机/减速器；随 M 值增加，摩擦项表达能力提高。固定提交的 [模型说明](https://github.com/ftservo/ftservo-bam/blob/4f7c0b0de3debf9c1ab254fc9654676e8aab9317/docs/theory/models.rst) 对应如下：

| 模型 | 摩擦结构 | HD1910 JSON 数值参数数目 |
|---|---|---:|
| M1 | 库仑 + 粘滞 | 7 |
| M2 | M1 + Stribeck 低速摩擦 | 10 |
| M3 | M1 + 负载相关摩擦 | 8 |
| M4 | M3 + Stribeck | 12 |
| M5 | 电机侧/外载方向分开的负载项 + Stribeck | 14 |
| M6 | M5 + 电机侧/外载侧的分段二次负载项 | 16 |

实际加载核对了六份 JSON 的字段、数值有限性和基本物理范围，再让固定版本加载器检查每个参数自身的 min/max 范围。参数文件哈希由 scripts/evaluate_bam.py 写进本地报告。M6 的关键文件值为 kt=0.5644993 Nm/A、R=2.9664762 Ω、armature=0.00182739 kg·m²、friction_base=0.01195066 Nm、friction_viscous=0.00476720 Nm/(rad/s)、command_delay=0.00097811 s。其它 M1–M5 的数值和结构不同，不能只替换一个通用“摩擦系数”。

### 2.1 电压、P 增益、模式和延迟

- BAM 的 HD1910Actuator 默认 vin=7.4 V、kp=32、error_gain=0.163、max_pwm=0.97。它计算位置误差的比例 PWM，再转为电压；电机转矩按 τ = kt·V/R − kt²·dq/R 计算，并受反电动势影响。默认 max_current=None，即 BAM 这个执行器实现没有电流限幅，亦没有温度/连续扭矩保护模型。
- 固定版本 bam/feetech/record.py 将 HD1910 的 P 增益寄存器写在地址 50 (0x32)，默认命令 kp=32、vin=7.4，并要求操作者传入 --id。它预热时写 P 增益、goal speed=0、目标位置，后续会切换 torque-enable、发送位置并读回电压/位置/速度/温度。**本轮没有运行它。** 源码没有先读取/设置工作模式寄存器的步骤；goal speed=0 注释称位置模式且不限制速度，不能据此证明待测舵机当前固件/寄存器就在对应模式。实际模式、P 增益当前值、固件版本和供电均未知。
- BAM 的 command_delay 被模型文档定义为采集台架命令链的传输滞后，可由 BAM 模拟器对已知目标序列做分数步移位。它不是自动等同于观察延迟、策略频率或真实设备端到端时延。HD1910 JSON 约 0.98–1.72 ms；provisional fork 假设 5 ms 物理步长下 3–6 步，即 15–30 ms，且明确未标定。两项来源和定义不同，不能互相覆盖。
- 本轮单舵机 A/B 为了固定共同条件，对两套模型都施加相同 4 个物理步（20 ms）目标延迟；BAM JSON command_delay 保留在报告中，但没有再叠加到 BAM 端。结果只用来展示模型/控制律敏感性，不代表测得真实时延。

### 2.2 公开代码能确认的辨识条件

固定提交的采集说明和 HD1910 all_record.py 表明，辨识设计使用直接接在舵机输出轴上的摆臂/末端砝码；每个样本必须记录砝码质量、摆臂质量与长度。HD1910 批量采集脚本的默认电压参数是 7.4 V，P 增益 sweep 为 4、8、16、32、64，默认激励包括 sin_sin、lift_and_drop、up_and_down、sin_time_square 四条轨迹，每条文档描述为 6 秒。record.py 保存目标/反馈位置、速度、负载、电压、温度等日志字段；拟合脚本按模拟与记录位置的 MAE 拟合 M1–M6，文档建议留出一个 P 增益值作验证集。

这些是审核时能从源代码和方法说明核实的采集设计，不是这六份 HD1910 JSON 的完整实验履历。固定仓库没有随参数发布对应原始日志/处理后数据、摆臂和砝码组合清单、每条曲线质量、实际电源波动、拟合 trials/optimizer、实际留出的 kp 或验证 MAE。JSON 只有模型参数和模型/actuator 名称；没有保存采集时用过的 kp/vin/设备固件/注册模式。故只能确认“参数按厂商公开 pipeline 生成”的源码路径，不能独立重现每个数值，也不能判断 M1–M6 的 HD1910 hold-out 表现。

不要为了补齐这项信息运行 all_record.py、record.py 或 fit.py：它们涉及真实舵机通信、写增益/目标、使能/运动或完整辨识流程。本轮只读源码和参数文件。

### 2.3 与 provisional PD 的区别

锁定的 [qiaosiyi HD1910 fork](https://github.com/qiaosiyi/microduck_rl_hd1910/tree/hd1910) 把已有 MicroDuck 几何与 61→14 Policy 保持下来，并使用 datasheet 约束的 provisional 输出侧 PD/DC 模型：位置刚度 0.55 Nm/rad、未标定粘滞/库仑摩擦/惯量/延迟、7.4 V 额定扭矩硬限幅 0.36284605 Nm。这些 legacy 值也不是实测 HD1910 固件传递函数。

BAM 是舵机内部位置 P 控制到电机电压/反电动势/输出转矩的近似，再叠加 M1–M6 减速器摩擦预算。两者不仅参数不同，接口和限制也不同；把 BAM 摩擦写入 MuJoCo 同时保留 provisional 摩擦/限矩，可能会重复计入摩擦或取消限矩。

## 3. 固定版本实测结果

运行 scripts/evaluate_bam.py 后的脱敏结论见 [S4/BAM 本轮记录](../records/field/s4-simulation/2026-10-15_s4-bam-evaluation.md)；原始 JSON/曲线保存在 Git 忽略的 .evidence/s4-simulation/。

### 3.1 注册大小写缺陷及最小修复方案

六份 JSON 的 actuator 均为小写 hd1910；固定版本 bam/actuators.py 只注册大写 HD1910。原版 load_model() 对 M1–M6 均重现 KeyError: 'hd1910'。同一进程中加一条别名 actuators["hd1910"] = actuators["HD1910"] 后，六个模型都能加载，reset 重复性、参数边界和单步有限性检查通过。

最小上游修复建议是将 hd1910 作为大小写兼容别名指向同一个 HD1910Actuator 工厂，并加测试覆盖：小写 JSON、显式大写 JSON、未知 actuator 名称失败、M1–M6 reset/有限单步。当前脚本只在进程内应用这个适配，没有改 vendor checkout 或 JSON，也没有声称已提交上游修复。加载器工作失败属于**实际发现的兼容性 FAIL**，所以综合报告 PARTIAL。

### 3.2 CPU 单舵机 A/B 条件与结果

脚本使用相同的单关节摆、质量（摆臂 0.03 kg + 末端 0.50 kg）、长度 0.15 m、重力、5 ms 时间步、2 秒运行、初始位置/速度和 0 → 0.25 rad → 0 目标轨迹。比较 provisional 控制器与 BAM M1–M6。BAM 侧设 vin=7.4 V、kp=32、error_gain=0.163、max_pwm=0.97，没有施加电流限制；provisional 侧保留 fork 里的额定扭矩上限。所有轨迹有限，CSV/PNG 和数值指标被自动保存。

| 后端 | 位置 RMSE (rad) | 峰值扭矩 (Nm) |
|---|---:|---:|
| provisional PD | 0.10149 | 0.13750 |
| BAM M1 | 0.07280 | 0.98725 |
| BAM M2 | 0.07283 | 0.98898 |
| BAM M3 | 0.06837 | 1.10815 |
| BAM M4 | 0.06895 | 1.12968 |
| BAM M5 | 0.06385 | 1.37234 |
| BAM M6 | 0.06372 | 1.36658 |

不能据此说 BAM 或 M6“更准确/更好”：BAM 峰值扭矩达到 provisional 0.36285 Nm 硬上限的约 2.7–3.8 倍，控制律和扭矩保护不相同；更低的 RMSE 主要说明在这个摆和控制设置下响应更强。没有 HD1910 实测轨迹作为真值，也没有任何全身行走 Policy 行为比较。

## 4. 兼容性分层与决策

| 层级 | 可以复用/需要处理的内容 |
|---|---|
| **参数可复用** | M1–M6 JSON、模型公式与 7.4 V 识别结果可用于离线研究、参数敏感性分析；使用时固定 SHA 并保留每个参数文件哈希，不把识别数据说成当前设备的标定真值。 |
| **代码需要适配** | 注册表小写别名；隔离调用 BAM 模型/reset；重构 provisional 的 torque cap、摩擦、延迟和 actor 接口；匹配 MuJoCo/MuJoCo Warp API；为 BAM 当前未提供的电流/热保护建立明确边界。 |
| **无法直接兼容** | 原版 stock loader 对 M1–M6；直接替换 HD1910 默认执行器；无对照地复用现有 checkpoint/ONNX；用 BAM 结果断言当前设备模式/真实延迟/扭矩能力；未经独立验证加进默认 GPU 训练配置。 |

固定 fork 的 `uv.lock`（x86_64 Linux）记录 mjlab==1.3.0、mujoco-warp==3.8.1、mujoco==3.10.0、warp-lang==1.12.0 和 torch==2.9.1，并锁定 CUDA 12.8 运行库；本次隔离环境中 `torch.__version__` 显示 2.9.1+cu128。ARM Linux 锁项则是 torch 2.9.1+cu129。锁文件还固定了来自 Rhoban 分支的 better-actuator-models==1.0.1（Git SHA 62bd8ce12154340be97e06f7f41a0ca8f116d967）。FTServo BAM 要求 Python>=3.12,<3.13，与本次 Python 3.12 匹配；其 mjlab extra 依赖 mjlab>=1.3,<1.4，并由 mjlab 间接提供 Torch，BAM 没有另设 Torch 版本约束。`mjlab` 和 `warp-lang` 的当前版本范围重叠，但 BAM 要求 `mujoco-warp<3.8`、`mujoco<3.8`，与 fork 锁定的 3.8.1/3.10.0 冲突。CPU JSON/MuJoCo 试验可在隔离 Python 3.12 环境做；这只能证明本轮 CPU 路径能运行，未证明 GPU 后端接口兼容。vendor BAM GPU backend 必须在独立实验分支和独立 lock 中验证，不能覆盖当前锁文件后称作原 fork 复现。

### 建议

**现在不建议进入可选 BAM GPU backend 实现。** 先保留现有 provisional 默认任务，并把本轮结果视为“注册问题已复现、CPU 模型差异可运行、真实性未知”。下一阶段若仍要推进，先在独立 lock 下完成 API/reset/延迟合同、受控电机数据与同条件曲线对照，再按 1 环境 → 64×5 GPU Smoke → Policy 行为评估逐级 Gate；这不改变当前硬件安全 Gate。未获得可审查台架数据前，M1–M6 不足以作为正式 HD1910 控制参数。

## 5. 可选命令和停止条件

以下从 MicroDuck 工作区根目录执行。先按 [S4-0](04_SIM_TRAINING.md) 固定 sources.json 中的两个上游 SHA，并检查 checkout 干净。

```bash
# 仅参数加载/注册测试：BAM 的单独 Python 3.12 环境，无 MuJoCo GPU 依赖
.upstreams/ftservo-bam/.venv/bin/python scripts/evaluate_bam.py --mode load-only --output-dir .evidence/s4-simulation/<new-run-id>-bam-load

# CPU 单关节对照：使用 HD1910 fork 已锁定的 Python 3.12/MuJoCo CPU 环境
.upstreams/hd1910-rl/.venv/bin/python scripts/evaluate_bam.py --mode compare --output-dir .evidence/s4-simulation/<new-run-id>-bam-compare
```

预期综合状态 PARTIAL，因为原版大小写加载测试应明确重现 KeyError: 'hd1910'；同时查看 report.json 中 JSON/参数/alias/reset/单步检查和 CPU A/B 是否通过。任何源 SHA 不匹配、checkout dirty、JSON 字段意外、NaN/Inf 或依赖错误都停止并保留完整异常，不继续到训练。脚本拒绝覆写非空输出目录；重试使用新的 run-id。报告、CSV 和图只写到 .evidence/，不会改上游、串口或任何舵机寄存器。

bam/feetech/record.py、bam/feetech/all_record.py、bam/fit.py 及其 SDK 调用含实机读写、P 增益写入、使能/运动或原始辨识过程；**本研究路径禁止运行这些脚本**。
