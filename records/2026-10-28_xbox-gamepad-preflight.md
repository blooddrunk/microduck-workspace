# 2026-10-28 · Xbox 手柄接入：只读预检、手册 18 与预检脚本上板

**做了什么**：为"把真 Xbox One 手柄连上鸭子"做准备——经 Tailscale（`100.64.0.12`）对鸭子做
**全程只读**的手柄链路体检，确认系统原生支持真 Xbox 手柄后，写了
[docs/manual/18-xbox-gamepad.md](../docs/manual/18-xbox-gamepad.md)（型号判别/配对/按键/排障）
并把只读预检脚本推上板。**未配对任何设备、未重启任何服务、未动 robotd 配置**；
对鸭子唯一的写入是白名单目录 `~/microduck-tools/remote/`（`push-duck.sh --apply`）。

## 核心结论：什么都不用装，配对即可用

1. **runtime 官方支持真 Xbox 手柄**：`robotctl pad pair --help` 明确写了 Xbox 手柄配法
   （短按 Xbox 键开机 → 按住顶边 Sync 键直到快闪），支持按 MAC 配对；`padd` 自述
   "driving whatever pad connects"，多支手柄共存、谁连上用谁。
2. **内核驱动在板**（`6.1.115-vendor-rk35xx`）：`xpad.ko`（USB/适配器）、`hid-microsoft.ko`
   （蓝牙）都在，`hidp` 已加载、`uhid` 内建——蓝牙 Xbox One S/Series 直连即用，无需 xpadneo。
3. **蓝牙就绪**：BlueZ 5.82，适配器 powered；注意 AIC8800 蓝牙由 `aic-bluetooth.service`
   晚挂载（开机约 73s），刚开机配不上是正常的。
4. **真 Xbox 手柄不需要 `gamesir-xboxd`**：那个服务只负责把 GameSir Nova 2 Lite 桥接成
   虚拟 Xbox 手柄；`btd` 是手机 App 的 BLE API 前门，与手柄配对无关。

## 顺带发现（已登记手册 17 清单）

- **鸭子当前没有任何已配对手柄**（蓝牙列表只有一副 Baseus 耳机）——手册 16 所述
  "实体 GameSir 手柄"的现状已漂移，配对记录可能某次重刷/清理后丢了。
- **按键绑定两处错位**：`pad bindings` 里 `a→ground_pick`、`dpad_down→sit_toggle`
  均报 "this robot has no such skill"（本机 robotd 技能表与默认绑定不齐），可用
  `robotctl pad bind` 修正。
- 板上 `robotctl`（API v37）比 `robotd`（API v40）旧，部分子命令带版本警告，能用。
- padd 启动日志 `driving —` 行给出**完整按键表**（Start=站立/切策略、Select 松手=卸力、
  Select 长按=坐下关机等），已收录进手册 18 §5。

## 新增产物

| 路径 | 内容 |
|---|---|
| [docs/manual/18-xbox-gamepad.md](../docs/manual/18-xbox-gamepad.md) | Xbox 手柄连接与配置手册（型号/架构/配对/按键/排障/预检档案） |
| `scripts/duck/remote/pad-preflight.sh` | 只读手柄预检（驱动/蓝牙/服务/robotctl/日志六段），已推上板并在板上实测通过 |
| `.evidence/duck-xbox-preflight-20261028/`（不入库） | 原始 SSH 采集与预检脚本运行输出 |

## 待人工（需现场）

1. 带一支蓝牙款 Xbox 手柄（One S 1708 / Series 1914 / Elite 2）到鸭子旁，按手册 18 §4：
   Sync 快闪 → `sudo robotctl pad pair` → `robotctl pad status` 验证。
2. 首驾渐进（站立 → 微摇杆 → 慢走），确认 deadman 行为。
3. 视需要改绑 `a`/`dpad_down` 的技能；试驾后 `pull-duck.sh` 存档。

## 隐私与脱敏状态

记录中只含蓝牙适配器 MAC 前缀公开信息与已脱敏设备名（耳机品牌型号保留——它在板上蓝牙列表里，
任何配过对的人可见，非个人身份信息）。无凭据、无密码、无密钥。
