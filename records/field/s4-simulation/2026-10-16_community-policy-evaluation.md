# 2026-10-16 · 社区 HD1910 Policy 离线快速测试

类型：OFFLINE / CPU SIMULATION。结论：**继续离线仿真；不进入实机运动台架。** A/B 均未通过本轮行为筛查；C 仅作为结构对照。未连接硬件、使能舵机、写寄存器/校准、部署固件或训练 PPO；S0–S3 状态未改。

先执行 `git fetch origin`，开始时工作区干净，原分支 `codex/wslg-mujoco-renderer-note` 的 HEAD 为 `67e7609`；main 从 `899457f` 安全快进至 `9e0a5cf2efeeaa66bd2ad9f1463005d71672cc50`，随后创建 `codex/hd1910-offline-policy-check`。已阅读 README、04/05/13 与 2026-10-15 S4/BAM 记录。没有运行 update.sh、uv sync 或修改官方 XL330 模型/环境。kissqy 原 checkout 为 `02a8548…`，仅 fetch 指定提交并导出 Git 对象，不改变其 HEAD。

机器可读脱敏结果：[community-policy-results.json](2026-10-16_community-policy-results.json)。原始日志、下载原件、逐步轨迹、完整 ONNX metadata 与原始部署合同放在 Git 忽略的 `.evidence/s4-simulation/2026-10-16-community-policy/`；其中含上游训练机路径和他人校准资料，不公开。JSON 摘要按字段白名单人工复核脱敏，不复制校准数据、设备标识或绝对训练路径。

## 候选矩阵

