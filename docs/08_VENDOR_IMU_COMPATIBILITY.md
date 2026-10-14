# 08 · 购买的第三方 ID200 IMU：协议对照与只读验收

**来源**：用户提供的《MicroDuck IMU 舵机总线通信协议》v1.2（2026-09-28）截图，尚未收到真实 IMU PCB 的正反面、固件版本和电压额定值。它不是自动等同于 kissqy FT6 固件。

## 已知合同和必须核对的差异

| 项目 | 购买文档 | kissqy FT6 运行时 | 判断 |
|---|---|---|---|
| 半双工 TTL | 1Mbps、8N1 | 飞特串口 | 传输层似乎一致，待台架实测 |
| ID | 200（C8） | 200 | 匹配 |
| FEETECH 快速读取 | 地址 56 长 15 | `SYNC_ADDRESS=56`, `SYNC_LENGTH=15` | 长度匹配 |
| 字节 0–5 | XYZ 角速度 `int16 LE` | 作为核心 12 字节解码 | **比例待核对** |
| 字节 6–11 | XYZ 四元数 `binary16 LE`，W 从 `sqrt(max(0,1-X²-Y²-Z²))` 恢复 | 同类核心 12 字节 | 帧一致性待量测 |
| 字节 12 | u8 采样序号 | u8 采样序号（回绕允许） | 大体匹配 |
| 字节 13 | 状态；截图只定义 bit0=未就绪 | bit0=未就绪、bit1=过期、bit3=读取节奏；保留高位必须为 0 | **状态位合同未完全证实** |
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
