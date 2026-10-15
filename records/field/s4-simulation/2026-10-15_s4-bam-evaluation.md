# 2026-10-15 · S4 CPU 仿真与 FTServo BAM 评估

> 类型：SIMULATION / DOCUMENT_REVIEW。软件检查在隔离上游环境中执行；没有连接舵机、写寄存器、使能或运行标定。没有运行 PPO 训练，也没有用本轮数值结果修改任何硬件 Gate。

## 来源和环境

- 本仓库审查基线：main SHA 899457fb6450f8704371595967f14e47f53e1bc7；实现位于独立分支 codex/s4-bam-evaluation。
- qiaosiyi HD1910 fork：77286a243c849e04483c7cc8ff4c5f8bae4eea16；uv.lock SHA256 2eeeb680025baa737e7ccf3a87da3695a9d49b228de0bb60d8af0c022ab5f1aa。
- FTServo BAM：4f7c0b0de3debf9c1ab254fc9654676e8aab9317。2026-10-15 对 Gitee 和 GitHub 的 refs/heads/main 执行 git ls-remote 均返回同一 SHA。固定提交 LICENSE 是 Apache-2.0。GitHub commit author/committer 显示 ftservo；发行元数据仍指向 Rhoban/bam。相同 SHA 证明远端公布了同一 Git 提交，不证明账号法律身份或硬件实验室认证。
- 宿主：Linux；Python 3.14.4；uv 0.12.18。锁定 fork 运行环境：Python 3.12.14、mjlab 1.3.0、MuJoCo 3.10.0、MuJoCo Warp 3.8.1、Warp 1.12.0、Torch 2.9.1+cu128、ONNX Runtime 1.24.4。
- CUDA：BLOCKED。nvidia-smi 不存在；torch.version.cuda 为 12.8，但 torch.cuda.is_available() 为 false、device_count=0。含 CUDA wheel 不能证明存在 GPU。
- GUI：PARTIAL。DISPLAY、Wayland 和 X11 socket 存在；本轮没有打开 viewer 窗口，因此渲染和键盘控制仍未验证。
- 私有原始报告与曲线：.evidence/s4-simulation/2026-10-15-preflight-3/、2026-10-15-audit-1/、2026-10-15-bam-load-final/、2026-10-15-bam-compare-final/。这些目录已被 Git 忽略。

## 实际验证和结果

| 检查 | 命令 / 证据 | 状态与解释 |
|---|---|---|
| BAM M1–M6 JSON、加载器、reset、单步 | 隔离 Python 3.12：.upstreams/ftservo-bam/.venv/bin/python scripts/evaluate_bam.py --mode load-only --output-dir .evidence/s4-simulation/2026-10-15-bam-load-final | PARTIAL。六份 JSON 字段/有限值/物理范围和 loader 参数范围 PASS；原版 M1–M6 均因 KeyError: 'hd1910' FAIL；进程内小写 alias 后六者都能 reset、重复单步有限。没有修改 vendor checkout 或 JSON。 |
| BAM / provisional 单舵机 CPU 对比 | .upstreams/hd1910-rl/.venv/bin/python scripts/evaluate_bam.py --mode compare --output-dir .evidence/s4-simulation/2026-10-15-bam-compare-final | PARTIAL：同一单摆/5 ms/2 s/共享 20 ms 延迟的 7 条曲线均有限；综合状态保留 loader FAIL。RMSE（rad）：provisional 0.10149、M1 0.07280、M2 0.07283、M3 0.06837、M4 0.06895、M5 0.06385、M6 0.06372。峰值扭矩（Nm）：provisional 0.13750、M1 0.98725、M2 0.98898、M3 1.10815、M4 1.12968、M5 1.37234、M6 1.36658。 |
| ONNX 快照 SHA 和契约 | fork models/hd1910-walking-iter-2000/SHA256SUMS；自动预检报告 | PASS：13 个文件的校验通过；ONNX 为 float32 1 输入/1 输出，[1,61]→[1,14]；零向量 CPU 推理有限。快照含发布的 model_2000.pt；这不是本轮新训练产物。 |
| ONNX 物理 rollout 与站姿检查 | uv run --locked scripts/validate_hd1910.py --onnx models/hd1910-walking-iter-2000/policy.onnx --output <private-cpu-validation.json> | PARTIAL：100 Policy 步/400 物理步/2 秒 rollout 数值有限；8/8 静止姿态稳定性试验超过 82° 倾斜并跌倒，行为子检查 FAIL。零速度 rollout 不能替代速度跟踪、GUI 操作或行走评估。 |
| 任务注册和 CUDA/GUI 预检 | python3 scripts/check_s4_environment.py --output-dir .evidence/s4-simulation/2026-10-15-preflight-final | PARTIAL：两个固定 SHA checkout 干净，任务注册 PASS，ONNX CPU contract/inference PASS，快照校验 PASS；CUDA/GPU Smoke BLOCKED；GUI 只有环境线索。 |
| Python 语法、CLI 和单元测试 | python3 -m py_compile scripts/evaluate_bam.py scripts/check_s4_environment.py tests/test_bam_evaluation.py tests/test_s4_preflight.py；两个脚本分别运行 --help；python3 -m unittest discover -s tests -v | PASS：语法与 --help 成功；58 个 unittest 全部通过。测试夹具中预期 FAIL/BLOCKED 文本不是套件失败。 |
| 仓库全套离线验收 | python3 scripts/run_checks.py --output .evidence/s4-simulation/2026-10-15-final-checks-4 | PASS：工作区/链接检查、58 个单元测试、上游状态查询、模拟舵机夹具及预期 BLOCKED 夹具均符合预期；9 个上游有 2 个非本任务来源可更新、0 个查询错误，BAM 与 HD1910 固定来源仍为 CURRENT。该命令不代表 GPU、行为或硬件验收。 |

