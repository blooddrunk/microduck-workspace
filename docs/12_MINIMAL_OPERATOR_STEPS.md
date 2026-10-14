# 12 · 本轮之后的最小操作教程

这轮软件准备完成不会改变硬件S1–S3状态。最短路径是**断电测量 → 单板 → 单舵机**，第三方IMU在额定电压缺失时等待。全机/电池联合供电、EEPROM、HOME均不在本轮许可内。

| 步骤 | 操作前提与具体操作 | 预期 / 异常判定 | 停止、恢复与证据 |
|---|---|---|---|
| 1 · 断电C1 | 拔全部电源、ZERO与HAT分离；按[10测量卡](10_C1_ELECTRICAL_REVIEW.md)测J13/J14 pin1/2/3与J4 GND、5V、电池网；端视图照片找到pad1后才编号 | 同网低阻，异网无持续短路；无法确定编号或图不符=BLOCKED/FAIL | 不接电；保留分离状态；拍两表笔、档位、极性、阻值；保存s3-hat-power摘要 |
| 2 · 备用系统卡 | 保留原卡、按[11](11_ZERO_V112_BOOT_REVIEW.md)完整备份与cmp；备用卡写可信ZERO3W镜像并读回；只接USB-C1 5V，不接HAT/舵机/IMU | 独立开机、无异常热/重启、可SSH；失败先核对供电/卡/hash，不能据Wi-Fi失败认定bootloader坏 | 异常立即断电；换回原卡；保存镜像URL/hash、板/Wi-Fi照片、UART或启动日志 |
| 3 · 只读系统 | 从电脑SSH到实际账户；在板上执行下列只读命令及docs06 H1脚本 | aarch64、存储/内存符合实物、无关键失败服务；缺权限/日志=BLOCKED | 保存原输出，不安装robotd；正常sudo shutdown关机再拔5V；异常恢复原卡 |
| 4 · 15只逐个读回 | 沿已确认FE-URT2台架，断电换线一次一只；FD仅Search/Read，读ID/固件/模式/raw/电压/温度/扭矩及可读偏移；填docs09台账 | 15只实物标签/关节/ID唯一可追溯；2048只作读数，不等同机械零位 | 运动、发热、异常供电即撤电；不点位置目标/校准/写入/HOME；保存每只原寄存器、截图与机械照片 |
| 5 · 离线台账 | 开发电脑运行下列validate命令；如已有本机runtime校准文件，按docs09只读review与provenance | 空白表应BLOCKED；有效表PASS仅数据一致；方向/来源缺失不得验收 | 不改设备；保存退出码/JSON/输入hash；逐只补真实证据，不拷模拟夹具 |
| 6 · IMU文档补齐 | 核对实物PCB/插座，取得厂家具体VCC范围、固件身份和数据年龄合同；当前仅离线requests/demo | 文档现在未提供这些，保持BLOCKED；不得接电池母线 | 不上电；保存厂家原文和版本，再按docs08单IMU只读台架流程审查 |

步骤3，在 **Radxa SSH**：

```bash
uname -m
cat /etc/os-release
uname -a
lsblk -o NAME,SIZE,TYPE,MOUNTPOINTS
cat /proc/cmdline
systemctl --failed --no-pager
```

步骤5，在 **开发电脑仓库根目录**（沿用已有S0–S2工具）：

```bash
mkdir -p local
cp -n templates/hd1910_inventory.csv local/hd1910_inventory.csv
cp -n templates/hd1910_mapping.json local/hd1910_mapping.json
# 填入真实只读/机械证据；此输出目录必须尚不存在：
python3 scripts/validate_servos.py local/hd1910_inventory.csv \
  --mapping local/hd1910_mapping.json --output .evidence/my-s2-readback-01
python3 scripts/imu_protocol.py --requests
python3 scripts/imu_protocol.py --demo
```

软件预期requests输出文档PING/READ/SYNC_READ帧，demo明确SYNTHETIC。不是发送到硬件的命令。不要把FD截图复制到公开Git；私有原件放`.evidence/`/`local/`，人工脱敏后摘要按[现场入口](../records/field/README.md)交接。每阶段记录具体命令、退出码、异常、停止动作、恢复状态与hash，不以“已完成教程”代替测量通过。