| 候选及来源 | 训练 / 执行器依据 | ONNX / CPU | 原生 HD1910 CPU 仿真 | 已知实机证据 | 本轮结论、风险与顺序 |
|---|---|---|---|---|---|
| A [kissqy Walk](https://github.com/kissqy/Microduck-kissqy/tree/f02e875e73b88bf8ec7d5bbb34d0b461ac83b010/microduck-hd1910/firmware/policies/walk) | VelStand-Rough-Backlash，checkpoint **9599**；Manifest/contract/training_physics；原生 M6 + STS3215Actuator 实现、kp_fw=5、总质量 0.82 kg、±1° 齿隙、15–30 ms action delay | PASS：61→14 float32，ONNX checker、CPU finite / 输入变化；内置归一化 | FAIL：3×10 s，零速筛查 PASS；直行和转向跟踪 FAIL；无跌倒/限位超出 | manifest 的 deployment_verified=false；包说明不构成本机步态验收；没有对应本机的独立真机测量 | **FAIL（行为筛查）**；下一轮仿真优先 1。不能把参数文件名 hd1910_m6 当实测本机模型；权重个人非商业许可 |
| B [qiaosiyi iter 2000](https://github.com/qiaosiyi/microduck_rl_hd1910/tree/77286a243c849e04483c7cc8ff4c5f8bae4eea16/models/hd1910-walking-iter-2000) | Velocity-Flat-HD1910，**2000/计划6000**；release/verification/cpu_validation；暂定 PD k=0.55、d=0、7.4 V 额定限矩 0.36284605 Nm | PASS；另重跑原生 PT/ONNX 128 观测，最大误差 9.54e-7；199 个发布源码指纹全部匹配 | FAIL：3×10 s 无跌倒，但转速误差、关节及目标限位超出均失败 | release 明确 hardware_validation=not performed；旧固定 HOME 持位 8/8 跌倒不等于学习策略本身跌倒 | **FAIL（行为筛查）**；优先 2，先查目标越界。未标定惯量/摩擦/延迟；Apache-2.0 |
| C [XgoDuck Walk](https://github.com/LuwuDynamics/xgoduck_runtime_arduino/tree/9dc36787bc61b102c2da0f97c9c758e639e90ab8/python) | Uno Q XGODuck runtime；任务 / 迭代 / 对应训练物理未披露；run_path=local | PASS：相同数值检查；原生 Policy.load/build_obs/infer 纯数学路径 PASS | **NOT_RUN**：此固定 runtime 未提供可匹配训练模型/任务的 HD1910 原生 MuJoCo 路径 | README 描述 Uno Q 项目；不构成 MicroDuck HD1910 真机策略证据 | **PASS（仅结构与CPU可运行性）**；优先 3，仅对照。许可未找到；runtime HOME 与 ONNX metadata 不一致 |

这里的 PASS/FAIL 是表中指定检查的状态；没有任何模型获得稳定连续行走或实机验收 PASS。三个 Policy 都能加载并输出 finite，这没有改变 A/B 的行为 FAIL，也没有补齐 C 的仿真。

## 固定产物与许可

| 模型 | 固定 commit | 文件路径 | Bytes | ONNX SHA256 | 许可 |
|---|---|---|---:|---|---|
| A | f02e875e73b88bf8ec7d5bbb34d0b461ac83b010 | microduck-hd1910/firmware/policies/walk/policy.onnx | 795454 | 1cbf8730eadd75a5704332c9f3c10f60bfa9412135b907831c9dbd731ce1795f | policies/LICENSE：Personal Non-Commercial v1.0；不覆盖所有第三方权利 |
| B | 77286a243c849e04483c7cc8ff4c5f8bae4eea16 | models/hd1910-walking-iter-2000/policy.onnx | 794100 | 40f7af33cc67218a9b5dc8c8daa4dc0c52260dfcbb76d8a71f66335cd254dec2 | 发布包 Apache-2.0；几何资产另行适用上游许可 |
| C | 9dc36787bc61b102c2da0f97c9c758e639e90ab8 | python/xgoduck_walk.onnx | 793706 | 5727b909d5ea1a0f9ff63bf4cea9707339dea6a522374c7a120da633605b923f | 固定 Git tree 未找到 LICENSE / COPYING / NOTICE；不可推定授权 |

C 的 master 经 ls-remote 固定后再下载；A/B 的 ONNX hash 另与发布 Manifest/release 比对。没有公开或再分发任何权重。A 原生引擎单独导出官方 `8d0db74916a4f833d1d9b95d6a1d7f4d13b9d5ec` + kissqy 指定 SHA 的 training 目录，并记录 301 个文件 hash；重建后核对 M6 文件 hash、kp、电压/掉压范围、延迟、HOME、动作倍率和无滤波约定。M6 hash 为 `ef2d51adfb1cc0831b9b02ca19aa9176fceecdf725148d084378d7d9a64afceb`。这不是上一轮 FTServo 仓库的 M6，也没有混用其参数。

B 的 release.code_base_commit 对应 dirty 导出时基线，单靠该基线不充分；本次固定完整发布 commit，核对 accompanying source_hashes.json 的 **199/199** 文件，避免将 dirty 基线误当完整训练来源。

A 保存的训练适配器标识为 R1.5.9，而固定发布源码中的适配器标识为 R1.5.26-no-ema；本次核对并重建的是上述关键部署物理合同。没有逐字段证明完整历史训练配置、随机化分布和原训练环境一致，不能把回放说成完整历史训练复现。

## 语义合同差异

A/B 的策略关节顺序相同：左腿 hip_yaw/hip_roll/hip_pitch/knee/ankle，neck_pitch/head_pitch/head_yaw/head_roll，右腿同序；嘴部不参与 14D 动作。HOME（rad）：

`[0,-.0873,-.4579,-.0049,.453,.3491,.3491,0,0,0,.0873,.4579,.0049,-.453]`

61D 布局为角速度 `[0:3]`、机体系投影重力 `[3:6]`、相对 HOME 关节位置 `[6:20]`、关节速度 `[20:34]`、raw previous action `[34:48]`、twist `[48:51]`、head `[51:55]`、body `[55:61]`。三份图均实际包含输入 Sub(mean) → Div(正的 61D 标准差) → MLP，运行时不再归一化。测试用直立重力及小幅倾斜/角速度/关节位置/速度/previous-action、0.1 m/s 前进、0.2 rad/s 转向，逐项记录输出变化；不把零向量当完整合理观测。

| 项目 | A | B | C |
|---|---|---|---|
| HOME / 顺序 | 上述 HOME / contract 顺序 | 同 A；metadata 只有三位小数，原生脚本使用完整 HOME | 逻辑顺序同类；runtime hip/ankle=±23°、knee=0；ONNX metadata 却约±20°、knee=±.005 rad，存在来源冲突 |
| previous action / scale | 原始输出；HOME+1×action | 同 A | 原始输出；1×action；嘴部单独 |
| 动作滤波 | 训练与导出均禁用 EMA，alpha=1 直通 | 未加 EMA | runtime `.45×previous + .55×current`；[5:10] 头部切片还包含右 hip_yaw，当前 alpha 相同掩盖该分组差异 |
| 指令 | constant twist + head4 + body6 | 相同布局的速度任务 | twist + head4；body6 强制置零 |
| 频率 | 50 Hz / 200 Hz 物理 | 50 Hz / 200 Hz 物理 | 50 Hz host / 100 Hz MCU；无对应原生仿真频率证据 |
| 执行器 | M6 kt=.62376、R=4.91019、kp_fw=5、无电流/热模型；训练电压7.4–8 V、掉压、齿隙/摩擦随机化 | provisional 输出侧 PD、额定限矩；native 回放固定7.4 V、4物理步延迟，无DR | 未固定与权重匹配的训练执行器；不能从 runtime 推导 |

A 的参数 JSON 自称 actuator=sts3215、原生实现 STS3215Actuator；名称与 HD1910 物理真实性仍需台架数据确认。A/B 虽尺寸和 HOME 相同，也没有建立训练执行器语义等价关系。C 与 A/B 不能直接互换。

## 实际回放与判断标准

使用已有隔离 HD1910 fork venv 作为依赖运行时，显式 CPU；A 从私有归档加载自己的 engine/adapter，B 使用自己的 load_cpu_model/PolicyInference。没有安装 CUDA 或大型训练包；已有 venv 的 Torch 含 CUDA wheel 不代表使用了 GPU。纯 ONNX 使用另建轻量 venv：Python 3.12.14、NumPy 2.4.2、ONNX 1.22.0、ORT 1.24.4；native 为 NumPy 2.4.1、MuJoCo 3.10.0、mjlab 1.3.0、Warp 1.12.0、mujoco-warp 3.8.1、Torch 2.9.1、ORT 1.24.4。完整 freeze 留在私有证据目录。

每场景请求10秒、50 Hz 策略，独立重置直立 HOME、零速度；head/body 指令零。A 保留原生 Rough 地形与启动随机化、seed=42，关闭评估推扰、不自动 reset，策略输入覆盖为固定指令。B 使用原生平地、固定电压/延迟且无DR。**不是同一物理基准，不以两表的误差差值评价哪个执行器更真实。**

预设快速筛查：倾角>55°或 root 高度<0.06 m 记跌倒并停止（A 高度相对 terrain origin）；NaN/Inf、原生 termination/timeout 停止；关节或目标越界>0.01 rad、全窗口 vx RMSE>0.1 m/s、yaw RMSE>0.2 rad/s 记FAIL。阈值是快速排错约定，不是已验证的步态验收规范。越界仅离线记录，不向实机发送。B 每物理步检查跌倒，A 每策略步采样；A 没有导出同等的逐步 MuJoCo warning 计数，明确 NOT_RUN，不填0。两者均记录有限性/终止/跟踪/限位和逐步推理耗时。

| A 场景 | 完成 | 最大倾角 | vx RMSE m/s | yaw RMSE rad/s | 关节/目标越界 | 状态 |
|---|---:|---:|---:|---:|---|---|
| 零速 | 10 s | 2.924° | .00592 | .06747 | 无 | PASS（筛查） |
| 直行 .1 m/s | 10 s | 6.464° | .09095 | .53057 | 无 | FAIL |
| 转向 .2 rad/s | 10 s | 2.308° | .00555 | .20713 | 无 | FAIL |

| B 场景 | 完成 | 最大倾角 | vx RMSE m/s | yaw RMSE rad/s | 最大关节/目标越界 rad | 状态 |
|---|---:|---:|---:|---:|---:|---|
| 零速 | 10 s | 2.010° | .03466 | .45309 | .05530 / 5.17565 | FAIL |
| 直行 .1 m/s | 10 s | 1.985° | .08141 | .46187 | .06162 / 5.07136 | FAIL |
| 转向 .2 rad/s | 10 s | 1.946° | .03443 | .43429 | .06858 / 5.15883 | FAIL |

B 零速最坏目标越界发生于 left_hip_yaw；目标超范围与实际关节超范围是两项指标。不能把受限机械状态当输出动作安全。全窗口未排除启动瞬态，也没有只挑最佳片段。A/B 均没有触发55°跌倒阈值；这不是稳定站立/持续行走认证。PT/ONNX 最大误差9.54e-7；CPU推理耗时以JSON实测 median/p95 为准，受主机负载影响，不是 ZERO 3W 实时性能证据。

## 可复现命令

以下是本轮执行路径，重跑请更换 `E` 为新 run-id，输出脚本拒绝覆盖非空目录。native 依赖预先存在，不运行 uv sync；缺少环境时记 NOT_RUN，不为回放下载 CUDA 栈。

```bash
E=.evidence/s4-simulation/2026-10-16-community-policy
python3 scripts/evaluate_community_policies.py prepare --output "$E/pinned-downloads"
uv venv --python 3.12 "$E/cpu-venv"
uv pip install --python "$E/cpu-venv/bin/python" numpy==2.4.2 onnx==1.22.0 onnxruntime==1.24.4
"$E/cpu-venv/bin/python" scripts/evaluate_community_policies.py check \
  --sources "$E/pinned-downloads" --output "$E/onnx-verified"
# 本轮已 fetch A 指定 SHA；official-rl 本地 object DB 已有指定引擎 commit。
# 如果缺少对象：仅 git fetch origin <对应commit>，不要 checkout 或更新已有环境。
python3 scripts/evaluate_community_policies.py prepare-kissqy-native --output "$E/native-pinned"
.upstreams/hd1910-rl/.venv/bin/python scripts/replay_kissqy_policy.py \
  --native-sources "$E/native-pinned" --sources "$E/pinned-downloads" --output "$E/kissqy-native-final"
.upstreams/hd1910-rl/.venv/bin/python scripts/evaluate_community_policies.py replay-qiaosiyi \
  --sources "$E/pinned-downloads" --output "$E/qiaosiyi-native-final"
"$E/cpu-venv/bin/python" -m unittest discover -s tests -v
python3 scripts/verify_workspace.py
```

A/B 回放的退出码1表示行为 FAIL，必须读 report.json，不能用进程正常退出代替验收。A 原生环境确实使用 CPU Warp/MuJoCo，首次编译约数分钟；无 viewer、无GPU任务。额外执行 A 原生 test_training_onnx.py（2项通过）；它使用小型夹具，不能冒充实际权重的动力学测试。B 将 verify.py/policy.onnx/model_2000.pt 链接到私有 `qiaosiyi-verification-copy/`，用 `--model-dir` 指向该目录重跑128观测，写结果至私有目录，不写回 upstream。C 仅导入 policy/rl_core，不导入 main/controller，不打开 Bridge/串口。

验证：隔离 CPU 环境运行全部 **62 个 unittest PASS**（包括新增源文件篡改、常量输出误判、错误形状、内置归一化4项）；语法/CLI、workspace 文档链接检查 PASS。A/B 最终脚本各复跑3×10秒，重复得到同样的行为指标及FAIL结论；延迟随主机负载变化。完整自动验收命令为 `python3 scripts/run_checks.py --output "$E/workspace-acceptance"`，日志保存在同一私有目录；该命令默认宿主没有 ONNX 依赖时会跳过4项，因此以轻量 CPU venv 中实际运行的62项结果为准。

## 下一轮建议、人工事项与停止条件

1. **值得继续 A 的离线仿真**：增加多 seed、较长时窗、启动/稳态分段、±转向/低速轨迹、接触/步态与侧向速度指标，并核对 native warning；保留当前合同和单独后端。转向误差 .207 距本轮 .2 阈值很近，也应原样报告FAIL，不事后放宽阈值。
2. **B 先排错再扩展**：检查 left_hip_yaw 大目标、动作/默认姿态/训练归一化统计和原生部署目标限幅约定；不要随手加clip/EMA把问题隐藏。保持旧固定HOME持位失败与学习策略回放分开。
3. **C 仅保留对照**：先请作者提供权重许可、任务/迭代/训练物理和 HOME 冲突解释，再考虑仿真适配；禁止称其为 MicroDuck HD1910 真机兼容策略。可选 SitStand 本轮 NOT_RUN，没有拿速度指令去替代其姿态 flag。
4. **现在不转实机运动台架**。不可自动完成的人工工作：本机电源/极性/防反灌与急停验收；逐舵机型号、ID、方向、机械/编码器零位、实际关节限位；IMU 安装/单位/静态姿态；作者许可及可审查物理标定证据。继续只读 S0–S3 记录须按原有流程另做，不由本轮推进硬件状态。
5. 后续任何环节出现 source/hash/合同不符、缺许可/模型来源、NaN/Inf、异常 termination、跌倒、目标越界、供电/温度/急停证据缺失，停止升级测试等级并保存原始证据。实机运动需在这些问题解决及现有硬件 Gate 完成后另行授权；本轮不执行。
