# 09 · HD-1910-C001：已经按 2048 中位校准，该怎么复核？

**本页默认你已用 FE-URT2-C001 对若干舵机完成 ID/中位设置；现在不建议继续写校准命令。**先分清三个容易混淆的“0”。

## 三个不同概念

1. **物理参考零位**：按模型定义的机械基准。对腿部是伸直、脚掌放平等参考几何（各关节的转轴/轴向仍要对齐）；是能拍照、测角度的物理状态。
2. **HD1910 编码器读数 `2048`**：4096 步一圈时的计数中点。FD 中位校准功能通常把**执行操作时的当前轴位置**设置成此读数，并可能写入非易失标定；如果操作时关节姿态不对，写入值仍是 2048、却不是正确几何零位。
3. **训练 HOME**：Policy 在默认站立姿势下每个关节的角度。官方示例中左右髋 pitch 约 ±26.2°、踝约 ∓26°、颈/头 pitch 约 +20°，因此 **HOME 不等于所有舵机 2048**。

读数在确定映射后可近似按下式换算（未考虑 firmware 方向标志、raw 环绕、减速方向、偏置）：

```text
joint_angle_deg ≈ (raw - zero_raw) * direction * 360 / 4096
假设 zero_raw = 2048；direction 必须根据各关节实际安装 +1/-1 确认。
```

这是**只读解码公式**，不是发送动作的命令。如果用错误的 direction/机械限位生成写入值，可能使腿部撞壳。

## 复核流程（Windows FD + FE-URT2）

### Z0：准备

- 仅连接单只舵机，供电/极性与端子已经在之前成功的台架配置下验证；换线先断电、先量电压。
- USB 调试板/供电的接入方式**按该型号手册**；如调试器可从 USB 提供逻辑/空载供电，也不能据此保证带载电流足够。
- 舵机 torque OFF，机械联动不可造成意外转动；已装在机器内部且不可安全摆正的关节，不要强掰、拆保护壳或强行推进。

### Z1：记录到底写过什么

在 FD 软件中，选择 COM → 正确波特率 → `搜索` → 点击当前唯一 ID，**只读取**：

```text
实际关节标签、当前 ID、firmware、模式、raw 位置
中位校准前后的实物角度（能否回忆/照片）
断电重新连接后的 raw 读数
是否使用过“中位校准”“位置校准”“写 2048 目标”等不同按钮
```

这三个按钮的语义不一定相同：**设置目标位置 2048** 会要求电机移动；**位置中位校准** 可能修改非易失偏移。必须从 FD 的实际操作名称和固件版本判断，不能根据“我点了 2048”猜其性质。

### Z2：比对机械姿态（不主动动）

在已断电并确认可安全轻微手动移动、扭矩 OFF 的条件下，观察你进行中位操作时：

- 腿是机械零位的**自然直立参考**，还是折叠/躺着？
- 颈、头的 yaw/roll/pitch 是否在设计参考水平和朝前位置？
- 舵盘安装齿位是否已经调整，结构件是否先碰撞/线束是否拉紧？
- 左右镜像是否一致？端点夹角是否与物理设计允许值吻合？

如果**确实是在参考直立几何零位位置校准**，2048 作为基线合理；但仍需确认软件方向、各关节范围和零点重复性。如果是在未知/折叠姿态直接一键“中位校准”，应标记 `CALIBRATION_UNVERIFIED`，下一阶段按官方模型/已知机械治具重新标定，不能宣称 PASS。

### Z3：建立可追溯台账

在开发电脑的 Linux/WSL 工作区运行：

```bash
mkdir -p local
cp -n templates/hd1910_inventory.csv local/hd1910_inventory.csv
cp -n templates/hd1910_mapping.json local/hd1910_mapping.json
python3 scripts/validate_servos.py local/hd1910_inventory.csv --mapping local/hd1910_mapping.json --output .evidence/servo-zero-review
```

这时用新目录保留旧记录。空白台账得到 BLOCKED **是正常的**。尽可能填写已经真实只读的 ID、mode、raw、`encoder_zero_raw`（固件如果无法直接只读零位，就填 UNKNOWN，不要把当前位置当零位）、物理参考的照片编号。不要从模拟测试文件复制 ID/温度数值冒充实机证据。

### Z4：什么时候才允许重做中位校准？

仅在准确了解你所用 FE-URT2、HD1910 固件及 FD 操作语义、已安全建立机械参考姿态、已只读备份全部校准寄存器、能够单个关节低速限幅和物理急停时，才进入专门的**现场人工标定**。如果对“重校会让关节瞬间转动吗”尚无答案，停止并咨询提供设备/软件者。

