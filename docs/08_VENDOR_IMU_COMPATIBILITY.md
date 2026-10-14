# 08 · 购买的第三方 ID200 IMU：协议对照与只读验收

**来源**：用户提供的《MicroDuck IMU 舵机总线通信协议》v1.2（2026-09-28）截图及本轮新增 QinmoTech 固定源原文（见末节），尚未收到真实 IMU PCB 的正反面、固件版本和电压额定值。它不是自动等同于 kissqy FT6 固件。

## 已知合同和必须核对的差异

| 项目 | 购买文档 | kissqy FT6 运行时 | 判断 |
|---|---|---|---|
| 半双工 TTL | 1Mbps、8N1 | 飞特串口 | 传输层似乎一致，待台架实测 |
| ID | 200（C8） | 200 | 匹配 |
| FEETECH 快速读取 | 地址 56 长 15 | `SYNC_ADDRESS=56`, `SYNC_LENGTH=15` | 长度匹配 |
| 字节 0–5 | XYZ 角速度 `int16 LE` | 作为核心 12 字节解码 | **比例待核对** |
| 字节 6–11 | XYZ 四元数 `binary16 LE`，W 从 `sqrt(max(0,1-X²-Y²-Z²))` 恢复 | 同类核心 12 字节 | 帧一致性待量测 |
| 字节 12 | u8 采样序号 | u8 采样序号（回绕允许） | 大体匹配 |
| 字节 13 | 状态；原文bit0=未就绪，bit1–7保留 | bit0=未就绪、bit1=过期、bit2=错误、bit3=读取节奏；保留高位必须为 0 | **与FT6年龄/错误状态合同不等价** |
| 字节 14 | 保留=0 | 必须为 0 | 匹配 |
| 身份读取 | **截图未列出** | 读 ID200 地址 0 长 5，必须是 `06 00 00 00 F2` | **强制阻塞项** |
| 角速度量纲 | `deg/s = raw/16.4` | kissqy `SflpDecoder` 用 `raw×0.0175°/s` | **不相同**，需核对实测和代码路径 |
| 设备电源 | **未给** | 取舵机母线 | **必须先问卖家输入 VCC 额定范围** |

换算比例相差约 `(1/16.4)/0.0175 = 3.4843` 倍。这不是可忽略的浮点误差。即使 ID、帧头和长度兼容，直接将角速度数据送进未经适配的推理输入也可能导致跌倒。不要通过关掉 IMU freshness/identity 检查“让它工作”。

