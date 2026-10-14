# S4 · HD1910 仿真与训练

这里保存**经人工脱敏后**的 `YYYY-MM-DD_<实验名>.md`；原始照片、日志、串口帧与可能包含私密标识的数据放在 **`.evidence/s4-simulation/<run-id>/`**（仓库根目录、被 Git 忽略）。目录中仅有本说明，**表示尚无新的实物验收记录**。

## 建议收集的证据

1. 实际使用的官方/HD1910 分支 commit、依赖锁、任务与模型 hash
2. CPU 回放环境、真实屏幕/日志；有 GPU 后的 64 env×5 iteration smoke 与 checkpoint、数值有限性
3. ONNX [1,61]→[1,14] 及关节顺序、HOME、action scale、normalizer 语义；实机兼容性仍另验

**停止/验收边界**：训练/仿真 PASS 不代表 HD1910 真机上电、IMU、安全控制和行走 PASS。

填表：[实验模板](../../TEMPLATE.md) · [分阶段证据保存与审查流程](../README.md) · [总体 Checklist](../../../CHECKLIST.md)。
