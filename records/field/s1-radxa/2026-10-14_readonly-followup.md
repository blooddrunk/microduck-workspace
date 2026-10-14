# S1 · 只读启动健康补查（2026-10-14）

记录类型：REAL_HARDWARE。单板启动/SSH可用性 PASS；整体硬件验收 BLOCKED；既有复位服务失败保留 FAIL。沿用用户确认的单板USB-C接线、保持开机要求、来源未知镜像接受与备份完成（USER_REPORTED）。

## 操作与证据

通过独立SSH会话读取 uptime、free、df、温度、findmnt、服务状态/源码、bluetoothctl show、nmcli设备状态和无线接口计数。普通账户不可见的日志，经评估后按用户授权的继续只读排查范围，使用sudo仅执行journalctl和dmesg；三个受限日志命令均退出0。未重跑rsetup/bt_test、打开串口、扫描/配对蓝牙、变更网络、安装软件、重启/禁用服务或关机。没有运行fsck。

原始证据仅在 `.evidence/s1-radxa/20261014T080108Z-readonly-followup/`；各文件完整SHA256保存在manifest.json。原始日志包含设备/网络标识，不发布；本摘要已检查并移除密码、IP/MAC、序列号、SSID。此轮新增原始证据尚未独立备份。

## 实测结论

- uptime由26分钟增长到27分钟，SSH重复连接成功；结合首次记录，采样覆盖约16–27分钟开机时间，不是连续负载试验。
- 内存总量2074259456字节、可用约1.66GB；根目录约17GB剩余，使用40%，swap当时未使用。
- 本轮SoC温度52.5→51.875°C，GPU温度48.888→47.777°C。不能据此判定满载或电气安全。
- 根分区mmcblk1p3为ext4、rw挂载。内核有`EXT4-fs: recovery complete`，随后成功挂载；所采完整内核日志中未见明确I/O error、Buffer I/O或EXT4-fs error。
- **/config所在mmcblk1p1 FAT分区报告上次未正常卸载**：日志提示可能存在损坏并建议fsck。此为待检查项，不等于已确认数据损坏；未对挂载中的分区执行修复。
- `rsetup-aic8800-reset@ttyS1`源码使用2秒超时，日志确认设备打开成功并发送复位请求，但等待结果超时，返回2；失败未被清除。
- 后续hciattach与bluetooth服务active，控制器`Powered: yes`、`Discovering: no`；这是控制器/服务状态证据，未测试实际配对或收发，不能判定完整蓝牙功能PASS。
- NetworkManager active，无线设备显示connected，采样的RX/TX errors与dropped均为0；没有另行发包验证网关、DNS或互联网，不能等同完整网络验收。
- 完整当前boot警告日志存在240条I2S/ASoC音频参数错误（包括成对日志），以及PipeWire/RTKit、BlueZ插件/profile、显示/设备树相关提示。这些不妨碍已观察的SSH，但不能一概标为无害。
- 未见明确Kernel panic、Oops栈或掉电/过热告警；日志没有告警不能替代供电测量，也不能证明设备一定具备相关检测能力。
- 当前boot早期日志日期与后期不同，故不依赖墙钟日期判定是否重启；本轮日志用journalctl -b限定当前boot，并结合uptime判断观察范围。

## 下一步

当前可以继续单板软件学习/只读检查。正常结束实验时先系统关机再由操作者断电；保持开机是当前明确选择。FAT分区需另在安全离线/卸载条件下检查，不能从本轮只读授权推导修复许可。蓝牙复位超时及音频告警保留为后续镜像/驱动调查项；此轮不修改服务。现有系统启动PASS不授权HAT、电池联合供电或机器人运动。
