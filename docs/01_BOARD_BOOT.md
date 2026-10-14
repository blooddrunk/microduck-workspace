# 01 · Radxa ZERO 3W 独立刷机、开机和 SSH（可先做）

**目标：** 主板未接 HAT、IMU、舵机和 2S 电池时，单独进入 Linux 并通过 SSH 采集系统信息。验收通过前不执行任何电机程序。

## 1. 准备

- Radxa ZERO 3W（RK3566）、合适的 microSD 与读卡器、品质可靠的**5V/2A 或更高供电能力** USB-C 适配器/线、一台 Windows/Linux 电脑。
- 建议预备第二张 microSD：一张**可回退的纯净 Armbian 系统卡**，另一张以后用于第三方复刻镜像。切勿覆盖唯一正常启动的卡。
- 不安装 HAT，不插 2S 电源/舵机/IMU。某些 Zero 3W 板可能带 eMMC，先核对 PCB/购买配置，不能盲选目标存储器。

## 2. 选择并下载系统镜像

优先从 [Armbian 官方 ZERO 3W 页面](https://www.armbian.com/radxa-zero-3/) 下载受支持的 **Minimal/CLI ARM64** 镜像，或按 [Radxa 官方安装文档](https://docs.radxa.com/en/zero/zero3) 选择匹配板型镜像。**不要选择 Raspberry Pi Zero 镜像，也不要默认第三方镜像适配你的 HAT。**

在下载页记下：系统发行版本、文件名、下载地址、镜像发布时间、校验文件。若发布方给出 SHA256，Windows PowerShell 可以验证：

```powershell
Get-FileHash "C:\path\to\your-image.img.xz" -Algorithm SHA256
```

与发布方公布的完整校验值**逐字符**比对；不一致不要刷。若发布方没有校验值，记录“无法独立核验来源”，不得写“已验证 SHA”。使用 [Armbian Imager](https://imager.armbian.com/) 或可信镜像工具指定**正确 microSD**，并在写入后执行工具的 verify/read-back（若支持）。刷写操作**会清除目标卡全部数据**。

## 3. 首次独立开机

1. 电脑端安全弹出 microSD，插入 Radxa；检查板子无短路、端口无遮挡。
2. **只接 5V USB-C 电源**。正常启动可能需要数分钟；首次设置用户/密码按你选择镜像的当前提示操作。
3. 使用路由器的“已连接设备”列表确认 IP。不要猜测固定 IP 或默认密码。
4. 电脑与 Radxa 同一可信局域网，Windows Terminal/PowerShell 执行：

```powershell
ssh <实际用户名>@<从路由器查到的IP地址>
```

`<...>` 是占位符，**先替换再执行**。首连核对主机指纹；如果旧卡/新卡使用了同一 IP，主机密钥变化需要核查原因，不要无条件忽略 SSH 告警。

## 4. 在开发板 SSH 终端逐条执行只读检查

```bash
uname -m
cat /etc/os-release
uname -a
cat /proc/meminfo | head -n 5
lsblk -o NAME,SIZE,TYPE,MOUNTPOINTS
df -h /
ip -brief address
ip route
ls -l /dev/ttyS* 2>/dev/null || true
ls -l /dev/i2c-* 2>/dev/null || true
systemctl --failed --no-pager
journalctl -b -p warning --no-pager | tail -n 80
```

**期望**：`uname -m` 通常是 `aarch64`；SD/根分区可见；有 IP 与默认路由；没有持续 USB/SD I/O 错误和重启。系统可能有少量无害 warning，请保留原始日志而不是“没有错误”一笔带过。`ttyS*` 或 `i2c-*` 存在仅表示 Linux 有设备节点，**不代表接上的舵机/IMU 通了**。

### 重要：UART 与引脚复用

ZERO 3W 的 UART2_M0 在 40 针物理 pin 8(TX)/10(RX) 上，Radxa 官方说明它也可能是 U-Boot/调试控制台。**不要直接把飞特总线 DATA 接到这两个脚**。先查实际设备树 overlay、console 是否占用、HAT 逻辑电平及半双工收发器，再在未来 S3/S5 使用正式驱动。禁止凭网上“/dev/ttyS2”名称自动判断插脚。

## 5. 最小安全加固与备份

设置新的强口令，优先添加你的 SSH 公钥；只在验证密钥登录可用后再考虑禁用口令。不要把凭据、Wi-Fi 密码或私钥提交本仓库。

成功 SSH 后关机（**没有其它电源路径**时）：

```bash
sudo shutdown -h now
```

确认设备完全停机后拔下 USB-C；给 microSD 做完整备份或保留可重刷镜像，记录板型与系统版本。

## 6. 什么时候选 kissqy Public Image R1？

它是**可选的第二张卡路径**，不是本节成功的必要条件。来源 [kissqy README](https://github.com/kissqy/Microduck-kissqy#下载与版本) 声称已实测 ZERO 3W 镜像、飞特 runtime 与中文中控。但它在其自身 HAT/IMU/固件组合中验证，**不是你的硬件兼容性承诺**。先通过纯净 Armbian 独立开机，再评估：

- 校验镜像来源与校验值，记录版本和服务/固件版本；镜像公开的热点/初始密码**首次配置后立即修改**。
- 先保持舵机供电物理断开；在有措施保证 `robotd` 不会开机上力之前，**不要将预配置运动镜像接入完整机械总线**。
- 固件与 IMU 是否“飞特总线 IMU”，以及 HAT 版次/供电路径是否与镜像适配，必须在 [02](02_SERVO_IMU.md) 和 [03](03_POWER_INTEGRATION.md) 里确认。

**验收记录**：镜像版本与 hash（或无法校验）、实际 IP（发布记录可脱敏）、`uname -m`、`os-release`、`lsblk`、异常日志、第一次开机照片、关机确认。此时只勾选 Checklist S1，接下来做 [02](02_SERVO_IMU.md)。
