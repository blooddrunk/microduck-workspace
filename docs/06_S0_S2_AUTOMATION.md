# S0–S2 自动准备与现场验收卡

本页配合 [00 盘点](00_START_HERE.md)、[01 单板](01_BOARD_BOOT.md)、[02 单舵机](02_SERVO_IMU.md)。所有脚本只用 Python 3.10+ 标准库；不安装驱动，不打开 UART/I²C，不扫描总线，不写舵机寄存器，不操作服务。**S2 的本轮范围是逐只只读基线与配置准备；全总线连接/IMU 验收属于 S3/S5。**

## 原始采集与共享记录分层

执行前建议先读 [分阶段证据目录与交接流程](../records/field/README.md)。现有 `/.evidence/` 与 `/local/` **已经忽略 Git**，适合放从设备采集的完整原始数据；`records/field/` 只存**手工脱敏的审查小结**（公开仓库）。`diagnose_radxa.py`、`validate_servos.py` 和 `run_checks.py` 原有输出选项、禁止覆盖与只读边界不变。

在开发电脑可以预先创建 `.evidence/s1-radxa/`、`.evidence/s2-servos/`，把每次结果放在带日期的**全新** run-id 下。远端 Codex 无法从 Git 下载本地忽略的原始证据；提交 `records/field/s1-radxa/...` 的脱敏摘要或显式提供经过检查的附件后，才让 Agent 判断 S1 数据。

## 在开发电脑生成自己的空白记录

在 Linux/WSL 开发电脑、本仓库根目录运行：

```bash
mkdir -p local
cp -n templates/hd1910_inventory.csv local/hd1910_inventory.csv
cp -n templates/hd1910_mapping.json local/hd1910_mapping.json
python3 scripts/validate_servos.py local/hd1910_inventory.csv \
  --mapping local/hd1910_mapping.json --output .evidence/servo-first
```

预期：复制保留已有文件，空白表显示 `BLOCKED`、退出码 2；详情在 `raw/00.json` 的 validation.issues。每次 `--output` 必须使用**未存在的新目录**，例如 `servo-second`。已有目录报 FileExistsError 是防覆盖保护，应换目录；不要删除原证据。`local/` 和 `.evidence/` 均被忽略。

将 S01–S15 标签贴到真实舵机并拍照。模板不预设关节或 ID，不表示官方关节顺序。按实际装配图与**选定运行时的固定 SHA 配置**填独立 mapping：`physical_label`、`joint_name`、`planned_id`、`policy_index`。14 个策略槽必须恰为 0–13，另一只填字符串 `excluded`；只有合同确认后才决定哪只排除。未知保留 `UNKNOWN`，绝不借模拟夹具补值。旧 ID 与规划 ID 可以不同；工具不会执行迁移。

### 台账字段与单位

| 字段 | 来源与意义 |
|---|---|
| physical_label / joint_name | 实物照片标签 / 对应运行时关节名，均不可重复 |
| current_id / planned_id | 单只只读应答 ID / 人工批准的规划；全表重号 FAIL，包括未改的出厂重号；不代表应立即改 ID |
| firmware / mode / baud | 工具只读或型号/固件手册原始字符串、实际波特率；无查询能力则 UNKNOWN |
| position_raw / encoder_zero_raw | 原始位置 / 编码器零点寄存器原值；不能用反馈位置代替零点 |
| mechanical_reference | 机械参考姿态的照片或测量说明，独立于编码器数值 |
| training_home_rad | 训练合同 HOME，单位 rad、训练关节坐标；不是写入编码器的值 |
| direction | 训练正方向到舵机原始增量的符号 +1/-1，需实物证据 |
| joint_min_rad / joint_max_rad | **训练关节坐标**中的已确认安全边界，HOME 必须在内；不是原始寄存器端点 |
| voltage_v / temperature_c | 单只只读反馈，V / °C；没有可解释单位时保持 UNKNOWN |
| voltage_min_v / voltage_max_v / temperature_max_c | 精确型号/固件规格与实验停止标准；不得使用夹具里的示例阈值 |
| registers_raw | JSON 数组，每项包含 address、width_bytes、value、manual_ref；按手册宽度保存无符号原始位型，不作符号/角度解码 |
| evidence_ref | 原始截图/日志与测量附件位置；程序不认证附件真实性 |