参考：fanhao375 [HD1910 零位与 HOME 记录](https://github.com/fanhao375/microduck-replica/blob/master/调试记录.md#第-9-步--装机归零试行程)；其“官方折叠”标定目标是**另一套机械与调试台版本**的案例，不能不经核对直接复写到你的设备。

## 判定与恢复

- **PASS（只读链路）**：每只 ID 唯一、断电重连可重复查询，有设备日志。
- **PASS（几何零位）**：每个关节都有姿态/测量对照与软件映射确认，这需要后续人工证据，不靠“2048”一值。
- **BLOCKED**：缺失实物参考姿态、寄存器映射或方向。记录当前状态，不要写新的零位。
- **FAIL**：坐标变号、转角冲突或异常运动。立刻撤电，恢复已保存校准值及安全机械姿态，查原因后才重新启用。

**不要通过不断重新校准让数值显示 2048；那会掩盖机械基准错误。**

## 固定训练/运行时映射合同与防串机检查

来源固定于 [上游审查清单](../upstreams/review-2026-10-14.json)：官方 RL `b02fdea` 的 `robot_groundcontact_rollers.xml` actuator 顺序及 `microduck_constants.py` HOME；kissqy `7a52d29` 的 `model.rs` / `feetech.rs` / `feetech_commissioning.rs`；fanhao `5397eb1` 的调试记录。完整轴向、来源 SHA 和未确认的本机方向见 [机器可读参考](../hardware/hd1910-contract.json)，**这不是本机 mapping/calibration**。

| Action | runtime 槽 | 设计 ID | 关节 | 默认 HOME rad | 本机 direction/zero |
|---|---|---|---|---|---|
| 0 | 0 | 20 | left_hip_yaw | 0 | UNKNOWN |
| 1 | 1 | 21 | left_hip_roll | -0.0873 | UNKNOWN |
| 2 | 2 | 22 | left_hip_pitch | -0.4579 | UNKNOWN |
| 3 | 3 | 23 | left_knee | -0.0049 | UNKNOWN |
| 4 | 4 | 24 | left_ankle | +0.453 | UNKNOWN |
| 5 | 5 | 30 | neck_pitch | +0.3491 | UNKNOWN |
| 6 | 6 | 31 | head_pitch | +0.3491 | UNKNOWN |
| 7 | 7 | 32 | head_yaw | 0 | UNKNOWN |
| 8 | 8 | 33 | head_roll | 0 | UNKNOWN |
| excluded | 9 | 34 | mouth | 0（非 Policy） | UNKNOWN |
| 9 | 10 | 10 | right_hip_yaw | 0 | UNKNOWN |
| 10 | 11 | 11 | right_hip_roll | +0.0873 | UNKNOWN |
| 11 | 12 | 12 | right_hip_pitch | +0.4579 | UNKNOWN |
| 12 | 13 | 13 | right_knee | +0.0049 | UNKNOWN |
| 13 | 14 | 14 | right_ankle | -0.453 | UNKNOWN |

14 Action 跳过 mouth 槽9，不得将右腿从槽9直接排列。Policy 的最终 HOME 由其 deployment contract 提供，上表只是源码默认；动态/自训练模型不能靠此表强行改 HOME。模型轴正方向遵循 MJCF 局部坐标右手规则，本机编码器方向取决于机械装配及固件方向参数，每个关节必须独立核对。

kissqy 公式与本页一致，**无 raw 自动最短路径绕回**；限位须在0..4095内，不能绕机械硬挡。上游 `model.rs` 还有 XL330 EEPROM / knee −512 常量，但飞特路径使用自己的校准和 HD1910 寄存器；不可照抄到 HD1910 EEPROM。软件 `zero_raw` 与FD写入的硬件偏移是两层，重复补偿会造成错误。

fanhao 最初使用设计 ID 表；后续把嘴舵机替换左髋并用 mouth ID29，14关节记录明确排除嘴。其样机“全部 zero2048、direction−1”是那套装配的记录，**不能作为本机15/15验收**。kissqy 中控文档明确 bundle 来源 `duck-10e4`，可能恢复全部direction−1及ID30=2526/31=2228/33=1599；旧R1又有另一批示例值。不能只拦三项数值，必须拦来源不符的整个文件。

持久化：默认文件 `/etc/robot/feetech-ft5/hd1910-calibration.toml`，可被 `bus.feetech_calibration` 改路径；commissioning 保存会生成 `.previous.toml`、`.saved.toml`，临时文件写入、fsync、rename 后生效。该文件是主机 TOML，不是 EEPROM 备份，也没有可靠本机身份绑定。安装/恢复脚本必须另审，不能因已有 `calibrated=true` 就信任来源。

新增只读检查命令（开发电脑，JSON 支持Python3.10+，TOML需3.11+）：

```bash
python3 scripts/review_calibration.py local/hd1910-calibration.toml \
  --provenance local/calibration-provenance.json --robot-id YOUR_LOCAL_ROBOT_LABEL
```

前提：拿到本机**只读复制**的实际生效文件、15只台账和机械证据；不要执行 runtime commissioning/restore/HOME。provenance JSON 至少包含 `robot_id`（自选本机标签，不用别人标签）、`calibration_sha256`（实际文件的 `sha256sum`）、`source="local-readback"`、`evidence_ref`（自有逐关节证据位置）。不生成假的 provenance 消除 BLOCKED。

预期：来源/文件hash一致、15关节顺序/设计ID、有限单位mount、合法零位/±1方向/限位及默认HOME、`motion_enabled=false`；PASS只代表离线一致，不授权运动。更改设计ID须另审映射合同，脚本当前保守拒绝。异常 exit2=BLOCKED，格式错误 exit1=FAIL；保存JSON输出，停止安装/写入/HOME，恢复方法是保留原文件与断电台架，不把他人文件“恢复”进去。软件 `.saved` 文件与15只寄存器原值都分别保存；后续有许可的校准写入才讨论恢复。本轮不会自动写任何一层校准。
