# S1 · ZERO 3W USB 首次只读实测（2026-10-14）

记录类型：REAL_HARDWARE；接线前提由操作者确认（USER_REPORTED）。整体硬件验收：BLOCKED；诊断采集整体：FAIL。

本轮范围更新：用户接受来源未知的现有镜像作为单板学习实验基线。**现有系统启动与 SSH 可用性 PASS**；镜像来源 UNKNOWN，不再单独阻塞当前只读单板实验，不能记为来源校验通过。备份完成由用户确认（USER_REPORTED），未由 Agent 核验备份文件、完整性或恢复能力。

## 已实测

- 操作者确认仅连接 USB-C，未连接 HAT、舵机、IMU 或电池。
- 三个独立 SSH 会话登录成功，使用既有主机密钥校验；没有关闭 SSH 密钥检查。未另行通过实物终端核对主机指纹。
- Debian GNU/Linux 12 (bookworm)、aarch64；内核 6.1.84-10-rk2410-nocsf，Python 3.11.2。
- 设备树型号 Radxa ZERO 3，内存约 2 GB；系统盘 mmcblk1 29.7 GiB，根分区 mmcblk1p3。
- 温度两轮采样约 50.6–55.0°C；uptime 持续增长。只能证明采样期间的状态，不能证明长期或负载稳定性。
- 将 scripts/evidence.py 与 scripts/diagnose_radxa.py 复制至独立用户目录，双端 SHA256 一致；执行 `python3 scripts/diagnose_radxa.py --output .evidence/s1-first --robotd`，退出码 1。
- 结构化报告已回传；16 份 raw JSON 的 SHA256 与 summary 逐项一致。

## 异常和验收边界

- FAIL：rsetup-aic8800-reset@ttyS1.service，蓝牙复位 ExecStart 返回 2。
- BLOCKED：普通账户无法读取完整 journal 或 dmesg；进程设备占用视图不完整；robotd 未安装；硬件验收仍需现场电气证据。
- 无线接口状态 up；没有验证 Wi-Fi 联网，不能判定无线功能通过。蓝牙失败不是 bootloader 故障证据。
- 现有镜像下载来源/发布 hash、刷写校验未知；用户已接受此限制。用户确认备份完成。
- 用户报告供电来自电脑 USB4 接口，经 USB-C 线连接主板；现有启动和 SSH 已验证该组合在采样时可用。端口具体供电额定能力、板端电压及负载下稳定性尚未测量（NOT_EXECUTED），不将其改写为实测 PASS。
- 未刷卡、改 bootloader/网络/服务、安装运行时、探测串口或控制机器人。用户要求保持开机，安全关机与人工拔线 NOT_EXECUTED。

## 证据与来源

原始文件仅保存在 `.evidence/s1-radxa/20261014T075107Z-usb-baseline/`，未公开。摘要已人工检查，不含密码、IP/MAC、设备序列号或网络凭证；原始证据尚未独立备份。

源码 commit：UNKNOWN（板上无 Git 元数据；来源以电脑记录为准）。电脑源码 commit：c950a5e0a442efb5146889f38cf108f48fd898fa。

- evidence.py SHA256：b926cedd4af61cc2ab78f5dfcdf10878f2201c3cb963c1b594cfddcd64b871de
- diagnose_radxa.py SHA256：b662be21a334c5ad21a7edb02d2789cac4d690a9c743768b7410e8ee0eedad15
- 回传 summary.json SHA256：dce1dc253798d9b82a6ab76c4866b7c511d3ec29af5d0bf05d68fb81f3ab6705

下一步：可继续单板只读排查蓝牙失败及系统日志，保留当前可启动的卡。镜像来源已按用户要求接受为未知，备份按用户确认完成；电气实测与负载稳定性仍为独立未完成项。本记录不授权 HAT、电池联合供电或机器人运动。


后续已取得sudo只读完整日志，原日志权限缺项已补采；新增FAT未正常卸载与音频警告，详见[只读补查](2026-10-14_readonly-followup.md)。历史诊断原始状态未改写。