CSV 的 `registers_raw` 必须按 CSV 规则转义 JSON 双引号；建议用 Python csv 模块生成或直接使用 JSON 数组输入。输入 JSON 与 CSV 使用相同字段；JSON 顶层须为 15 个对象的数组。寄存器地址不由脚本指定，只按确切固件手册填写。未建立寄存器定义、没有读出原值时保持空白，不能填写虚拟地址。

语法允许 unicast ID 0–253，**实际设备/固件可能要求更窄范围**；波特率、寄存器语义、模式含义需手册/运行时单独核对。静态验证不计算角度到 raw 的比例、环绕或偏置，不检查控制器实际采用 P/D，不生成部署配置。准备中的机械/方向未实测项目保持 BLOCKED，无需为了拿 PASS 越级运动。

退出码：0=静态 PASS，1=FAIL（表损坏/冲突），2=BLOCKED（未知值）。工具结果不勾硬件 Checklist。FAIL 时修正记录与来源；设备状态不明时停止供电、回到逐只只读，不批量改寄存器。

## 将只读脚本送到 Radxa

只允许已满足独立 USB-C 5V 启动前提、**不接 HAT/IMU/舵机/电池**的 Radxa。以下传输命令在 Linux/WSL 开发电脑仓库根目录运行；先将变量占位符换成自己已经核验主机指纹的 SSH 登录目标：

```bash
RADXA_TARGET='实际用户名@实际IP'
ssh "$RADXA_TARGET" 'mkdir -p ~/microduck-diagnostic/scripts'
scp scripts/evidence.py scripts/diagnose_radxa.py "$RADXA_TARGET":microduck-diagnostic/scripts/
git rev-parse HEAD
sha256sum scripts/evidence.py scripts/diagnose_radxa.py
```

预期：文件成功传输，开发电脑记录源码 commit 和两个文件完整 SHA256。这里只写用户目录；不覆盖板子的固件/系统配置。若 SSH/SCP 失败，检查同一局域网、IP 与 SSH 用户；主机密钥异常先核对板子与系统卡，不关闭校验。

在 **Radxa SSH 终端**运行：

```bash
cd ~/microduck-diagnostic
sha256sum scripts/evidence.py scripts/diagnose_radxa.py
python3 scripts/diagnose_radxa.py --output .evidence/s1-first --robotd
```

预期：板上文件 hash 与电脑逐字符一致；生成 `summary.json` 与 `raw/`。只复制脚本的目录没有本仓库 Git 元数据，commit 可能 UNKNOWN，或者检测到外层其它仓库；**板上报告里的 commit 不作为源码来源证明**，用电脑记录的 commit + 双端文件 hash 对齐。本工具同时保存脚本 hash。要记录整个目录的 commit，可在板上使用独立、干净的工作区克隆；不强制联网安装。

报告中的 PASS 只说明那项采集成功。启动 warning、无日志权限、systemd 不可用、robotd 未安装、设备节点缺失/进程可见性不足保留 BLOCKED；异常服务 FAIL。报告整体保留 hardware_acceptance BLOCKED，需要人工电气与启动健康验收。**不用 sudo 自动补采**；如必须读受限日志，先评估再由操作者针对具体只读命令补充证据。不要为“变绿”启用 UART overlay、改 stty 或运行 i2cdetect。

`device_occupancy` 是 `/proc/*/fd` 瞬间快照，只看到进程 PID；看不到内核驱动占用、U-Boot console，也不能认证引脚。结合 `/proc/cmdline`、所选镜像设备树与准确板型文档审查 UART；未知 pin/overlay 为 BLOCKED。robotd 只读 LoadState/ActiveState 等元数据，不读 Environment，不启动服务；存在或不运行都不能证明不会 torque-on。

## 人工验收卡（每项六个要素）

### H0 · 断电盘点与电气来源（S0）

1. **前提/工具**：电池、USB-C 与其它供电全部拔下，万用表、相机、准确 PCB Rev 原理图/型号手册；缺任何项 BLOCKED。
2. **操作/测点**：拍板正反面、丝印和接头端视图；逐只标签；画两条供电路径。按原理图标出的 GND/V+/DATA 和电源入口作断电通断/电阻检查，记录探针所在针脚与插头朝向。未知点标 BLOCKED，不猜测、不上电试探。
3. **预期/判定**：实际数量与 15 路规划吻合；测点/连通关系可与确切版本原理图逐项核对；没有未解释短路。电容充电造成的瞬时蜂鸣不直接判短路，需有经验的人复核，不能自定通用电阻阈值。
4. **失败停止/恢复**：保留断电；纠正标识/线束并重测，资料缺失时先取得原理图，不叠接 HAT。
5. **证据**：照片、Rev、资料链接/版本、测点对、测量数值、仪器与拓扑，敏感序列号遮挡。
6. **证明范围**：证明记录完整且断电连接与设计相符；不能证明稳压输出、负载稳定性、热安全或真机兼容。