### BAM A/B 条件和解释

单关节模型：0.50 kg 末端载荷、0.03 kg 摆臂、0.15 m 长度、标准重力、5 ms timestep、2 秒；位置命令由 0 rad 在 0.10 秒切到 0.25 rad，0.80 秒回零；两侧相同 20 ms 目标延迟。BAM 为 7.4 V、P 增益 32、error_gain 0.163、PWM 上限 0.97、未设置电流限制；provisional 使用 fork 的 0.36284605 Nm 额定扭矩限幅。

不能把更低 RMSE 解读为厂商 BAM 更准确：BAM 在这次试验的峰值扭矩约为 provisional 硬上限的 2.7–3.8 倍，控制律和限幅不同；没有实物 HD1910 轨迹作真值，也没有比较全身 Policy。

### 厂商公开的辨识设计与证据缺口

固定源码描述摆臂/砝码 pendulum，记录砝码质量、摆臂质量和长度；HD1910 all_record 默认 P 增益为 4/8/16/32/64、电压参数 7.4 V、4 条轨迹（sin_sin、lift_and_drop、up_and_down、sin_time_square），每条约 6 秒。拟合代码按位置 MAE 拟合参数，文档提供按 kp 留出验证的入口。当前固定仓库只发布六份 JSON，没有这些 HD1910 原始/处理后日志、负载组合表、实际电源波动、固件/模式、实际验证集或各模型 hold-out MAE；因此实际采用的辨识样本组合与每个 JSON 的误差水平仍未知。采集/拟合代码含实机访问，本轮未运行。

## S4 阶段状态

- S4-0：PARTIAL。固定来源、依赖、task ID、ONNX 契约和本地 CUDA 状态有自动证据；缺少真实 GPU 和 GUI 渲染证据。
- S4-1：SKIP。本轮未操作被忽略目录中的官方 XL330 baseline。
- S4-2：PARTIAL。SHA/数值 CPU rollout PASS；站姿验证器 FAIL；可视化窗口和控制输入未执行。
- S4-3：BLOCKED。无 NVIDIA GPU，本轮没有启动训练。
- S4-4：SKIP。依赖 S4-3。
- S4-5：SKIP。没有新训练 checkpoint，未做用户 Policy 的 play/export。
- S4-6：PARTIAL。stock loader 缺陷真实复现；隔离 alias 和 CPU 曲线 PASS；没有 GPU backend，也没有实测准确度结论。

## BAM 决策

可复用的是固定 SHA 的参数文件、模型公式和离线敏感性输入；需要适配的是大小写注册、MuJoCo/MuJoCo Warp API、reset/延迟/限流接口；不能直接替换的是 provisional 默认执行器和现有 checkpoint/ONNX。FTServo BAM 的 mjlab extra 要求 mujoco-warp<3.8 与 mujoco<3.8，当前 fork 锁定的是 3.8.1 与 3.10.0。**暂不建议下一阶段实现 BAM GPU backend**，先要有独立 lock/API 兼容证据与可审查的对照轨迹。

## 用户下一步最短路径

从工作区根目录先运行以下命令。本机预期预检为 PARTIAL：固定来源、task ID、ONNX 与已发布快照 PASS；CUDA/GPU Smoke BLOCKED、训练 checkpoint NOT_EXECUTED。

~~~bash
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE="$PWD/.evidence/s4-simulation/$RUN_ID"
mkdir -p "$EVIDENCE"
python3 scripts/check_s4_environment.py --output-dir "$EVIDENCE/preflight"

cd .upstreams/hd1910-rl
(cd models/hd1910-walking-iter-2000 && sha256sum -c SHA256SUMS)
MUJOCO_GL=egl uv run --locked scripts/validate_hd1910.py \
  --onnx models/hd1910-walking-iter-2000/policy.onnx \
  --output "$EVIDENCE/cpu-validation.json"
~~~

预期快照哈希全部 PASS；CPU validator 进程成功并产出 JSON，但报告中已知 8/8 静止姿态失败，不能把退出码 0 当行为 PASS。如 Linux GUI 可用，再按 [S4 教程](../../../docs/04_SIM_TRAINING.md) 执行 GLFW 回放。只有 `nvidia-smi` 与 Torch CUDA 都确认真实 GPU、任务注册检查通过，并满足教程的 Smoke 日志/有限值/新 checkpoint SHA 条件，才进入 S4-4。详见 [S4 教程](../../../docs/04_SIM_TRAINING.md) 与 [BAM 评估](../../../docs/13_FTSERVO_BAM_RESEARCH.md)。
