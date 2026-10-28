# 18 · Xbox 手柄连接与配置手册（真 Xbox One / Series，含 GameSir 对照）

> 目标：把一支**真的 Xbox 手柄**（Xbox One S / Series X|S / Elite 2）连上鸭子用来驾驶。
> 结论先说：**鸭子这套 runtime 官方就支持真 Xbox 手柄**，不需要装任何东西——
> 2026-10-28 只读预检确认内核驱动、蓝牙、`padd`、配对命令全部就绪（见 §8），
> 剩下的只有"人到现场按配对键"这一步。
>
> ⚠️ 安全前提与[手册 16 §1](16-web-and-policies.md)完全一致：鸭子放地上有支撑、周围 1 米清空、
> 现场有人、急停可达。`motion_enabled = true`：一上电、给指令鸭子就会动。

## 1 30 秒版

```bash
# 1) 手柄：短按 Xbox 键开机 → 按住顶边 Sync 小键直到 Xbox 灯【快闪】（进配对模式）
# 2) 在鸭子附近，SSH 上鸭子（连接方式见手册 14），然后：
sudo robotctl pad pair          # 等它打印 paired/connected
robotctl pad status             # 应看到 pad connected + padd active
# 3) 驾驶：按一次 Menu/Start 站立 → 再按一次开启策略驾驶 → 微动摇杆慢走（渐进流程见手册 16 §3）
```

配错/换手柄：`sudo robotctl pad forget`；不认识的手动配对：`sudo robotctl pad pair <MAC>`。

## 2 我的手柄能不能连（型号判别）

| 手柄 | 蓝牙 | 能否连鸭子 |
|---|---|---|
| Xbox One S（型号 **1708**，2016 起） | ✅ | ✅ 推荐（二手便宜） |
| Xbox Series X\|S（**1914**） | ✅ | ✅ |
| Xbox Elite 2（**1797**） | ✅ | ✅（背键映射未验证） |
| Xbox One 初代（**1537/1697**） | ❌ 无蓝牙 | ❌（见下） |
| Xbox Elite 初代（**1698**） | ❌ 无蓝牙 | ❌（见下） |
| GameSir Nova 2 Lite（鸭子原配） | ✅ Xbox 模式 | ✅ 走 gamesir-xboxd 桥接，见 §5 |
| DualSense / Switch Pro 等其他手柄 | — | runtime 同样支持（`robotctl pad pair` 帮助里写了配法），未实测 |

- **型号在电池仓标签上**；更简单的判别法：**能和手机蓝牙配对 = 有蓝牙**。
- 初代无蓝牙手柄理论上可走 USB 线（内核 xpad 支持），但鸭子 ZERO 3W 的 USB-C
  是供电/gadget 口（RNDIS 用它），板上没有暴露的 USB host 口，Xbox 无线适配器也插不上——
  **实际方案就是换一支蓝牙款**。
- 两个前置条件：
  - **固件别太老**：One S 早期固件蓝牙兼容性差，配不上/掉线先用 Windows 的
    "Xbox Accessories" 应用（或 Xbox 主机）把手柄固件升级。
  - **电量**：1708 用 5 号电池或锂电包，低电会频繁断线——连不稳先换电池。

## 3 系统是怎么吃手柄的（为什么"直接就能连"）

```text
真 Xbox 手柄 ──蓝牙──> BlueZ(hidp) ──> 内核 HID (hid-microsoft/hid-generic) ──> /dev/input/eventX
GameSir Nova 2 Lite ──蓝牙──> gamesir-xboxd 桥接（uinput 虚拟 Xbox 手柄）──┘
                                                                              ↓
                                       padd（"driving whatever pad connects"）
                                                                              ↓ 50Hz 意图 + deadman
                                                                          robotd ──> 15 舵机
```

- **真 Xbox 手柄不需要 gamesir-xboxd 桥**：内核 6.1（板上 `6.1.115-vendor-rk35xx`）自带
  Xbox 支持——USB 走 `xpad`，蓝牙走 `hid-microsoft`，驱动文件 2026-10-28 已确认在板
  （`/lib/modules/.../joystick/xpad.ko`、`.../hid/hid-microsoft.ko`），插上/连上会自动加载。
- `padd` 不挑品牌，"连上谁就驱动谁"；**多支手柄可共存**（都保持配对，谁连上用谁），
  所以加一支 Xbox 手柄不影响原 GameSir。
- `btd` 服务（"Robot BLE transport adapter"）是手机 App 连鸭子的 BLE API 前门，
  **与手柄配对无关**，别混淆。
