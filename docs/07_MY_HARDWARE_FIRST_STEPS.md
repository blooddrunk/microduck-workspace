# 07 · 针对这套实物的下一步：ZERO 3W V1.12、官方 C1 HAT、HD1910

> 截至 2026-10-14，按实物照片与用户反馈形成本课。**不代表已经替你的机器完成电气/固件验收。**硬件档案：[硬件 JSON](../hardware/observed-2026-10-14.json) · [审查记录](../records/2026-10-14_hardware-photo-review.md)。

## 先明确 Codex 和你的顺序

**先发给 Codex 的 Goal 可以立即执行**：软件/原理图/FT6 与 IMU 对照不依赖完成下面 4 项；你可以随后或同时完成 S0/S1/S2 的人工任务。远程 Codex 只读取得的公开仓库文件与脱敏摘要，**看不到**被 Git 忽略的 `.evidence/`。实验过程的原始文件放 `.evidence/<阶段>/<run-id>/`，公开可分享的结果按 [records/field/ 分阶段证据目录](../records/field/README.md) 填写脱敏 Markdown。没有实测结果时 Codex 应标 BLOCKED，并继续完成其它离线任务。只有 S3 的最终接线/上电/使能依赖真实验收。

## 一页结论：下一轮先做 4 项，不要先组装通电

| 顺序 | 要做的事 | 要提交的结果 | 何时停止 |
|---|---|---|---|
| 1 | 单独启动 ZERO 3W V1.12（已装 32 GB microSD） | 系统发行版、`uname -m`、SSH、诊断输出 | 无可信系统镜像/没有 5V 供电证据 |
| 2 | 用 FE-URT2-C001 逐只**只读** HD1910 | 15 个 ID→实体关节；中位校准前姿态说明；模式/读数 | 无法确认单只 ID 或误动作 |
| 3 | 核对 C1 HAT、电池座及 IMU 供电（**断电测量**） | 端子朝向/实物正反面、C1 原理图、供电路径、VCC 规格 | 不知道 GND/V+/DATA 或 IMU 额定电压 |
| 4 | 纯软件解析 IMU 示例协议，准备独立只读台架 | 示例帧脚本通过、身份寄存器/缩放系数疑点清单 | 试图直接启用真机策略 |

当前**不应**把 2S 电池、HAT、IMU、15 颗舵机全部一起接到板子后启动。

## 任务 A · ZERO 3W V1.12：独立启动

你目前有：ZERO 3W PCB `V1.12`、2GB、无 eMMC、有排针；SanDisk Ultra A1 32GB microSD。**这张卡可能已有镜像，但照片不等于已经刷机。**

