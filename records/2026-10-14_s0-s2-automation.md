# 2026-10-14 · S0–S2 自动化准备

本轮起始 commit：`df3a11419a1b98cc68acd06ca507c25543faf8fc`。按指定顺序 fetch、checkout main、pull --ff-only、status、rev-parse；工作区干净，快进一条文档基线 commit，保留原有忽略的仿真环境。最新 README/Roadmap/Checklist/docs 00–05、scripts、来源锁和 CI 已阅读；未运行旧 update.sh 或改变依赖。

## 范围与阶段

完成只读诊断、台账静态检查、私有证据包与桌面教程。S0 仍进行中，S1/S2 未实机验收；S3–S9 未执行。本轮没有寄存器写入、设备树/串口配置、服务启停、接线或运动。

原 S2 中的全总线/IMU 最终验收明确归属 S3/S5；ID 写入和主动标定需后续真实硬件许可与参数确认。未提供 HAT/IMU Rev、原理图和电源实测，因此未知引脚保持 BLOCKED，无最终 pin-to-pin 表。

## 七源变更审查

实际运行 `python3 scripts/sync_upstreams.py check`，7/7 远端分支 HEAD 与锁一致，0 更新、0 查询错误。下面的完整 SHA 保留在 sources.json；不升级、不移植，变更摘要均为“相对本轮起始锁无漂移”。

| 来源 | 分支 / 固定 SHA | 兼容性判断与仍需核对 |
|---|---|---|
| pollen-robotics/microduck | main / `95a7e91725b4c079a6ee6ba0a018c8b08e2a7e46` | 无新差异；保留官方 Dynamixel 基线判断，飞特协议与 IMU 适配未由本轮认证 |
| pollen-robotics/microduck_rl | develop / `b02fdea4902c2b93b7d34a83a6f05da4ececb7d3` | 无新差异；XL330 训练不能认证 HD1910 参数 |
| pollen-robotics/elec_RPI_Robot_HAT | main / `4478fdfb0d6c6766110776bfed44316884e94e52` | 无新差异；实物 Rev/电源/半双工与针脚仍需核对 |
| fanhao375/microduck-replica | master / `5397eb14d356fa618b294a25cebd4bb0ec59c162` | 无新差异；保留供电掉压、I²C IMU/补丁、增益生效风险，本机未测 |
| kissqy/Microduck-kissqy | main / `7a52d297a9adfe6d2315481953dc64060252d142` | 无新差异；镜像、HAT、飞特 IMU 固件须成套，启动上力行为需独立确认 |
| qiaosiyi/microduck_rl_hd1910 | hd1910 / `77286a243c849e04483c7cc8ff4c5f8bae4eea16` | 无新差异；执行器/训练 HOME/动作接口仍是待实物核对的合同 |
| LuwuDynamics/xgoduck_rl | main / `326d77a1122870bdefa2c36403937502c958e69c` | 无新差异；M6 参数/固件/测量条件不自动适用于本机 |

以上兼容性判断沿用现有审查边界；此次 HEAD 比对未重新认证所有源码或第三方硬件结论。

## 验收结果

在 Linux x86_64 开发宿主实际执行 `python3 scripts/run_checks.py --output .evidence/acceptance-s0-s2-release`，开始时间 `2026-10-14T03:48:17.708330+00:00`（UTC；台北 UTC+8）。源码为上述起始 commit + 未提交改动；精确 scripts/templates 文件 SHA256 保留在 [公开摘要](automation-evidence-2026-10-14/summary.txt)，不能把基线 commit 误称为最终代码。

| 检查与实际命令 | 结果 | 原始命令输出（经过人工敏感内容检查） |
|---|---|---|
| `python3 scripts/verify_workspace.py` | PASS：17 必要文件、内部链接、7 SHA 格式 | [raw 00](automation-evidence-2026-10-14/raw-00.txt) |
| `python3 -m unittest discover -s tests -v` | PASS：25 tests | [raw 01](automation-evidence-2026-10-14/raw-01.txt) |
| `python3 scripts/sync_upstreams.py check` | PASS：7 current / 0 update / 0 error | [raw 02](automation-evidence-2026-10-14/raw-02.txt) |
| `validate_servos.py` + simulated JSON/mapping | 静态 PASS、exit 0；硬件未验证 | [raw 03](automation-evidence-2026-10-14/raw-03.txt) |
| `validate_servos.py` + 空白 CSV/mapping | BLOCKED、exit 2（预期；验收断言 PASS） | [raw 04](automation-evidence-2026-10-14/raw-04.txt) |

测试日志里的合成 FAIL/BLOCKED 行来自故意失败测试，整套 unittest 返回 0，不代表真实设备异常。失败测试覆盖重复/缺失字段/ID、映射冲突、CSV 宽度/重复列、JSON 损坏、非有限数值、HOME 越限、供电/温度声明冲突、寄存器记录损坏、权限不足、命令缺失/超时、证据防覆盖与权限/hash。

还实际执行 `python3 scripts/diagnose_radxa.py --output .evidence/host-only-diagnostic --robotd`：exit 2 / BLOCKED。这是 **x86_64 宿主** 的采集演练，板型节点缺失、日志权限/可见性受限、robotd 缺失，UART/I²C 节点缺失/占用可见性不足；不算 Radxa 验收。含主机标识的原始包仅本地保存。

**受限项**：没有 Radxa/HD1910/万用表现场访问与测量证据，H0/H1/H2 为 BLOCKED；宿主没有 `nvidia-smi` 命令或 `/dev/nvidia*` 设备节点，CUDA 环境未可用，GPU smoke/长训 NOT_EXECUTED；CPU 仿真亦未重跑（本轮范围 S0–S2）。网络本轮可用，上游查询已实际完成。CI 增加 templates 路径触发及两个 CLI 验收；远端 CI 结果在最终交付中按实际状态说明。

原始证据保留开发电脑 `.evidence/`；不自动提交硬件诊断、原始标识或个人台账。原始文件与摘要分别存储，摘要含命令、UTC 时间、source commit/dirty、脚本文件 hash、原始文件 hash 与范围。

## 桌面下一步与下轮最小任务

按 [自动化教程](../docs/06_S0_S2_AUTOMATION.md) 的 H0/H1/H2 六要素卡执行：断电贴标签/照片 → 取得准确 HAT/IMU/适配器资料 → 完成断电测点核对 → Radxa 独立 5V 启动采集 → 单舵机只读。每步失败保持/恢复断电，保存失败，不越级写入或运动。

下轮最小输入：实物盘点与版本来源、独立主板诊断和第一只 HD1910 原始只读信息；据此审查所选运行时兼容分支及下一只读取步骤，不提前推进整机供电。
