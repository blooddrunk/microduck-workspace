# S0 · 实物与断电盘点

这里保存**经人工脱敏后**的 `YYYY-MM-DD_<实验名>.md`；原始照片、日志、串口帧与可能包含私密标识的数据放在 **`.evidence/s0-hardware/<run-id>/`**（仓库根目录、被 Git 忽略）。目录中仅有本说明，**表示尚无新的实物验收记录**。

## 建议收集的证据

1. ZERO 3W V1.12/2GB/无 eMMC、HAT ASE01187-C1、FE-URT2、IMU、电池座和可调电源的**实物型号与资料来源**
2. 未上电的 C1 HAT、IMU 与线束端视图，逐点测出的 GND/VCC/DATA 通断记录；不能用照片猜脚序
3. 电池、HAT、ZERO 的供电拓扑，保险丝/断电开关/保护与未知电压的阻塞记录

**停止/验收边界**：无法确认 PCB Rev、接头极性、电池座或 IMU VCC，就维持 S3 BLOCKED。不做整机通电。

填表：[实验模板](../../TEMPLATE.md) · [分阶段证据保存与审查流程](../README.md) · [总体 Checklist](../../../CHECKLIST.md)。
