# duck/ —— 鸭子实况档案

这里存放**这台实物鸭子**（不是上游项目）的当前状态档案与定期快照。多人各自线下推进时，
这里是"鸭子现在到底什么样"的唯一权威答案。

## 当前一页纸状态（2026-10-27 15:00 CST，只读巡检）

| 项 | 值 | 依据 |
|---|---|---|
| 主机名 / 机器人名 | `microduck` / **duck-a437**（serial `e98b5305836f874a`） | `robotctl system info` |
| 主板 | Radxa ZERO 3W，Armbian 26.2.1 trixie，内核 6.1.115-vendor-rk35xx，aarch64 | `uname -a` |
| 存储 / 内存 | 30G eMMC 卡用 36%；2G 内存；温度 ~56°C | `df`/`free`/thermal_zone |
| 网络 | WiFi `GL-MT3600BE-5e4`（信号 100），IP `192.168.8.161`（DHCP 名 `microduck`） | `ip addr`、路由器租约表 |
| 运行时 | kissqy 镜像 R5 派生：robotd/padd/mediad/tofd/btd/configd/gamesir-xboxd/powerlog 全部 active | `systemctl` |
| 标定 | **15 关节全部 `calibrated = true`，`motion_enabled = true`**，IMU 挂载已确认 | [snapshots 标定](snapshots/2026-10-27_runtime/calibration/hd1910-calibration.toml) |
| 策略 | `/opt/robot/feetech-ft5-r5/models/` 下 6 个 hash 目录 + roller 技能；provenance 显示 2026-10-01 由 microduck-training-studio 训练部署 | [snapshots/models](snapshots/2026-10-27_runtime/models/provenance-manifests.txt) |
| 语音 | `voice_chat.py --wake-keep 20` 在跑（`~/zhangtong/duck-voice`，张同的 ASR 项目） | `ps aux` |
| 网页中控 | `http://192.168.8.161:8080`（mediad 提供） | robotd/mediad 日志 |
| 注意 | mediad 崩溃循环持续：重启前 NRestarts=497，14:53 重启后 17 分钟内又 +123（15:10 实测仍在 activating 循环）；当天 14:53 鸭子被重启过一次 | `systemctl show mediad`/uptime |

**能力现状：组装完成、零位标定完成、可站立/行走/翻滚等（社区+自训策略），正在做语音控制；
本队自己主线的训练尚未开始**（见根 README 的 S4 仿真线）。

## 目录结构

```
duck/
├── README.md        ← 本文件：一页纸状态 + 说明
├── network.md       ← 网络身份证：MAC/IP 演变、路由器拓扑、三种连接方式
└── snapshots/       ← 每次 pull-duck.sh 产生的 sanitized 快照（入库）
    └── 2026-10-27_runtime/
        ├── system/network/services/files-tree/sizes.txt   运行时五视图
        ├── status-*.txt                                    单连接完整采集（含重启后复查）
        ├── calibration/   hd1910-calibration*.toml ×3（当前/上一次/保存档）
        ├── etc-robot/     robotd.toml ×4（总配置 + feetech-ft5 当前/历史）
        └── models/        策略 provenance（manifest/contract/profile）+ 构建版本
```

## 怎么刷新这份档案

```bash
scripts/duck/status-duck.sh --save      # 只读巡检（不动鸭子）
scripts/duck/pull-duck.sh               # 生成 duck/snapshots/<今天>_runtime/
# 人工审阅快照无隐私后 git commit；大件（策略权重）用 --policies 拉到 local/（不入库）
```

注意：`motion_enabled = true` 意味着**一上电、给指令鸭子就会动**。远程操作前先看
[安全手册](../docs/manual/15-duck-state-check.md)的红线清单。