1. 电脑端准备 USB 读卡器和可信的 ZERO 3W **RK3566/AIC8800 对应镜像**。优先查 [Radxa ZERO 3 官方系统安装](https://docs.radxa.com/en/zero/zero3) 或 [Armbian ZERO 3](https://www.armbian.com/radxa-zero-3/)；镜像名称与发布 SHA 必须记录。镜像下载页若没提供 hash 就记录无法校验，而非“校验成功”。
2. **刷机前对 microSD 备份**；系统镜像与刷卡工具同时选择正确设备，避免误擦 Windows 磁盘。若已有未知系统，建议另用干净卡做试验，不覆盖唯一可用系统。
3. 主板**不要插 HAT、IMU、舵机、F550 电池**，只通过背面丝印标 `5V IN / USB OTG` 的供电接口（不是 `USB3.0` 或 `HDMI`）给 **5V**；使用能稳定提供至少 2A 的正规电源/线。先核对原板背面丝印与当前插口朝向；不应使用 7.4V 电源直接输入主板。
4. 第一次启动后从路由器查 IP，电脑 PowerShell（不是 Radxa 终端）执行：

```powershell
ssh <系统创建的用户名>@<路由器确认的局域网IP>
```

5. 在 Radxa SSH 终端执行，只读：

```bash
uname -m
cat /etc/os-release
uname -a
lsblk -o NAME,SIZE,TYPE,MOUNTPOINTS
cat /proc/cmdline
systemctl --failed --no-pager
```

期望 ARM64 `aarch64`、可见 microSD 系统盘、SSH 稳定；异常/无 Wi-Fi/无法引导保持 BLOCKED 并记录镜像与启动日志，不要瞎改 bootloader。此时不要安装 `robotd`。

6. 电脑的 Linux/WSL 工作区按 [06 自动化验收卡 H1](06_S0_S2_AUTOMATION.md) 复制 `diagnose_radxa.py` 到板上，回传**脱敏**的原始检查和源码 hash；命令/SSH 前置详见原教程。按正确流程 `sudo shutdown -h now` 关机，断开唯一 5V 电源。

**V1.12 专项提示**：fanhao375 发现同批 V1.12 对 kissqy Public Image R1 引导存在差异，参见 [2026-10-12 镜像分析](https://github.com/fanhao375/microduck-replica/blob/master/docs/HD1910-20261012-kissqy镜像R1分析.md)。不能直接假设 `kissqy R1` 适配你的 V1.12；先独立完成 A 并留好可启动的基线 SD 卡。如果纯净系统启动失败，优先获取当前适配 V1.12 的厂家镜像/bootloader 证据，**不要先跑未知脚本写 boot 扇区**。

## 任务 B · FE-URT2：复核 ID 与 2048，不再重写

1. 确认断开 HAT/其他电源，一次仅接一颗舵机到飞特 FE-URT2-C001 的**TTL 半双工**输出。优先沿用你先前已经确认和成功工作的那条接线；若换线/接口或换电源，必须重新测量极性与供电。不要误插 RS485。
2. 在 Windows 飞特 FD 软件中选已确认的串口和设备实际波特率（HD1910 常见 1000000，但读出才算确认），**只做 Search/Read**；截取 ID、固件、工作模式、`当前位置 raw`、电压、温度、扭矩使能状态、P/D/限位和可用的校准偏移。
3. 断电后换下一颗；记录 15 颗的**贴纸→实际关节→ID**，以后可用 `templates/hd1910_inventory.csv` 及 `scripts/validate_servos.py` 校验重号/缺项。没有逐只重新清点就不标记 15/15 已通过。
4. 对“2048”进行区分：`编码器 2048` 只是可表示的中点；执行 FD“中位校准”时**那一刻关节是什么姿态**，才决定哪个几何角等于零。按 [09 · 校零复核](09_HD1910_ZERO_REVIEW.md) 审查后才有权讨论是否需要重校。
5. 以当前“**已写过一次中位，但正确性待验证**”为客观状态。**禁止为了得到 2048 读数而重复执行中位校准；禁止立即 15 关节 HOME/站立。**

建议将成功/失败截图存到本地证据目录（注意脱敏），并在记录中注明“来自真实 FE-URT2 只读”而不是仿真器合成数据。

## 任务 C · C1 HAT：查准源文件，先断电核对

### 确认的型号

你的板子贴纸可辨为 `elec_RPI_Robot_HAT ASE01187-C1`、Pollen Robotics 品牌标识；主控对接接口为 40Pin **排母**，属于**官方 HAT C1 设计**，而不是 kissqy 的自制 HAT。

官方开源仓库在历史目录留有与标签一致的工程快照：

- [C1 原理图](https://github.com/pollen-robotics/elec_RPI_Robot_HAT/blob/main/production/_old/ASE01187-C1_elec_RPI_Robot_HAT_SCH.pdf)
- [C1 BOM](https://github.com/pollen-robotics/elec_RPI_Robot_HAT/blob/main/production/_old/ASE01187-C1_elec_RPI_Robot_HAT_BOM.csv)
- [官方 HAT README / PCB revision](https://github.com/pollen-robotics/elec_RPI_Robot_HAT)

官方 C1 版本修复了 3V3、理想二极管方向并将 I2C3 设为默认接口；D1 后续改动了其它器件。**禁止拿仓库当前 D1 的连接器图片/供电位置代替 C1 实物。**

### 能识别但尚未完成供电核对的接口

| 实物位置/标号 | 官方设计用途 | 要做的检查 |
|---|---|---|
| `J13 / J14` 白色 **3P** | TTL 半双工舵机总线，供电通过电机母线分配 | 核对 C1 原理图上的 DATA、`+BATT`、GND 各针端视图；飞特舵机线可能 2.0mm、HAT 使用 2.5mm，要用正确 2.0→2.5 线束，不硬插 |
| `J3 / J11` 白色 **4P** | RS485 舵机口 | **不能**拿它接三线 TTL HD1910/IMU |
| `Speak` 标注的 **2P** | 喇叭输出 | **绝不是电池输入**，不能接 F550 或可调电源 |
| `J5–J8` 小型 **4P** | HAT I2C/SPI 类扩展口（实际用途随端口） | 不是你的“3 线总线 IMU”插座 |
| `2×20` 排母 | 与 ZERO 3W 排针叠接 | **断电**比对 1 号针位置、防短路、间隙/机械支撑 |

官方 HAT README 说明**HAT 通过电机连接器获得供电**，并从该母线稳压供给主控 5V。这不是“把 F550 直接接到 5V 口”：必须用 **C1 原理图确认电机母线与 5V 路径**，先不接 ZERO、舵机和 IMU，用受限流电源在正确引脚测空载电压与极性，合格后分段测试。**本页不提供凭照片猜的插座针脚编号。**

### 电池

唯卓仕 F550 是 NP-F 类电池，需另有合适的**电池座/取电板**及连接器。拍电池座正反面和铭牌，断电核实电池座 `+`/`-`，再用万用表测实际输出；**2S 满电可到 8.4V**，接近 HD1910 额定上限，确认供电过压/纹波与接头额定后才使用。初期优先可调电源，先确认是否有**可靠限流和物理断电开关**，不要使用鳄鱼夹做运动负载电源线。

## 任务 D · 第三方双协议 IMU：先确认实物、再读 ID200

商品截图展示一个*总线 IMU*，不是 BNO085 I2C 方案。按 [08 · 协议及兼容性核验](08_VENDOR_IMU_COMPATIBILITY.md)，先核对商家**实际模组 VCC 输入范围、接头间距、实物丝印、固件版本**；不具备这些数据**不允许接到 8.4V 电机母线**。

从电脑离线验证协议帧不需连设备：

```bash
python3 scripts/imu_protocol.py --requests
python3 -m unittest discover -s tests -v
```

之后才由现场人员决定是否安全进行 FE-URT2 **只读** ID200 Ping/Read。此步骤要求扭矩 OFF，**不能连着 15 个舵机直接开扫描**，单独 IMU 台架、共地、源电压规格与 ID200 正确无误后执行。

## 当前硬门槛

| 门槛 | 2026-10-14 状态 |
|---|---|
| HAT **型号/设计分支** | 已从照片确认 C1 |
| 主板 **型号/设计分支** | 已从照片确认 V1.12；2GB/无 eMMC 用户报告 |
| 可调电源与 FE-URT2 | 用户报告已拥有，能力/接线待核 |
| 2048 **中位命令已操作** | 用户报告；机械零位未验收 |
| ZERO **实际引导成功** | BLOCKED |
| HAT **极性/5V 输出实测** | BLOCKED |
| IMU **供电额定、身份、数值格式** | BLOCKED |
| 全机同时供电、全部上力或跑 Policy | **禁止越过前述 Gate** |

按这些步骤上传系统诊断、FD 截图和 HAT/IMU/电源读数后，下一轮才生成每一根真实线束的最终接线表并进入 S3。

## 本轮审查后的优先入口

先用 [12 最小操作教程](12_MINIMAL_OPERATOR_STEPS.md)。C1针号候选、电源路径和反灌见[10](10_C1_ELECTRICAL_REVIEW.md)，V1.12启动/原卡保护见[11](11_ZERO_V112_BOOT_REVIEW.md)，更新后的[08](08_VENDOR_IMU_COMPATIBILITY.md)固定QinmoTech原文，[09](09_HD1910_ZERO_REVIEW.md)含15→14映射与本机校准来源检查。旧段落中“下轮才生成接线表”现已细化为**已有源码候选表，仍需实物端视图与万用表验收**；没有最终接线许可。
