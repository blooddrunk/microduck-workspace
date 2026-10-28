# 17 · 多人协作、仓库结构与优化加固清单

> 目标：多人同时在线开发时不互相踩脚；以及 2026-10-27/28 巡检发现的可优化点。

## 1 仓库结构地图（2026-10-27 起）

```
microduck/（本仓库，公开）
├── README.md / ROADMAP.md / CHECKLIST.md      项目导航与安全闸门
├── docs/00–13                                 硬件验收与仿真教程（原系列）
├── docs/manual/14–18                          ★ 实用手册系列（本系列，日常操作层）
├── duck/                                      ★ 鸭子实况档案
│   ├── README.md                              一页纸状态（每次巡检后更新）
│   └── snapshots/<日期>_runtime/              sanitized 快照（标定/配置/服务/策略出处）
├── scripts/                                   只读诊断与验证（Python）
├── scripts/duck/                              ★ 鸭子运维工具集（bash，见其 README）
│   └── remote/                                设计为"在鸭子上运行"的脚本（push 白名单）
├── apps/                                      ★ 应用正本（新应用一律放这里，模板 _template/）
├── hardware/                                  硬件档案（servo 台账、合同）
├── policies/                                  官方 ONNX 清单（权重不入库）
├── records/                                   脱敏后的实验记录（field/ 分阶段）
├── templates/                                 台账/映射模板
├── upstreams/ + .upstreams/                   上游 SHA 锁定与本地镜像
├── microduck/ · microduck_rl/                 官方 runtime/RL 本地副本（忽略 Git）
├── local/                                     ★ 每台电脑私有配置/拉取产物（忽略 Git）
└── .evidence/                                 原始证据与 raw 拉取（忽略 Git）
```

鸭子上的家目录目前是**按人命名的空间**（`~/zhangtong/duck-voice`、`~/shishaodong/ultralytics-learn`
等）。约定：鸭子上的目录当"运行现场"，**代码的正本放本仓库**（新应用一律放
[`apps/<名字>/`](../../apps/README.md)，从 `apps/_template/` 拷贝起步；2026-10-28 起 apps/ 架构
已落地，板上个人开发子目录按同日决定保持不变，各负责人自愿迁入），
改完经 `push-duck.sh` 上板。鸭子上直接改的东西，收工前 `pull-duck.sh` 拉回来存档。

## 2 每日开发循环（推荐流程）

```bash
# 上手：连上 + 看状态 + 看谁在
#（tailnet 成员最简：local/duck.env 的 DUCK_HOST 直接写 100.64.0.12 即可，无需隧道/跳板）
scripts/duck/tunnel-duck.sh &            # 无 tailnet / 黑洞窗口期的兜底通道
scripts/duck/status-duck.sh
scripts/duck/ssh-duck.sh 'w'                 # 有别人在线时，重大操作先打招呼

# 收工：把鸭子上变过的东西存档
scripts/duck/pull-duck.sh                    # 标定/配置/服务快照 → duck/snapshots/
scripts/duck/pull-duck.sh --code --policies  # 代码与权重要搬家时用（进 local//.evidence）
cd .evidence/duck-sync-*/code && 精选进仓库   # 需要沉淀的代码人工拷入 apps/ 并 git commit
```

推送方向（仓库 → 鸭子）只走白名单：

```bash
scripts/duck/push-duck.sh            # 演练（dry-run），看会改什么
scripts/duck/push-duck.sh --apply    # 确认后执行；只进 ~/microduck-tools/
```

约定（红线回顾）：

1. 任何 `systemctl restart/stop`、`robotctl` 运动类命令、写 `/etc/robot/`：先群里说。
2. 重启鸭子前 `w` 看一眼、群里说一声（今天就发生过一次重启把别人的会话打断）。
3. `pull` 永不删除；`push` 只进家目录白名单；密码永不进仓库。
4. 标定/robotd 配置改动后必须重新快照存档。

## 3 优化与加固清单（按优先级，2026-10-27 实测发现）