源码交叉核对：
- [kissqy FT6 Fast Sync 源码](https://github.com/kissqy/Microduck-kissqy/blob/main/microduck-hd1910/firmware/duck-control/src/feetech.rs)
- [kissqy FT6 IMU 说明](https://github.com/kissqy/Microduck-kissqy/blob/main/microduck-hd1910/firmware/firmware/imu-source/README_FT6_SYNC15.md)
- [kissqy IMU 解码器](https://github.com/kissqy/Microduck-kissqy/blob/main/microduck-hd1910/firmware/duck-control/src/imu.rs)

## 1. 不连硬件，先在开发电脑验证文档帧

在本仓库根目录执行：

```bash
python3 scripts/imu_protocol.py --requests
python3 scripts/imu_protocol.py --demo
python3 -m unittest discover -s tests -v
```

脚本**只生成文档所示的飞特 Ping / Read 请求并解析合成的回复**，无串口接口，也不向硬件发送数据。合成样例只能验证 parser 与合同，不代表收到 IMU 真数据。输出包含身份签名与角速度比例待测提示。

### 文档的飞特协议示例

```text
PING ID200:
TX FF FF C8 02 01 34
RX FF FF C8 02 00 35

READ address 56, 15 bytes:
TX FF FF C8 04 02 38 0F EA
RX FF FF C8 11 00 <15 bytes> CHECKSUM

SYNC_READ address 56, length 15, ID 200:
TX FF FF FE 05 82 38 0F C8 6B
```

注：`FF FF FE ...` 里的 `FE` 为广播 ID；`SYNC_READ` 回复在多设备情况下有严格时序，不能仅用单设备 Ping 成功断定 50Hz 周期稳定。

## 2. 现场台架验收（严格依赖实物）

1. **必须先拿到卖家 IMU 的真实供电允许范围和实物 PCB 针脚端视图**；文档只写 `DATA/VCC/GND`，没有标出允许的 VCC。不要直接插在接近 8.4V 的 HAT 舵机母线上。
2. 确认 IMU 的双 3P 口为并联；**两个口的 VCC 直接相连，不要接两套不同电源**；三个线的极性用断电通断测量且核对实际模组丝印。不要只按导线颜色或截图上的“从左到右”。
3. 用稳定合规的限流电源、单独的半双工适配器、共地，仅连接 IMU 一块设备。先由有能力的操作者在断电时接线，通电后只执行 Ping 与只读（可由飞特 FD 软件完成）。不接 15 颗舵机，不运行 Policy，不写 IMU 固件。
4. 读取 **ID200 地址 0 长 5 的身份数据**，核对是否 `06 00 00 00 F2`。若不一致，则 kissqy FT6 可能拒绝此 IMU；不要伪造固件身份。
5. 多次读取地址 56 长 15 的原始返回帧（建议至少 100 帧，足够评估序号、状态 bit 和 checksum），保存 HEX、时间戳、状态异常。若状态位0提示未就绪，**不能将四元数纳入控制**。
6. 在有安全固定姿态的情况下，读取静止、前后左右倾斜与缓慢已知角度转动的数据：检查 quaternions、gyro 符号/幅值、序号递增/回绕和数据新鲜度。已知角度转动只可验证近似比例，精确比例需已知角速度测量设备。
7. 根据真实身份与字段一致性，由 Coding Agent **静态比较**现有 kissqy FT6 与第三方协议，必要时设计显式“vendor IMU profile”，保留原来的 FT6 身份与 freshness 安全检查，不做隐藏兜底。真正接入须另行测试。

## 3. 判定

- **协议文档静态核查 PASS**：离线脚本测试与 checksum/帧结构正确。
- **电气 BLOCKED**：真实 IMU 额定 VCC、引脚和限流供电未核。
- **FT6 合同 BLOCKED**：0–4 身份、完整状态语义、gyro 比例未验证。
- **IMU 现场 PASS**：只读日志、状态/数据、姿态方向与应用层比例都符合所选 runtime 的约定，才能进入 S3/S5 的进一步联合测试。

未取得电气和身份通过记录前，**严禁把这块第三方 IMU 与完整 HD1910 总线一起接入并直接执行站立 Policy**。

## 本轮固定源码结论与最小适配设计（2026-10-14）

用户补充的 [QinmoTech PROTOCOL v1.2](https://gitee.com/QinmoTech/IMU-DXL/blob/4644a9d19e07ac47f2c145c5e064c96683a5450b/docs/PROTOCOL.md) 已由 Git 获取，固定 SHA `4644a9d19e07ac47f2c145c5e064c96683a5450b`；网站读取失败不影响 Git 原文审查。文件/图像 hash 在 [审查源清单](../upstreams/review-2026-10-14.json)，作为第八个上游加入版本锁。

更正前述“截图未完全定义”：在线原文明确 **bit1–7 为保留**，仅 bit0 表示尚未解算；未承诺 30ms 发送时年龄保证。文档仍只说“遵循产品标注”，**没有 VCC 数值**；未定义飞特 address0/5 身份签名。Dynamixel PING 的 1030/XM430-W210 只是工具发现标识，不能替代 FT6 `06 00 00 00 F2`。自动协议选择在首个有效帧发生，通信停 20s 后重置；不交错发送两种协议探测。

Qinmo 文档轴：从元件面看，+X 沿长边向下，+Y 向右，+Z 朝观察者，右手正旋转。传输 XYZ binary16，恢复 W≥0 后归一化；接口采用 WXYZ 表达。绝对旋转的 body→world/world→body 约定仍须通过倾斜/已知转动实测，六轴 yaw 长期会漂移。不要照搬 kissqy mount。

本轮逐行核对固定 [kissqy feetech.rs](https://github.com/kissqy/Microduck-kissqy/blob/7a52d297a9adfe6d2315481953dc64060252d142/microduck-hd1910/firmware/duck-control/src/feetech.rs) 与 [imu.rs](https://github.com/kissqy/Microduck-kissqy/blob/7a52d297a9adfe6d2315481953dc64060252d142/microduck-hd1910/firmware/duck-control/src/imu.rs)：

- FT6 ready 是 `(status & 0x07)==0`，不仅是 bit0；bit2 同样拒绝，bit3 仅节奏信息，bit4–7 与 reserved14 必须为0。
- FT6 声明年龄上界30ms，与整轮通信耗时合计≤50ms；连续3次计数不变拒绝。计数变化/255→0 只证明可能有更新，不能替代传感器缓存年龄。
- SflpDecoder gyro 为 `raw×0.0175×π/180 rad/s`；vendor 应为 `raw/16.4×π/180`，直接使用现有 runtime 的量纲**不兼容**。这是静态合同差异，不是假设实物已返回该格式。
- 上游拒绝 all-zero XYZ 四元数字节作为未初始化，等待25个有效样本；平方和≤1.02 后恢复W、单位化。默认 mount 是绕Y +90°，gyro `trunk=[raw_z,raw_y,-raw_x]`，quat 使用 `[w,x,y,z] × mount⁻¹`，然后投影重力/三点中值。该 mount 不能从购买文档自动推出。

本地 `read15(data, profile="ft6"|"vendor-v1.2")` 只做**离线解码**，输出两种比例对照、选定 profile 的 rad/s、XY ZW/WXYZ 和年龄是否已知。`StatusStream` 支持保存日志的分片、多帧、坏 checksum 后重同步；不打开串口。`SampleGuard` 固定身份、就绪、重复计数、时间单调/间隔、通信耗时、非零四元数与25样本门槛；任何错误清除就绪累积。vendor profile 拒绝未定义状态位，**没有年龄依据便不能 accept**。参数 `verified_vendor_age_ms` 仅用于离线模拟经独立验证的年龄输入；主机接收时间不构成该证据，不允许现场填0绕过。

最小 runtime 适配待实施：增加显式 profile 配置（默认FT6；未知值拒绝启动）；把 gyro scale、允许状态位、身份期望、年龄来源与 mount 分离。FT6 身份与30/50ms合同原样保留；vendor 必须在自有真实固件签名确认后固定独立身份，并提供传感器更新计数/缓存年龄的可信来源（优先厂商提供寄存器或固件合同）。未提供前 vendor 只读诊断，不能上力。使用单位 mount 和归一化 WXYZ，保留异常四元数、25样本、重复计数与现有保护。部署前另做 runtime 单元/台架/50Hz 故障注入，本轮不改上游 runtime、不安装镜像或固件。

**下一步验收条件**：先取得具体 VCC 范围与实物端视图；符合条件后单 IMU 只读 PING、0/5、56/15，不用商家调试台的自动动作替代原始帧。保存100+帧与时间戳、四方向/已知转动原始数据；若身份不同、状态保留位不为0、缓存年龄未知或角速度比例/符号不符，停止控制路径，断电恢复独立台架。参考上一节现场流程，未取得数值 VCC 前不执行此上电步骤。
