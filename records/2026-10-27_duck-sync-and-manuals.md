# 2026-10-27 · 鸭子实况同步、运维工具集与实用手册

**做了什么**：经 GL-MT3600BE 路由器（Tailscale 跳板/隧道）对鸭子做了一次全程只读巡检，
把运行时状态/标定/配置/策略出处回收到仓库（`duck/`），新增 `scripts/duck/` 运维工具集
与 `docs/manual/14–17` 实用手册。未发送任何控制命令，未重启任何服务，未修改板上任何文件
（唯一例外：向鸭子和路由器的 `authorized_keys` 各追加了一把本机公钥以建立免密通道）。

## 连接链路（本次实测可用）

- 鸭子 `192.168.8.161`（WiFi `GL-MT3600BE-5e4`，DHCP 名 `microduck`，MAC `cc:c8:37:…:3c:93`）。
- 异地路径：`ssh -J root@100.64.0.8`（GL 路由器，dropbear）→ 鸭子；中继偶发抖动，
  改用常驻隧道 `scripts/duck/tunnel-duck.sh`（127.0.0.1:2222）后稳定完成全部采集。
- 采集期间 14:53 左右鸭子被重启一次（他人操作，非本次巡检引起；期间连接重置即源于此）。

## 关键发现（详见 duck/README.md 一页纸状态）

1. **标定完成且运动已启用**：15 关节全部 `calibrated = true`，`motion_enabled = true`，
   IMU `imu_mount_verified = true`（含四元数）。标定三份历史档已存 `duck/snapshots/`。
2. **已部署 6 个自训策略**（walk/sitstand/ground_pick/kick×2/roulade），provenance 显示
   2026-10-01 由 microduck-training-studio（rsl_rl）训练部署；另有 roller 技能与官方 seed-v5。
   权重 21 个 onnx（43MB）拉到 `local/duck-policies-20261027/`（不入库）。
3. **服务面**：robotd/padd/tofd/btd/configd/gamesir-xboxd/powerlog 正常；
   **mediad NRestarts=497**（崩溃循环，CPU 占用高，疑与音频被语音进程占用相关）——优化清单 P0。
4. **语音控制在跑**：`voice_chat.py --wake-keep 20`（`~/zhangtong/duck-voice`，讯飞 ASR +
   大模型识别 + 意图解析）；代码已拉 `.evidence/duck-sync-*/code/`（含 `.env`，永不入库）。
5. **板上代码无版本管理**（多个队友目录无 .git）——优化清单 P0-4。
6. 低电自动关机与 limp_fall 均为 false（安全取舍待团队决策）。
7. 网页中控端口为 **8080**（8088 仅首次配网热点模式）。

## 新增产物

| 路径 | 内容 |
|---|---|
| `duck/README.md` · `duck/network.md` | 一页纸状态、网络身份证与三种连接方式 |
| `duck/snapshots/2026-10-27_runtime/` | 五视图 + 标定×3 + robotd 配置×4 + 策略 provenance |
| `scripts/duck/{lib,ssh,status,find,pull,push,setup-key,tunnel}-*.sh` | 运维工具集（全部实测过） |
| `docs/manual/README.md + 14–17` | 初学者手册：连接/巡检/操控/协作与优化清单 |
| `local/duck.env`（不入库） | 本机隧道模式连接配置 |

## 隐私与脱敏状态

- 未采集/未入库：bash_history、`.claude*`、`.env`、SSH 私钥、WiFi 密码。
- 快照与手册中出现队友目录名（zhangtong/shishaodong 等）：提交前如需匿名化由人工替换。
- 路由器/鸭子口令只用于本次建立密钥通道，未写入任何仓库文件。

## 下一步建议（摘自 docs/manual/17 优化清单）

P0：处理 mediad 崩溃循环；给鸭子本体装 Tailscale（根治异地连通）；板上代码正本迁入仓库；
评审低电保护开关。P1：语音进程 systemd 化；SSH 收敛为纯密钥；journald 限容。
