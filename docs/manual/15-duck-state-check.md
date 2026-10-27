# 15 · 鸭子状态巡检手册：怎么看懂它现在的样子

> 目标：回答"鸭子现在健康吗？关节什么状态？网络什么状态？跑了什么程序？"
> **本手册所有命令都是只读的**——不会让鸭子动、不会改任何配置。这也是远程操作的红线：
> 需要让舵机运动、重启服务、写入配置的操作，必须先在群里说，并按 [docs/03 分级通电](../03_POWER_INTEGRATION.md)。

## 1 一键巡检（先跑这个）

```bash
scripts/duck/status-duck.sh            # 打印 9 段报告
scripts/duck/status-duck.sh --save     # 同时留档到 .evidence/duck-status-<时间戳>/
```

输出分 9 段，下面逐段解释**看什么、什么算正常**。

## 2 系统与资源（第 1、2 段）

| 看什么 | 正常参考（2026-10-27 实测） | 异常信号 |
|---|---|---|
| `uptime` | 空闲时 load < 1 | load 持续 > 3：有程序失控（见 §6 mediad 案例） |
| `free -h` | 2G 内存，空闲时 used < 700M | available < 200M 会开始用 swap、卡顿 |
| `df -h /` | 30G 卡用 ~36% | > 85% 要清理（大头通常是日志/模型） |
| thermal_zone | 45–60°C | > 80°C 会降频，摸头壳烫手就要停 |
| 温度来源 | `/sys/class/thermal/thermal_zone*/temp`（毫摄氏度） | — |

## 3 网络状态（第 3 段）

| 看什么 | 命令（鸭子上） | 解读 |
|---|---|---|
| IP 地址 | `ip -br address` | `wlan0 ... 192.168.8.161/24` 为正常 |
| 网关/路由 | `ip route` | `default via 192.168.8.1` = GL 路由器 |
| WiFi 名和信号 | `nmcli -t -f ACTIVE,SSID,SIGNAL dev wifi` | `yes:GL-MT3600BE-5e4:100`；信号 < 40 走路会掉线 |
| 从外面测 | 本机 `scripts/duck/find-duck.sh 192.168.8` | 扫不到 = 不在线/换网 |

> 深入：[duck/network.md](../../duck/network.md) 有完整拓扑和历史 IP 记录。

## 4 运行时服务（第 4 段）——鸭子的"生命体征"

kissqy R5 运行时由一组 systemd 服务构成（`systemctl status <名>` 看详情）：

| 服务 | 干什么 | 正常状态 |
|---|---|---|
| `robotd` | **主控制守护**：读 15 舵机+IMU、跑策略、安全死人 | active (running)，NRestarts=0 |
| `padd` | 手柄意图客户端（网页/实体手柄 → robotd） | active |
| `mediad` | 摄像头/音频/网页中控（**8080 端口**） | active；NRestarts 很大 = 已知问题（§6） |
| `tofd` | 头部 ToF 测距 | active |
| `btd` / `configd` / `gamesir-xboxd` | 蓝牙/配网/手柄桥 | active |
| `powerlog` | 掉电诊断记录（团队自加） | active |

关键看点：

```bash
systemctl show robotd --property=ActiveState,SubState,NRestarts,MainPID
systemctl --failed --no-pager        # 应该输出为空
journalctl -u robotd -n 20 --no-pager
```

- 日志里周期性出现 `intents went stale — the velocity command is zeroed` 是**正常的**：
  没人操作时安全机制每秒把速度指令清零（deadman）。它在工作 = 安全系统活着。
- `systemctl --failed` 有条目 = 有服务挂了，把输出贴到群里。

## 5 物理状态：关节标定与 IMU（第 5 段）——鸭子最贵的档案

**标定文件是这只鸭子的"身体记忆"，丢了就要重新调零。** 当前生效的是：

```
/etc/robot/feetech-ft5/hd1910-calibration.toml
```

里面记录了 15 个关节（右腿 10–14、左腿 20–24、头颈嘴 30–34）各自的：

- `zero_raw`：机械零位的编码器原始值（约 2048 ± 60，每只鸭子唯一，**这就是"调零"的结果**）
- `direction` / `min_rad` / `max_rad`：方向与软限位
- `calibrated = true`：该关节已标定
- 文件头 `motion_enabled = true`：**允许运动总开关**（false 时策略拒绝输出）

IMU 挂载姿态在 `imu_mount_quat`（四元数），`imu_mount_verified = true`。

只读查看（别用编辑器改它）：

```bash
grep -E 'motion_enabled|imu_mount' /etc/robot/feetech-ft5/hd1910-calibration.toml
python3 -c "import tomllib; d=tomllib.load(open('/etc/robot/feetech-ft5/hd1910-calibration.toml','rb')); [print(j['name'], j['id'], j['zero_raw']) for j in d['joints']]"
```

> 舵机实时角度/电压/温度：网页中控有面板；命令行可用 `robotctl`（先用 `robotctl --help` 看，
> 只用查询类子命令）。历史台账在仓库 [hardware/](../../hardware/) 与 docs/09。

仓库里的最新存档：[duck/snapshots/2026-10-27_runtime/calibration/](../../duck/snapshots/2026-10-27_runtime/calibration/)。
**每次重新标定后必须 `scripts/duck/pull-duck.sh` 重新存档**，这是多人协作的保命习惯。

## 6 已知问题：mediad 崩溃循环（2026-10-27 实测 NRestarts=497）

症状：`systemctl show mediad -p NRestarts` 数字巨大（几百），CPU 被 gst-plugin-scanner 吃掉，
负载 3+，机身发热。

- 原因线索：kissqy 镜像里 mediad 负责摄像头/音频/网页；无摄像头或音频被占用时会反复崩
  （fanhao 上机记录也有此现象，见 `.upstreams/fanhao-replica/docs/HD1910-20261012-kissqy整套上机.md`）。
- 诊断：`journalctl -u mediad -n 50 --no-pager` 看崩在哪一步。
- **临时缓解（需群里确认后做）**：不用摄像头/语音时 `sudo systemctl disable --now mediad`
  ——但网页中控 8080 也是它提供的，关了网页就没了。取舍见[手册 17 优化清单](17-team-workflow.md)。

## 7 电源与电池

- 目前 `feetech-ft5_robotd.toml` 里 `"battery_empty_shutdown" = false`、`"limp_fall" = false`
  （含义：低电不自动关机、失稳不软倒）。**低电保护未启用**，人离开前手动关机。
- 电量/电压看网页中控面板，或 `robotctl system` 系列子命令（先 `--help`）。
- 掉电诊断数据：`powerlog` 服务在记录（团队为排查"摔倒掉电"加的）。

## 8 把状态存进仓库（团队约定）

```bash
scripts/duck/status-duck.sh --save     # 原始留档 .evidence/（不入库）
scripts/duck/pull-duck.sh              # sanitized 快照 → duck/snapshots/<日期>_runtime/
# 人工审阅后 git commit，让大家都能看到鸭子当天长什么样
```