### P0 · 直接影响可用性/安全

| # | 问题 | 证据 | 建议 |
|---|---|---|---|
| 1 | **mediad 崩溃循环**：NRestarts=497，CPU 被 gst-plugin-scanner 吃到 load 3+，机身发热 | `systemctl show mediad -p NRestarts`；ps 里 91.8% CPU | **已缓解（2026-10-27 16:20）**：`media.source` 切 `"test"` 后 load 回 ~1、8443 信令恢复（改前备份 `robotd.toml.bak-20261027-camoff`）。根因疑相机 overlay 不对 + 语音进程抢音频。恢复真相机：先修 overlay 再改回 `"camera"`。注意：崩溃止住后板子仍自发重启 → 见 #5 |
| 2 | ~~异地连通性依赖单台路由器~~ ✅ **已解决（2026-10-27/28）**：GL 已通告子网路由 192.168.8.0/24；鸭子本体已装 Tailscale，tailnet IP `100.64.0.12` | `duck/network.md` §2/§6；[snapshots/2026-10-28_runtime](../../duck/snapshots/2026-10-28_runtime/) | 残留的窗口期可达性问题 → P1 #6 |
| 3 | **低电保护关闭**：`battery_empty_shutdown=false`、`limp_fall=false` | `etc-robot/feetech-ft5_robotd.toml` 快照 | 讨论后按 kissqy 文档启用；启用前先复盘 powerlog 数据（团队已有掉电记录） |
| 4 | **板上代码无版本管理**：zhangtong/shishaodong/voice 各目录没有 .git，靠手打 tar 包（duck-voice-20261027.tar.gz） | find 无 .git；家目录见 tar 包 | **2026-10-28：`apps/` 正本架构已建**（约定+模板+推送排密钥）；板上个人目录按决定保持不变，板上一律部署副本（push-duck），各负责人自愿迁入 |
| 5 | **板子自发重启（2026-10-28 新登记）**：一上午 4 次（09:17/09:22/09:45/09:53，间隔 5–8 分钟；`media.source` 已是 test 仍照发 → 与 mediad 风暴无直接关系；09:53 后至 10:17 稳定） | uptime 启动时间序列；09:34 板温 59.4°C | 优先查电源（电池触点/线径/压降）与散热，复盘 powerlog 掉电记录；已装 tailscale，重启后自动回 tailnet（撞上控制面黑洞窗口会延迟回网，见 P1 #6） |

### P1 · 体验与稳健

| # | 问题 | 建议 |
|---|---|---|
| 6 | **Headscale 控制面国内可达性（2026-10-28 新登记）**：服务器 IP 从校园网出口（中国移动）被间歇性整 IP 黑洞，窗口几分钟～20+ 分钟；鸭子重启撞上窗口会延迟回网，窗口结束自愈 | 需服务器管理员：给 `hs-nosla.haoqi90.top` 加对国内稳定的入口（CDN/前置域名/备用端口），或在离团队近处加自建 DERP；过渡期靠 GL 既有连接兜底（跳板/隧道）。详见 [duck/network.md §5](../../duck/network.md) |
| 7 | SSH 仍是"共享密码 + 少量公钥"，且鸭子 sudo 密码还是镜像出厂默认（弱口令） | 每人 `setup-key-duck.sh` 装自己钥匙；钥匙齐后改 `PasswordAuthentication no` 并**轮换鸭子 sudo 密码**（duck 和路由器都一样；路由器管理密码也应轮换，别再走聊天记录） |
| 8 | voice_chat.py 从终端手工跑（pts/0），退出就没了 | 他们目录里已有 `duck-voice.service`——评审后 `systemctl enable` 它，配 `Restart=on-failure` |
| 9 | eMMC 寿命与日志 | `journalctl --disk-usage` 看量，`/etc/systemd/journald.conf` 加 `SystemMaxUse=200M`；swap 已在用，训练类任务别放板上 |
| 10 | 板上 5.7G 的 ultralytics-learn 数据集 | 数据集迁到开发机/NAS，板上只留推理产物 |
| 11 | 找鸭子靠 IP 记忆 | **已大头解决**：tailnet 固定 IP `100.64.0.12`（换 WiFi 不变）；LAN 扫描 `find-duck.sh` 已备；avahi（`microduck.local`）降为可选 |
| 12 | **手柄现状漂移**（2026-10-28 新登记）：鸭子配对表里没有任何手柄（手册 16 所述 GameSir 已不在配对表）；`pad bindings` 两处指向本机不存在的技能（a/ground_pick、dpad_down/sit_toggle） | 现场按[手册 18 §4](18-xbox-gamepad.md) 重新配对——真 Xbox One S/Series **免装驱动即用**（内核 xpad/hid-microsoft 在板）或 GameSir；错位绑定用 `robotctl pad bind` 修正 |

