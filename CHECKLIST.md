# 实验 Checklist（证据优先）

状态含义：`[x]` = 已证实（附证据链接）；`[ ]` = 未完成；`[豁免]` = 2026-10-27 决定不再补做（见下）。
原始诊断/照片放 Git 忽略的 `.evidence/`、`local/`；**审查脱敏后**的摘要进 [records/field/](records/field/README.md)。
本仓库公开：凭据、WiFi 密码、`.env`、私钥、设备标识不得入库。

> **2026-10-27 门禁豁免**：整机已由团队线下完成装配/标定/通电并长期运行，原 S0–S3 的形式化证据
> （断电测量、单舵机台架读回、备用卡、IMU 四方向实测等）不再补做。新证据基线 =
> [duck/snapshots/ 实况快照](duck/snapshots/2026-10-27_runtime/README.md)（只读巡检）。
> **豁免不适用于换件/换镜像/重新接线**——那属于新的电气事件，对应检查重新生效。

## 2026-10-27 实况基线（已证实）

- [x] 整机运行：robotd/padd/tofd/btd/configd/gamesir-xboxd/powerlog 全部 active，`systemctl --failed` 为空（重启后复查）。
- [x] 15 关节标定完成：`calibrated = true` × 15，`motion_enabled = true`，IMU `imu_mount_verified = true`；含 .previous/.saved 历史档。→ [calibration 快照](duck/snapshots/2026-10-27_runtime/calibration/)
- [x] 6 个自训策略已部署（walk/sitstand/ground_pick/kick×2/roulade，2026-10-01 training-console 训练），provenance（task/checkpoint/sha256）已存档。→ [models 快照](duck/snapshots/2026-10-27_runtime/models/)
- [x] robotd 运行时配置快照（policy 路径/增益/skill 表/安全项）已存档。→ [etc-robot 快照](duck/snapshots/2026-10-27_runtime/etc-robot/)
- [x] 网络身份确认：IP 192.168.8.161、MAC cc:c8:37:3d:3c:93、WiFi GL-MT3600BE-5e4；异地通道（跳板/隧道）可用。→ [duck/network.md](duck/network.md)
- [x] 语音控制在跑：`voice_chat.py --wake-keep 20`（讯飞 ASR + 大模型识别 + 意图解析）。
- [x] 权重备份：21 个 onnx（43MB）拉到本机 `local/duck-policies-20261027/`（不入库）。
- [x] 已知问题登记：mediad 崩溃循环（重启前 NRestarts=497，重启后 17min +123）；低电保护与 limp_fall 关闭。

## 运维加固待办（P0/P1，详见[手册 17](docs/manual/17-team-workflow.md)）

- [ ] P0 mediad 崩溃循环：现场决策 disable 或定位修复（疑与语音进程抢音频相关；保留 8080 网页中控的需求要一并权衡）
- [ ] P0 鸭子本体安装 Tailscale（装完异地直达，摆脱 GL 路由器中继）
- [ ] P0 板上无版本代码收编：`~/zhangtong/duck-voice`、`~/voice/microduck-voice`、`~/shishaodong/ultralytics-learn` 正本迁入本仓库 `apps/`（注意 `.env` 密钥不入库）
- [ ] P0 评审并决定低电保护：`battery_empty_shutdown` / `limp_fall` 是否启用；结合 powerlog 掉电数据分析
- [ ] P1 语音进程 systemd 化：评审 `duck-voice.service` 后 enable，配 `Restart=on-failure`
- [ ] P1 SSH 收敛纯密钥：各队员 `setup-key-duck.sh` 装钥匙，齐后关密码登录（鸭子与 GL 路由器）；路由器管理密码轮换
- [ ] P1 journald 限容（`SystemMaxUse=200M`）与板上 5.7G 数据集外迁
- [ ] P1 每次重标定/换策略后 `pull-duck.sh` 重新存档（写进操作习惯）

## 语音/本地模型待办（P2）

- [ ] 本地 ASR 替代讯飞云端：sherpa-onnx int8 流式模型上板验证（内存/延迟/识别率），安装脚本走 `scripts/duck/remote/` 评审流程
- [ ] 唤醒词本地化（openWakeWord / sherpa-onnx KWS）替代 `--wake-keep` 窗口逻辑
- [ ] intent 规则库扩充与回归样例集
- [ ] 可选：本地 TTS（piper 中文）；板上不跑 LLM，复杂意图留云端可选项

## S4 自有训练线（继续有效）

- [x] S4-2 数值部分：ONNX SHA256、float32 61→14 与 2 秒有限 CPU rollout 通过；静止姿态 8/8 FAIL（约 82° 倾倒）——记录在案，不是站立 PASS。
- [x] S4-6 CPU 部分：BAM M1–M6 原版注册键名错误复现、隔离 alias 可加载、CPU A/B 有限值；综合 PARTIAL。
- [ ] S4-0 完整预检复核（CUDA BLOCKED、GUI 环境线索未复核）。
- [ ] S4-3：真实 CUDA + 64 env × 5 iteration smoke（loss 有限、checkpoint 可读）。
- [ ] S4-4：完整长训 + TensorBoard 分项 + 回放/扰动评测。
- [ ] S4-5：checkpoint → 含 normalizer 的 ONNX、61→14、PT/ONNX 数值等价与语义验证。
- [ ] S9（本仓库管线）：自有 ONNX 按[手册 16 §5](docs/manual/16-web-and-policies.md) 上机流程完成一次部署→回滚演练。
- [ ] S8：任一自训策略的 sim-to-real 对照（轨迹/延迟/压降），一次只改一个变量。

## 历史门槛（S0–S3，2026-10-27 豁免）

以下各项**不再要求补证**；列在这里是为了换件/换镜像时知道哪些检查要重新生效：

- [豁免] S0 断电万用表测量（短路/极性/pin1）、供电路径图与保险丝确认。
- [豁免] S1 备用系统卡制作与回退演练（V1.12 引导方案见 [docs/11](docs/11_ZERO_V112_BOOT_REVIEW.md)）。
- [豁免] S2 单舵机台架逐只读回（FE-URT2 只读 15 ID 台账）；标定实际经整机完成并存档。
- [豁免] S3 pin-to-pin 对照、双电源反灌实测、IMU 四方向倾斜与静止偏置记录。
- 说明：换 HAT/换 IMU/换镜像/改供电拓扑时，上述对应项**重新变为必检**。

## 历史软件交付（保留勾选记录）

- [x] 2026-10-14 只读采集工具/台账模板/证据包格式（[记录](records/2026-10-14_s0-s2-automation.md)）。
- [x] 2026-10-14 C1 原理图审查、QinmoTech IMU 协议差异、15→14 训练合同、V1.12 引导回退（[记录](records/2026-10-14_s1-s3-review.md)）。
- [x] 2026-10-15 上游 8 源 SHA 锁定同步（[记录](records/2026-10-15_upstream-sync.md)）；2026-10-27 推进 5 个锁。
- [x] 2026-10-15/16 S4 BAM 评估与社区策略筛选（[S4 记录](records/field/s4-simulation/)）。
- [x] 2026-10-27 实况同步、运维工具集、手册与快照（[记录](records/2026-10-27_duck-sync-and-manuals.md)）。