- 配对入口是 **`robotctl pad pair`**（它自己调 BlueZ）：配对即 trust，重启后手柄自动回连，
  无需人登录。`robotctl pad forget` 撤销一支手柄。

## 4 配对步骤（现场操作，约 2 分钟）

**第 0 步 · 环境预检（可选，只读）**：

```bash
# 鸭子上（push-duck.sh 推送后）：
bash ~/microduck-tools/remote/pad-preflight.sh
# 或手动看三样：robotctl pad status / systemctl is-active padd / bluetoothctl show | head -5
```

**第 1 步 · 手柄进配对模式**：

1. 短按 Xbox 键开机（**不要长按**——长按是关机）。
2. 按住手柄**顶边的 Sync 小圆键**（USB-C 口旁边）直到 Xbox 灯**快闪**。
3. 手柄拿到鸭子旁边（半米内），配对期间别松开配对状态。

**第 2 步 · 鸭子上执行配对**：

```bash
sudo robotctl pad pair
# 它会扫描"正在配对模式的手柄"并自动选一个；成功会打印 paired/connected
```

- 若提示不认识该设备（罕见），它会**打印扫到的地址**，用地址显式配：
  `sudo robotctl pad pair AA:BB:CC:DD:EE:FF`。
- 若扫描窗口内没找到：确认灯在快闪、距离够近，重跑一次（可加 `--timeout 30` 加长）。

**第 3 步 · 验证**：

```bash
robotctl pad status     # 期望: pad <MAC> connected; padd active — driving
robotctl logs padd -n 20   # 看 padd 有没有报错（不需要 sudo）
```

**第 4 步 · 首次驾驶**（渐进，同[手册 16 §3](16-web-and-policies.md)）：

1. 手柄连上**不会立刻动**——按一次 **Menu/Start** 才上电站立到 HOME，再按一次才开启策略驾驶（完整按键表见 §5）。
2. 原地站立 → 微动摇杆 → 慢走；异常（单腿软、异响、前倾不受控）立即松手，
   deadman（500ms 无输入即清零速度并卸力）会接管。
3. 收工/搬鸭前：按一下 **Select/View 松手即卸力**（或 `robotctl robot relax` / 网页中控松使能），再关手柄。

## 5 按键映射与 GameSir 对照

**固定控制**（padd 启动日志 `driving —` 行原文，2026-10-28 实测，对本机 walk 模式有效）：

| Xbox 按键 | 作用 |
|---|---|
| **Menu（Start）按一次** | 关节上电、缓升到 HOME 站立 |
| **Menu 再按** | 开/关策略驾驶（走路的使能开关） |
| 左摇杆 | 行走方向/速度（策略开启时） |
| `y` | 头部控制模式 |
| `b` | 躯干姿态模式 |
| `lt` / `rt` 扳机 | 嘴部（开合） |
| `dpad_up` 长按 3s | walk / roller 模式切换 |
| `dpad_right` | 重启全部舵机 |
| **`select`（View）松手** | **卸力断电**（拿起鸭子前按这个） |
| `select` 长按 2s | 坐下并关机 |
| （roller 模式下 `dpad_left` 2s | 蹲/转轮滑技能；本机当前 walk 模式不生效） |

**一键技能绑定**（`robotctl pad bindings`，可改；两处"无此技能"是本机 robotd 技能表
与默认绑定没对齐，自行改绑即可）：

| 按键 | 绑定 | 状态 |
|---|---|---|
| `x` | roulade 前滚翻 | ✅ |
| `lb` / `rb` | kick_left / kick_right 踢球 | ✅ |
| `a` | ground_pick | ⚠️ 本机无此技能 |
| `dpad_down` | sit_toggle | ⚠️ 本机无此技能 |

改绑/复位（即时生效，padd 一秒内跟上）：

```bash
robotctl pad bind <button> <skill>     # 例: robotctl pad bind a roulade
robotctl pad reset [button]            # 省略按钮 = 全部五个复位默认
robotctl robot do --help               # 看本机实际有哪些技能名
```

GameSir Nova 2 Lite 对照：Xbox 模式（A+HOME 开机）下经 `gamesir-xboxd` 桥接，
按键布局同上表；真 Xbox 手柄少一层桥接、延迟更低。两支都配对时**谁先连上用谁**，
换手柄用完把另一支关机即可，或 `sudo robotctl pad forget` 清掉不用的。

## 6 验证与体检工具（全部只读）

