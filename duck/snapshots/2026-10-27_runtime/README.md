# 2026-10-27 鸭子运行时快照（sanitized）

- 采集方式：`scripts/duck/pull-duck.sh`（对鸭子只读；未发送任何控制命令）
- 目标：radxa@192.168.8.161（经 GL-MT3600BE 路由器 100.64.0.8 隧道）
- 采集期间事件：14:53 左右鸭子被重启过一次（队友操作），故含重启前后两份服务状态

## 内容

| 文件/目录 | 说明 |
|---|---|
| `system.txt` 等 5 份 | 重启后（up 3min）的系统/网络/服务/文件树/体积五视图 |
| `status-20261027T0654Z-*.txt` | 重启后 1 分钟时的单连接完整采集 |
| `calibration/hd1910-calibration.toml` | **当前生效标定**：15 关节 `calibrated=true`、`motion_enabled=true` |
| `calibration/*.previous / *.saved` | 标定历史档（previous: motion_enabled=false，saved: true） |
| `etc-robot/robotd.toml` | robotd 总配置（28KB，含逐项注释的默认值文档） |
| `etc-robot/feetech-ft5_robotd.toml` | HD1910 运行时配置：policy 路径/增益/skill 表/安全项 |
| `models/provenance-manifests.txt` | 6 个已部署策略的训练出处（task/checkpoint/sha256） |

## 已部署策略（/opt/robot/feetech-ft5-r5/models/，均为 2026-10-01 training-console 训练）

| 模型 hash（前 8） | 任务 | checkpoint |
|---|---|---|
| 1cbf8730 | Mjlab-VelStand-Rough-Backlash（主行走） | model_9599.pt |
| 1c94934c | Mjlab-SitStand-Flat | model_10000.pt |
| 59e15d7b | Mjlab-Roulade-Flat（前滚翻） | model_9999.pt |
| b14e3a8b | Mjlab-GroundPick-Flat-Backlash | model_9999.pt |
| 67ad09d8 | Mjlab-BallKick-Flat | model_9999.pt |
| ee0376c9 | Mjlab-BallKickLeft-Flat-Backlash | model_9999.pt |

另有 roller 技能（crouch/standup/spin）与官方 seed-v5、duck_detect.onnx（权重不入库，
已拉到本机 `local/duck-policies-20261027/`，21 个 onnx 共 43MB）。

## 隐私核对（提交前人工过目）

- [x] 无 WiFi 密码（network.txt 仅 SSID 名与信号）
- [x] 无 SSH 私钥/authorized_keys 内容
- [x] bash_history、.claude 等个人目录未采集
- [ ] 复核 `files-tree.txt` 无敏感路径后再 commit
