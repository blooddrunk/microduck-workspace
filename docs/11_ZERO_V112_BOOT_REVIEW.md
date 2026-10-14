# 11 · ZERO 3W V1.12：独立启动、备用卡与引导回退

2026-10-14 静态审查；本机启动 **NOT_EXECUTED**。2GB、无eMMC来自用户报告；V1.12不能进一步推断为 V1.12I/J 或固定 Wi-Fi 模组，先拍模组标识。

| 来源 | 当前可确认 | 不能据此确认 |
|---|---|---|
| [Radxa FAQ](https://docs.radxa.com/en/zero/zero3/faq) / [下载](https://docs.radxa.com/zero/zero3/download) | ZERO3仅5V，USB-C1 OTG输入；推荐≥15W；V1.12有厂家原理图；串口1500000 | 指定旧第三方镜像可在本机启动 |
| [Armbian ZERO3 下载页](https://armbian.com/boards/radxa-zero3) | 本次页面列26.8.1 Minimal Debian13 vendor6.1.115；有SHA/PGP | 所有V1.12批次/无线驱动/U-Boot都已实测；不把页面stable当本机PASS |
| [fanhao 镜像分析](https://github.com/fanhao375/microduck-replica/blob/5397eb14d356fa618b294a25cebd4bb0ec59c162/docs/HD1910-20261012-kissqy镜像R1分析.md) | 其R1原包主线U-Boot2025.10+DDR1.21在一批V1.12有启动差异；替换Radxa引导有样机成功记录 | 本机同批次；未知镜像均可套补丁 |
| [fanhao 镜像说明](https://github.com/fanhao375/microduck-replica/blob/5397eb14d356fa618b294a25cebd4bb0ec59c162/tools/radxa/镜像使用说明.md) | V1.12J还报告需B1 DTB+引导、Armbian6.1.115、Trixie组合 | 换U-Boot即可解决所有板/无线问题 |
| kissqy Public Image R1 | 社区封装系统带robotd/设备服务和样机校准，系统与执行器合同需分开验收 | 开机成功代表IMU/舵机已兼容 |

推荐先用厂家匹配 ZERO3W/V1.12 的当前完整镜像在**另一张 microSD**启动。如果现在只有一张32GB卡，先完成全卡备份，取得备用卡前不覆盖。没有实际启动错误前，不先改引导。原有系统卡贴标签，断电取出保留。

## 备份/记录卡（电脑 Linux，板子不连接外设）

前提：原卡已从关机板取出，读卡器接电脑，确认物理盘容量/型号和所有分区未挂载；设备路径例子为占位，**不能照抄磁盘号**。在原生Linux读卡器主机执行；WSL若看不到实体盘不猜盘号，可用Windows整卡读取工具保存完整 raw image。

```bash
lsblk -o NAME,SIZE,MODEL,TYPE,MOUNTPOINTS
# 以下 /dev/REPLACE_WITH_VERIFIED_SD 是操作者核对后的整盘，不是分区。
# 确认备份路径不存在，空闲空间大于整卡，原卡各分区已卸载后：
sudo dd if=/dev/REPLACE_WITH_VERIFIED_SD of=local/zero-original-full.img bs=4M iflag=fullblock conv=excl status=progress
sha256sum local/zero-original-full.img
stat -c %s local/zero-original-full.img
sudo blockdev --getsize64 /dev/REPLACE_WITH_VERIFIED_SD
# 原卡未发生任何写入，重新读取比较：
sudo cmp local/zero-original-full.img /dev/REPLACE_WITH_VERIFIED_SD
```

预期文件大小等于整盘字节数，cmp退出0。输出盘号/设备识别可能敏感，留私有证据。异常读错/尺寸不符/cmp非0：停止刷机，保留原卡，检查读卡器，不把不完整镜像称备份。停止dd可Ctrl-C，保留失败文件另命名，重新备份到新文件；`conv=excl`拒绝覆盖既有备份。恢复优先直接插回原卡；若原卡损坏，在**另一张足够大的卡**通过镜像工具恢复完整raw文件并读回比较，不只恢复分区或前32MB。恢复也是写卡动作，先重新核对目的盘；此轮不执行。

每个候选下载镜像保存：发布页面URL、实际文件URL、版本/日期、压缩包与解压image SHA256、发布SHA校验和签名验证状态、镜像字节数、板版本和无线芯片。SHA相符仅是完整性；自行计算的hash不是发布者认证。使用 balenaEtcher 等在备用卡写入并执行读回校验，保存验证结果。拔下电脑读卡器后才装板，不写eMMC/SPI/MaskROM。

## 如果后续确认需要改 bootloader

**此轮不运行补丁**。固定 [kissqy-r1-v112.sh](https://github.com/fanhao375/microduck-replica/blob/5397eb14d356fa618b294a25cebd4bb0ec59c162/tools/radxa/kissqy-r1-v112.sh) 的来源与代码hash见审查清单。脚本报告的源文件（本轮未下载/认证二进制）：

- 原包 `microduck-zero3w-0.15.1-R1.img.xz`，预期SHA256 `75da978b5d56acd9e4146256431732381de84523bb683e4ab7ac9f0580a7bce5`（来自脚本引用发布页，待独立核对）。发布入口：[kissqy 仓库](https://github.com/kissqy/Microduck-kissqy/tree/7a52d297a9adfe6d2315481953dc64060252d142)，不能把其他R版本重命名成R1。
- Radxa包 [u-boot-rk2410_2017.09-64-39cd993_arm64.deb](https://radxa-repo.github.io/bookworm/pool/main/u/u-boot-rk2410/u-boot-rk2410_2017.09-64-39cd993_arm64.deb)，预期SHA256 `fb319203ab7d568aac77505504c05698385aea8a0e8f895c226c6bc557a1bce7`（上游脚本锁值，本轮未实下载比对）。
- 修改的是工作副本image：512字节扇区64写idbloader、16384写u-boot.itb，要求分区从32768或以后开始；改extlinux.conf，不再以armbianEnv.txt作为有效overlay入口；可选禁摄像头/ToF服务。不能将这些偏移直接用于任意实体盘或未知分区布局。

实施前必须有完整卡备份、原压缩镜像/解压镜像、两个引导payload的hash、分区表和/boot副本、恢复卡且读回成功。只对新命名的离线image副本修改；记录每个输入和输出hash、完整命令及diff。源镜像/包hash不同、分区空间不足、缺DTB/overlay、磁盘身份不明立即停止。新卡启动失败先断电回原卡，用3.3V UART（不接适配器VCC，准确确认GND/TX/RX）保存1500000波特引导日志；不循环修改唯一系统卡。不升级内核/替换DTB再“碰碰运气”。若批次需要B1 DTB，再独立固定其来源/hash与匹配内核，不能在运行系统盲换。

本轮没有选定可认证的可用二进制，也没有修改引导；上述是完整的变更前合同，不能填写“bootloader PASS”。
