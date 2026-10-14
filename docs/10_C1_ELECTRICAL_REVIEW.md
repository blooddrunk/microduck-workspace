# 10 · ASE01187-C1 电气审查与断电验收表

审查日期 2026-10-14；**所有实物针脚、电压、反灌均未验收**。只固定 C1 历史产物，没有使用当前 D1 KiCad 工程推导 C1 接线。

来源：[官方固定 commit](https://github.com/pollen-robotics/elec_RPI_Robot_HAT/tree/4478fdfb0d6c6766110776bfed44316884e94e52/production/_old)。已获取 C1 SCH、BOM、POS、PCB PDF、Gerber ZIP、STEP ZIP 和原许可证，保存于 [reference/c1](../hardware/reference/c1/)，原始字节 SHA256 见 [manifest](../hardware/reference/manifest.json)。注意 **C1 SCH 文件的各页标题栏仍是 B1/2026-05-06**，第一页含 C1 修订记录；PCB PDF 标 C1/2026-07-08。此内部版本不一致需保留，不能把文件名或标签视为逐针验收。PCB ZIP 是生产数据，不等于可编辑的 C1 KiCad 源文件；本次没有找到独立 C1 KiCad 源快照。

Radxa 来源：[V1.12 厂家原理图](https://dl2.radxa.com/zero3/docs/hw/3w/radxa_zero_3w_v1.12_schematic.pdf)，下载原件与 SHA 固定在同一 manifest。HAT 页码 2/3/4 分别为排母、电源、舵机接口；Radxa 页码 20/22 分别为排针、5V 输入。

## 候选排针对照：按物理针号，不按 Raspberry Pi GPIO 名

| ZERO CON1 / HAT J4 同号针 | Radxa V1.12 网络 | C1 HAT 网络/用途 | 实物状态 |
|---|---|---|---|
| 1、17 | VCC3V3_SYS | +3V3 | 待万用表/方向确认 |
| 2、4 | +5V_INPUT | +5V，HAT 向主控供电 | 待测 5V；不能接电池电压 |
| 6、9、14、20、25、30、34、39 | GND | GND | 待通断确认 |
| 8 | UART2_TX | IO_14 / DynUART_Tx，自动方向 | 待测；需匹配 UART2 overlay |
| 10 | UART2_RX | IO_15 / DynUART_Rx | 待测；不能被 console 占用 |
| 3、5 | GPIO1_A0/A1_3V3 | IO_02/03，板载 IMU/音频 I2C | GPIO 功能及驱动尚未验收 |
| 7、29 | GPIO3_C4/B3_3V3 | IO_04/05，J6 默认 I2C3 | Pi 总线名不等于 RK3566 总线名 |
| 19、23 | GPIO4_C3/C2_3V3 | IO_10/11，J8 | 未配置，不接扩展设备 |
| 21、24 | GPIO4_C5/C6_3V3 | IO_09/08，J7 | 同上 |
| 27、28 | I2C4_SDA/SCL_M0，经 R32/R39 | ID_SD/SC；J6 可选非默认 | 不因物理兼容而自动启用 |
| 31 | GPIO3_B4_3V3 | IO_06，电源关断检测 | 软件未验收 |
| 15 | GPIO3_B0_3V3 | IO_22，IMU 中断 | 软件未验收 |
| 12、35、38、40 | GPIO3_A3/A4/A6/A5_3V3 | IO_18/19/20/21，音频 | 此轮不用 |
| 11、13、16、18、22、26、32、33、36、37 | 见 Radxa p20 | C1 p2 相应 GPIO，非本轮总线用途 | 不做飞线、不输出“可用”结论 |

40Pin 装配必须核对 pin1 标记及面对面镜像，排母背面观察与排针正面左右相反。Radxa 图 CON1 符号值为 `2X20-F-2MM`，不能以这个库符号保证实物机械间距；实际排针/排母间距、定位、元件净空和支撑柱都待量。整板叠接前查全部非电源 GPIO 的冲突，不能只核对 UART 两针。

## 舵机口与电源路径

| C1 p4 接口针号 | 候选网络 | 测量/验收位置 |
|---|---|---|
| J13/J14 pin1 | GND | 到 J4 任一 GND 通断 |
| J13/J14 pin2 | +BATT，直通舵机电压 | 两口 pin2、U9 IN 通断；与 J4 5V 不能直通 |
| J13/J14 pin3 | TTL DATA | 两口 pin3 通断；经 TH1 100Ω、R33 150Ω 到缓冲器；不是 UART_TX 直连 |
| J3/J11 pin1 | GND | 到 J4 GND |
| J3/J11 pin2 | RS485 B（U8 pin7） | 差分口；不能接 TTL DATA |
| J3/J11 pin3 | RS485 A（U8 pin6） | 同上 |
| J3/J11 pin4 | +BATT | 电池母线；禁止对照 3P 左右位置硬插 |
| J1 Speak | 音频功放输出 | 绝非电池输入，两个端子也不能视为 GND/VCC |

**端视图约定**：源图定义的是编号，不是照片左/右。只有找到 PCB pad1（方焊盘/标记）并断电通断确认，才可在“朝插座开口、锁扣朝上”的实物照片标记 `1=GND、2=VCC、3=DATA`；从线束背面观察必须镜像。当前不能给无照片基准的左到右接线指令。第三方 IMU 文档的 DATA/VCC/GND 观察方向是文字正向，不能直接套到 HAT 插座端视图。

C1 p3：`+BATT → U9 AP63205 IN/EN → SW/L4（6.8µH，2A标注）→ C21/C22 → Q2 + U10 LM5050-1 理想二极管 → +5V → J4 2/4`。BOM 应与 U9/U10/Q2/L4 实物相符。官方 README 的 5–28V 是 HAT 声明，图上 24V/7S 是设计备注，**都不是 HD1910 或第三方 IMU 的供电许可**。2A 标注也不代表 ZERO + 所有外围的实测余量；Radxa 当前建议 ≥15W，HAT 供电裕量需负载/纹波测试。

电池候选接法：电池座已确认的 `+ → 保险/开关 → 指定电机口 +BATT`，`− → GND`；专用线束必须保留 DATA 无接触，不接 Speak，不把电池输出接 J4 2/4。**本轮仅审查，不执行这个供电动作**；初测用已确认限流的可调电源，不用 F550。电池座极性、满充输出、保险和接头额定未核，保持 BLOCKED。

## 反灌结论及最小测量卡

Radxa p20 的 header 2/4 与 p22 USB-C J2 VBUS 共用 **+5V_INPUT**。因此候选路径 `HAT +5V → header 2/4 → USB-C VBUS` **没有画出的隔离器件**。C1 理想二极管在 buck 输出侧，不能隔离 Radxa header 与 USB 电源。禁止双供电；不能因 C1 修过 MOS 方向便称“USB 安全”。断电二极管档不能证明带电动态隔离。

1. **前提**：HAT 与 ZERO 完全分离，所有 USB、电池、电源及外设拔下，电容放电；禁止带电通断档。先给两板和线束拍方向/pin1 照片。
2. **具体测点**：按上表测 GND、+BATT、5V 各组通断；分别记录 +BATT↔5V、5V↔GND、+BATT↔GND 双向电阻/二极管档。ZERO 单独测 header2/4↔USB J2 VBUS，仅使用带测点的断电 USB breakout，不用表笔挤 USB-C 内部触点。
3. **预期**：同网络低阻；不同电源网络不可永久近零。充电电容导致阻值上升不等于短路；读数不明也不判 PASS。
4. **异常与停止**：编号无法确认、永久近零、母线与 DATA 短接、与图不符，都停止接线，保存照片和两个表笔位置，不试插/试电。
5. **恢复**：保持全断电和板卡分离。不要用重刷系统或反复通电解决电气问题。
6. **证据**：表型号/档位、观察方向、pin1、每对测点读数与时间，放 `.evidence/`；脱敏摘要交 `records/field/s3-hat-power/`。此测量卡完成后仍需另行审核限流空载 5V 与负载余量，才进入供电验收。
