# 05 · 来源可信度、上游同步与验收证据

## 从哪些仓库学习，各负责什么？

| 层次 | 上游 | 应当复用的部分 | 不可直接推导 |
|---|---|---|---|
| 官方 | [pollen-robotics/microduck](https://github.com/pollen-robotics/microduck) | Rust 运行时架构、官方 ZERO 3W provisioning、观测合同 | 对 HD1910 通信协议与接线即插即用 |
| 官方 | [pollen-robotics/microduck_rl](https://github.com/pollen-robotics/microduck_rl) | mjlab + PPO、61→14、BAM XL330 基线 | 不重新建模就可替代飞特 |
| 官方 | [pollen-robotics/elec_RPI_Robot_HAT](https://github.com/pollen-robotics/elec_RPI_Robot_HAT) | 官方 HAT 工程/原理图 | 与不同私制 HAT 的 PCB Rev 完全一致 |
| 社区实机 | [fanhao375/microduck-replica](https://github.com/fanhao375/microduck-replica) | 实测电气问题、IMU 校准、供电掉压、HD1910 现场反馈 | 其 BNO085/开发板/补丁与你的固件自动兼容 |
| 社区集成 | [kissqy/Microduck-kissqy](https://github.com/kissqy/Microduck-kissqy) | HD1910 runtime、HAT+IMU、镜像、中控、硬件时间线 | 公开系统镜像对任意 HAT/IMU/电池安全适配 |
| 社区训练 | [qiaosiyi/microduck_rl_hd1910](https://github.com/qiaosiyi/microduck_rl_hd1910/tree/hd1910) | HD1910 任务、CPU 回放、训练命令、ONNX 快照 | 暂定执行器参数已完成真机标定/步态无风险 |
| 社区模型 | [LuwuDynamics/xgoduck_rl](https://github.com/LuwuDynamics/xgoduck_rl) | 1910 M6 参数研究、物理模型与对比工具 | 不经参数、固件与实验条件比对就可复制 |

各引用的**固定 commit** 在 [sources.json](../upstreams/sources.json)：初始锁于 2026-10-14，最近一次同步见 [2026-10-15 记录](../records/2026-10-15_upstream-sync.md)。上游可能后续改写 README、模型、固件与安全提示；读最新资料时必须记录日期/commit。资料冲突时：**实物铭牌+版本匹配的原理图/厂商手册 > 有测量条件的实机记录 > 仓库声称 > 推测**。社区结论仅对它的样机配置成立。

## 同步策略：跟踪变更，不自动运行陌生代码

环境要求：Python 3.10+（只用标准库）、Git。**在本仓库根目录**：

```bash
# 1. 检查版本漂移，不下载源码、不修改当前仓库
python3 scripts/sync_upstreams.py check

# 2. 只下载需要的 fork 到 .upstreams/（被 .gitignore 排除）
python3 scripts/sync_upstreams.py fetch --name hd1910-rl

# 3. 同步完成并完成变更审查后，显式更新 sources.json 的固定 SHA
python3 scripts/sync_upstreams.py fetch --name hd1910-rl --update-lock

# 4. 下载其余来源时明确逐个操作，避免拉取巨大二进制仓库
python3 scripts/sync_upstreams.py fetch --name kissqy-runtime
```

`check` 使用 `git ls-remote` 对比 pinned SHA 与远程分支 HEAD，**有更新时会提示，不自动覆盖**。`fetch` 在 `.upstreams/<name>/` 建立独立浅克隆，checkout 为 detached HEAD，并打印原锁版本/新版本；不会运行上游安装脚本，也不会覆盖本项目的 `microduck/` 或 `microduck_rl/`。`--update-lock` 会修改本仓库的锁文件，**只在审核改动与兼容性后 commit**。更新 pinned SHA 不代表自动移植任何源码。

原有 `./update.sh` 专门同步老的**两个官方本地克隆及 HF Policy**，它会改变当前 CPU 仿真环境，不等于这里的社区 fork 快照。避免两套脚本同时执行；更新官方后先运行旧仿真与依赖回归，记录新的 SHA，失败时回退到之前记录的版本。

### 上游变更审核清单

1. 用 `check` 查看哪些源更新，获取 changelog、commit diff、主要改动路径/许可证。
2. 判断是固件/IMU/总线/电源的变化、训练代码/数据合同的变化，还是文档变更；硬件风险优先。
3. 自动运行静态测试、单元/协议模拟、ONNX 契约与 CPU 回放（取决于变更类型）；禁止以“未执行”冒充“通过”。
4. 若出现硬件 Rev/线序/原理图变动，把现有 S3 的接线状态标回 **未验证**，直到该实物重新核对。
5. commit 更新后的 SHA、测试日志摘要与 `CHECKLIST.md` 状态；风险未解决则不接纳移植。

## 每阶段都必须形成的证据

**规范化目录**：[records/field/](../records/field/README.md) 含 S0/S1/S2/S3/S4/S5–S9 的脱敏摘要分类与 Codex 交接流程；完整原始日志/截图/私有台账保留到仓库根目录 `.evidence/`、`local/`（被 Git 忽略）。**该仓库是 Public**，不可自动公开原始设备数据或机密标识。只有已提交的脱敏记录或明确提供的附件，远程 Agent 才能用于证据复核。


用 [records/TEMPLATE.md](../records/TEMPLATE.md) 复制成按日期的实验记录，保存：目标与设备 Rev、软件 SHA、命令、关键参数（电压、电流、舵机 ID、IMU 偏置）、原始输出/照片/视频位置、预期/实际结果、失败如何回滚、未解决问题。可用 `python3 scripts/verify_workspace.py` 自动审查文档内部链接和上游 SHA 结构。

**自动化能做**：仓库文档链接/版本锁校验、软件测试、串口日志和 CSV 分析、动作/观测合同检查、训练日志与模型回放。**自动化做不到**：确定未知实物三针线序、验证真实接插件极性、触摸检查过热、确保急停已物理安装、判断夹伤风险。因此这些项目未提供测量证据时必须 STOP，不以“待人工证据补充”作为无解释的完成状态。

S0–S2 的 2026-10-14 上游检查结果与兼容性判断见 [执行记录](../records/2026-10-14_s0-s2-automation.md)；2026-10-15 的漂移审查与版本锁更新见 [同步记录](../records/2026-10-15_upstream-sync.md)。远端一致只证明 SHA 匹配，不认证电气/固件兼容。`git` 网络命令有 45 秒超时，失败不改锁。

2026-10-14 新增第八来源：[QinmoTech/IMU-DXL](https://gitee.com/QinmoTech/IMU-DXL/tree/4644a9d19e07ac47f2c145c5e064c96683a5450b)，固定v1.2协议；当日其余七源锁未变。sync工具默认GitHub，显式host只允许github.com/gitee.com。逐文件审查hash见[review清单](../upstreams/review-2026-10-14.json)，C1/Radxa下载原件hash见[reference manifest](../hardware/reference/manifest.json)。
