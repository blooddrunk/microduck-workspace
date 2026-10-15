# 2026-10-15 · 上游快照同步

## 结果

从 `main` 基线 `c0ceabe17ac23660bbcd5b47fa9731c070f69e5d` 开始时，工作区干净，且本地 `main` 与 `origin/main` 一致。运行 `python3 scripts/sync_upstreams.py check` 检查目录中全部 8 个上游：3 个发现新 HEAD，0 个查询错误。按仓库的同步流程，只取回这 3 个更新并审阅变更摘要、主要路径和硬件/运行时相关代码，然后更新 `upstreams/sources.json` 的固定 SHA 与日期。

| 来源 | 旧 SHA | 新 SHA | 更新摘要与处理 |
|---|---|---|---|
| `official-runtime` (`pollen-robotics/microduck`, `main`) | `95a7e91725b4c079a6ee6ba0a018c8b08e2a7e46` | `648bf228207f1fdedb652516d90d97ec3c50fffa` | 18 个提交、43 个文件。增加可配置的 idle 头部/嘴部动作及 Vetbook 传感器记录与卡片；没有发现 Feetech、IMU、HAT、电源或舵机总线改动。仅更新快照锁，没有引入机器人行为。 |
| `fanhao-replica` (`fanhao375/microduck-replica`, `master`) | `5397eb14d356fa618b294a25cebd4bb0ec59c162` | `1a2936849b47e638dfc596996026f047dcfb5b05` | 5 个提交、10 个文件。README 与实机记录更新，新增步态分析脚本；文档记录了 V167/control.43 使能时写 RAM D=0、扭矩限制 1000。该社区记录不是本机测量或运行许可。 |
| `kissqy-runtime` (`kissqy/Microduck-kissqy`, `main`) | `7a52d297a9adfe6d2315481953dc64060252d142` | `02a8548d86d9bdcc04047c0ef8b706432cee6a59` | 8 个提交、218 个文件。发布 R17 V167/control.43、整理 FT6_SYNC15 固件资料与包，并增加 AMP2.0 HAT/IMU 工程和打印资料。审阅到固件使能流程会写 RAM D=0 与扭矩限制 1000；AMP2.0 是新的硬件版本。本次不安装该固件、不应用这些参数，也不据此认定 IMU、AMP2.0 或整机兼容。 |

其余 5 个来源（`official-rl`、`official-hat`、`hd1910-rl`、`luwu-actuator`、`qinmo-imu`）检查时均与原锁一致。三项更新的比较范围、提交摘要与硬件相关改动已审阅；未发现这些差异中有 `LICENSE`、`COPYING` 或 `NOTICE` 文件变更。

## 范围与验收边界

- 本次只推进三个上游 SHA；新源文件、固件、模型、硬件工程与二进制没有复制进本仓库。浅克隆留在 Git 忽略的 `.upstreams/`。
- 未运行上游安装/构建脚本，未执行 `update.sh`，未更改本机官方运行时或策略；未安装镜像/固件，未连接或驱动硬件。
- 本次没有运行软件测试或硬件验收。版本锁表示快照基线更新，不表示代码集成、测试通过或本机兼容；既有 C1/IMU/供电/舵机验收状态不变。
- 更新锁后再次执行 `python3 scripts/sync_upstreams.py check`：8 current、0 update、0 error。

2026-10-14 的逐文件源码/硬件审查继续代表其当时固定的 SHA，不会被本次锁更新追溯改写。