### H1 · 主板独立启动（S1）

1. **前提/工具**：HAT/总线物理脱离，可信且已核验的镜像卡、合规 5V USB-C 电源、万用表与 SSH 电脑；刷卡前确认目标/备份。
2. **操作/测点**：按 01 教程刷卡校验、单路 USB-C 启动；只在厂家标明且可安全探测的 5V/GND 测点测供电，探头避免短接。没有安全测点/仪器则电压项 BLOCKED。采集诊断，观察启动期间重启/温升，再正常关机拔电。
3. **预期/判定**：文件 hash、板型和架构匹配；SSH 可重复连接，根文件系统可读；供电符合确切板型规格，异常服务/存储错误逐项解释，无持续异常重启或过热。单次日志不能证明长期稳定。
4. **失败停止/恢复**：异味/异常热直接拔电；正常软件故障先安全关机再断电，检查电源/卡；恢复原干净备份卡。无法 SSH 先检查路由器与镜像，不能猜密码/改 UART。
5. **证据**：镜像与源校验值、写后校验、开机照片、电源铭牌/测点值、源码 commit/hash、诊断原始包、关机状态。
6. **证明范围**：仅证明独立主板在记录条件下启动；不能证明 HAT 供电、串口接线或 HD1910/IMU 驱动。

### H2 · 一只舵机只读，逐只重复（S2）

1. **前提/工具**：H0 的接头和供电资料已核对，准确 FE-URT 型号手册、万用表、限流供电、Windows 飞特工具、无干涉固定台架。若无法确认连接会保持卸力或工具不会写参数，则不接电 BLOCKED。
2. **操作/测点**：全部断电接线；适配器不接舵机时按准确手册检查端子 V+/GND 电压与极性，读完断电再接唯一舵机；在 Windows 工具只读 Ping/信息/寄存器，记录参数。每次换线必须**断电再换**。若已装机械无法安全解除干涉，不强拆/强掰，暂停找有经验的人。
3. **预期/判定**：只有一个应答，标签/ID/固件模式可解释；电压与温度在所确认规格/停止标准内，多次读数可重复，无误动作；编码器/方向/机械未确认项仍 BLOCKED。
4. **失败停止/恢复**：误动、过热、供电掉压马上物理断电；冷却后按供电→GND/DATA→协议/COM/波特率排查。无应答保存失败日志，不恢复出厂、不写零点、不刷固件、不自动改 ID。
5. **证据**：接头测点照片/电压、真实型号、Windows 工具版本与只读界面截图、每只标签/原始寄存器值/时间/错误次数，CSV 或 JSON 与独立 mapping。
6. **证明范围**：证明该一只在该连接下的只读链路与参数基线；不能证明全总线稳定、机械方向/限位/标定、训练 HOME 可执行或走路安全。

## 自动验收与证据分享

在 **Linux/WSL 开发电脑、本仓库根目录**运行：

```bash
python3 scripts/run_checks.py --output .evidence/acceptance-first
```

预期：依次实际执行 workspace、unittest、七源 check、模拟表静态 PASS、未知模板 BLOCKED（预期退出 2）。汇总的 PASS 仅限上述软件检查。没有网络时 upstream BLOCKED，整体退出 2；其它实际失败退出 1。修复后用新目录重跑，不覆盖旧证据。上游有更新只报告漂移，另行审查；不自动替换环境。

每个包分为原始 stdout/stderr 和结构化摘要，附 UTC 时间、命令、起始源码 commit、dirty 状态、脚本 hash、每份原始输出 hash 与检测范围。**不会自动去敏**：原始 IP/MAC、用户名、CPU 序列号、日志中的 Wi-Fi 密码/令牌都可能敏感；先逐份检查，分享脱敏副本（重新计算 hash），保留本地原本，不提交整个目录。目录权限 0700、文件 0600 适用于 Linux 文件系统；外部同步/Windows ACL 需另查。

当前无实机、万用表的 Coding Agent 只能完成离线与远端版本检查。CUDA 训练/CPU 回放不属本轮验收；S0 尚未闭合、S1/S2 均没有硬件 PASS 时，不进入 S3/S5。