### P2 · 功能演进（本地模型路线）

| 方向 | 现状 | 建议 |
|---|---|---|
| **本地 ASR**（替代讯飞云端） | stt 走讯飞流式 + 大模型识别，`.env` 存云端密钥 | Zero 3W（4×A55, 2G RAM）可跑 sherpa-onnx int8 流式模型（paraformer/zipformer，<500MB 内存）；语音响应不再依赖外网，密钥也不用上板。装法写成 `scripts/duck/remote/install-sherpa-asr.sh` 评审后用 |
| 本地 TTS | tts.py 播 mp3 | piper 中文 int8 可选；优先级低 |
| 唤醒词 | `--wake-keep 20` 参数暗示有唤醒窗口逻辑 | openWakeWord / sherpa-onnx KWS 本地化 |
| 端侧 LLM 意图 | intent.py 规则式 | 板上不建议跑 LLM；规则+小分类器足够，复杂意图留给云端可选项 |
| 自训策略闭环 | 已用 training-console 出 6 个策略 | 训练在开发机（本仓库 S4 线），产物按手册 16 §5 上板流程走 |

## 4 鸭子本体 Tailscale：✅ 已完成（2026-10-28）

> 原为"待评审后执行"的建议，2026-10-28 已装机并全链路验证，本节改为结果存档。

- 版本 v1.104.4（pkgs.tailscale.com apt 源），`tailscaled` 开机自启，常驻内存实测 ~34MB
  （此前估算 ~50MB，对 2G 板子可接受）。安装本身不动 robotd。
- 加入团队自建 Headscale `hs-nosla.haoqi90.top`（`home` 命名空间，preauth key 注册，
  headscale 节点 ID 17），hostname `microduck`，tailnet IP **`100.64.0.12`**（换 WiFi 不变）。
- 从任何 tailnet 机器 `ssh radxa@100.64.0.12` / `http://100.64.0.12:8080` 直达，
  不再依赖 GL 中继；GL↔鸭子实测 WireGuard 直连 2–10ms。
- 有意保持默认 `--accept-routes=false`：鸭子自身在 GL 通告的 192.168.8.0/24 内，接受会成环。
- **复装/新板警告：必须 `--login-server https://hs-nosla.haoqi90.top`，不要用 tailscale.com**
  （会进另一个 tailnet、与所有现有节点互不可见，且国内难连其控制面）。
- 已知限制：Headscale 服务器 IP 从校园网出口会被间歇黑洞（见 §3 P1 #6），鸭子重启若撞上
  窗口会延迟回网、窗口结束自动恢复——2026-10-28 实证：约 21 分钟窗口后无人工干预自愈。
- 完整档案：[duck/network.md](../../duck/network.md) 与
  [duck/snapshots/2026-10-28_runtime](../../duck/snapshots/2026-10-28_runtime/)。

## 5 每次巡检后的例行更新

- `duck/README.md` 的"一页纸状态"表
- 新快照目录 + `records/` 里一篇脱敏记录（模板 `records/TEMPLATE.md`）
- 发现的新问题进本清单或 CHECKLIST
