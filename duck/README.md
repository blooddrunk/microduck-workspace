# duck/ —— 鸭子实况档案

这里存放**这台实物鸭子**（不是上游项目）的当前状态档案与定期快照。多人各自线下推进时，
这里是"鸭子现在到底什么样"的唯一权威答案。

## 当前一页纸状态（2026-10-28 10:17 CST 增量巡检；上一版 2026-10-27 15:00）

| 项 | 值 | 依据 |
|---|---|---|
| 主机名 / 机器人名 | `microduck` / **duck-a437**（serial `e98b5305836f874a`） | `robotctl system info` |
| 主板 | Radxa ZERO 3W，Armbian 26.2.1 trixie，内核 6.1.115-vendor-rk35xx，aarch64 | `uname -a` |
| 存储 / 内存 | 30G eMMC 卡用 36%；2G 内存；温度 ~59°C（10-28 实测，10-27 为 ~56°C） | `df`/`free`/thermal_zone |
| 网络 | WiFi `GL-MT3600BE-5e4`（信号 100），IP `192.168.8.161`（DHCP 名 `microduck`）；**本体 Tailscale `100.64.0.12`**（2026-10-28 起，tailnet `hs-nosla.haoqi90.top`） | `ip addr`、路由器租约表、`tailscale ip` |
| 运行时 | kissqy 镜像 R5 派生：robotd/padd/mediad/tofd/btd/configd/gamesir-xboxd/powerlog 全部 active | `systemctl` |
| 标定 | **15 关节全部 `calibrated = true`，`motion_enabled = true`**，IMU 挂载已确认 | [snapshots 标定](snapshots/2026-10-27_runtime/calibration/hd1910-calibration.toml) |
| 策略 | `/opt/robot/feetech-ft5-r5/models/` 下 6 个 hash 目录 + roller 技能；provenance 显示 2026-10-01 由 microduck-training-studio 训练部署 | [snapshots/models](snapshots/2026-10-27_runtime/models/provenance-manifests.txt) |
| 语音 | `voice_chat.py --wake-keep 20` 在跑（`~/zhangtong/duck-voice`，张同的 ASR 项目） | `ps aux` |
| 网页中控 | `http://192.168.8.161:8080`（现场/子网路由）或 `http://100.64.0.12:8080`（tailnet，异地首选） | robotd/mediad 日志 |
| 手柄 | **当前无任何已配对手柄**（2026-10-28 预检，配对表只有一副耳机）；真 Xbox One S/Series **免装驱动即用**（内核 xpad/hid-microsoft 在板、BlueZ 5.82，`sudo robotctl pad pair` 即连） | [手册 18](../docs/manual/18-xbox-gamepad.md) · pad-preflight |
| 注意 | mediad 崩溃已缓解（2026-10-27 16:20 `media.source="test"`，备份 `.bak-20261027-camoff`，8443 信令恢复）；**但 2026-10-28 上午板子自发重启 4 次**（09:17/09:22/09:45/09:53，与 mediad 无关，电源/散热嫌疑 → 手册 17 §3 #5）；tailscale 已装，重启自动回 tailnet | uptime 序列、[network.md §5](network.md) |

**能力现状：组装完成、零位标定完成、可站立/行走/翻滚等（社区+自训策略），正在做语音控制；
本队自己主线的训练尚未开始**（见根 README 的 S4 仿真线）。

## 目录结构

```
duck/
├── README.md        ← 本文件：一页纸状态 + 说明
├── network.md       ← 网络身份证：MAC/IP 演变、路由器拓扑、三种连接方式
└── snapshots/       ← 每次 pull-duck.sh 产生的 sanitized 快照（入库）
    ├── 2026-10-28_runtime/   网络变更增量快照：本体 Tailscale 装机记录与实测数据
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