| 命令 | 看什么 |
|---|---|
| `robotctl pad status` | 手柄配对/连接 + padd 是否在驱动 |
| `robotctl monitor` | 实时面板（含 pad 事件流、意图、关节状态） |
| `robotctl logs padd -n 50` | padd 日志尾部（免 sudo） |
| `cat /proc/bus/input/devices` | 找 `Xbox Wireless Controller` 节点（蓝牙连上才出现） |
| `timeout 8 bluetoothctl devices Connected` | 蓝牙层连接状态 |
| 深度链路质量：`pad-link-test.sh` | 量化掉线/停顿。脚本在**本机**官方 runtime 副本 `microduck/scripts/pad-link-test.sh`（该目录被 Git 忽略、不在公开仓库），scp 上板跑；测时摇杆要一直动 |

## 7 故障排查速查

| 症状 | 原因与办法 |
|---|---|
| `pad pair` 扫不到 | 灯没在快闪（长按 Xbox 键其实是关机了）；距离远；重进配对模式再跑，加 `--timeout 30` |
| `pad pair` 说不认识 | 按它打印的 MAC 显式配对：`sudo robotctl pad pair <MAC>` |
| 配对成功但 `pad status` 没显示 | `robotctl logs padd -n 50`；`cat /proc/bus/input/devices` 看节点在不在；再看 §7 末尾蓝牙服务项 |
| 连上几秒就断 | 手柄电池低（换电池）；固件老（Windows Xbox Accessories 升级）；2.4G WiFi 满载挤占蓝牙（AIC8800 单天线共存，离路由器远点或用 5G 频段） |
| 走路中偶发急停（日志 `intents went stale`） | 蓝牙链路停顿触发 deadman——这是**安全机制在正确工作**；频发就用 `pad-link-test.sh` 量化，再考虑换电池/缩短距离 |
| 手柄能连手机、连不上鸭子 | Xbox 手柄一次只记住/服务一台主机：先在手机/电脑蓝牙里**断开并忽略**该手柄，重进配对模式再配鸭子；顺带确认电量与固件（§2） |
| 两支手柄打架 | padd 只驱动先连上的；把不用的一支关机，或 `sudo robotctl pad forget <MAC>` |
| 蓝牙适配器整个不见了（`bluetoothctl show` 空） | AIC8800 的蓝牙由 `aic-bluetooth.service` 晚挂载（开机约 73 秒后才就绪）；掉电重启后没起来就 `systemctl status aic-bluetooth bluetooth btd`（改动前群里打招呼） |
| 想回到"无手柄"状态 | `sudo robotctl pad forget`（可逐支），padd 空转无副作用 |

已知小坑（2026-10-28 实测）：板上 `robotctl`（API v37）比 `robotd`（API v40）旧，
`pad bindings` 等命令会打版本警告，能正常用；若某子命令报"无法服务"，以网页中控同名功能兜底。

## 8 2026-10-28 预检实测档案（本手册的依据）

只读巡检（经 Tailscale `100.64.0.12`，未动任何服务/配置）确认：

| 项 | 实测值 | 结论 |
|---|---|---|
| 蓝牙 | 适配器 `CC:C8:37:3C:C3:1E` powered，BlueZ **5.82**，别名 duck-a437 | ✅ 就绪 |
| 内核 | `6.1.115-vendor-rk35xx`，`xpad.ko` + `hid-microsoft.ko` 在板，`hidp` 已加载 | ✅ 无需装驱动 |
| 服务 | padd / gamesir-xboxd / btd / robotd / bluetooth 全部 active | ✅ 就绪 |
| 配对入口 | `robotctl pad pair` 帮助文档**明确写了 Xbox 手柄配法**，支持按 MAC 配对 | ✅ 官方路径 |
| 当前配对列表 | 只有一副耳机（Baseus Bowie M2s Pro），**没有任何手柄在配对** | ⚠️ 手册 16 所述 GameSir 实体手柄现状已漂移，登记进[手册 17 清单](17-team-workflow.md) |
| 按键绑定 | 5 个一键技能绑定中 2 个指向本机不存在的技能（a/ground_pick、dpad_down/sit_toggle） | ⚠️ 小问题，见 §5 |

原始输出存 `.evidence/duck-xbox-preflight-20261028/`（不入库）；脱敏记录见
[records/2026-10-28_xbox-gamepad-preflight.md](../../records/2026-10-28_xbox-gamepad-preflight.md)。

**本次已完成**：只读预检、本手册、`scripts/duck/remote/pad-preflight.sh` 上板（push 白名单）。
**待人工（需现场）**：手柄物理配对、试驾、按需改绑技能——就绪后按 §4 走。
