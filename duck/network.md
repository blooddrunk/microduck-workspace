# duck/network.md —— 鸭子的网络身份证（怎么找到它、连上它）

> 最后核实：2026-10-28。IP 会变，MAC 和流程不变。连不上先跑 `scripts/duck/find-duck.sh`。

## 1 身份标识（不变的锚点）

| 标识 | 值 |
|---|---|
| WiFi MAC（wlan0） | `cc:c8:37:3d:3c:93`（Radxa AIC8800；扫描网段时按前缀 `cc:c8:37` 匹配） |
| USB 网卡 MAC（usb0/RNDIS） | `96:26:7b:02:60:1f` |
| 主机名 | `microduck`（DHCP 里也注册这个名字） |
| 机器人名 / 序列号 | `duck-a437` / `e98b5305836f874a`（`robotctl system info`） |
| Tailscale IP | `100.64.0.12`（tailnet `hs-nosla.haoqi90.top` 内固定，2026-10-28 起；换 WiFi 也不变，见 §6） |

## 2 网络拓扑（2026-10-27 实测）

```
                      Tailscale（tailnet: hs-nosla.haoqi90.top）
   ┌────────────────────┬─────────────────────┬───────────────────┐
   │                    │                     │                   │
work-pc(你)         GL-MT3600BE          my-workspace-router    home-router(iStoreOS)
100.64.0.4          100.64.0.8           100.64.0.10            100.64.0.5
当前在192.168.10.x   ▲ LAN 192.168.8.1/24   通告192.168.10.0/24    通告192.168.100.0/24
                    │ 通告192.168.8.0/24（2026-10-27起）
                    │ WAN 172.17.50.238/22
                    │ (Tailscale中继东京,偶发抖动)
              WiFi: GL-MT3600BE-5e4
                    │
              🦆 microduck = 192.168.8.161 ＋ 本体 Tailscale 100.64.0.12 (2026-10-28起)
                 (另常驻: lutao笔记本.133 / zt主机.238 / LAPTOP-56HVUEDS.236)
```

- 鸭子历史 IP：`192.168.31.86`（2026-10-14，小米路由）→ `192.168.8.161`（现在，GL 路由）。
  换路由/重配网后 IP 会变，以 [find-duck.sh](../scripts/duck/find-duck.sh) 结果为准。
- GL-MT3600BE **已通告并获批子网路由 `192.168.8.0/24`**（2026-10-27 实测：tailnet 机器可直达鸭子
  的 8080/22 等端口，不再必须跳板/隧道）。路径经东京 DERP 中继、偶发抖动，打不开就重试或退回方式 B/C。
- 鸭子本体已装 Tailscale（2026-10-28，v1.104.4）：tailnet IP **`100.64.0.12`**，从任何 tailnet
  机器直达、不依赖 GL 中继（实测 GL↔鸭子 WireGuard 直连 10–50ms，从 GL 开
  `http://100.64.0.12:8080` 网页中控正常）。鸭子保持默认 `--accept-routes=false`——它自己就在
  192.168.8.0/24 里，接受该子网路由会成环。装机记录见
  [snapshots/2026-10-28_runtime](snapshots/2026-10-28_runtime/README.md)。

## 3 三种连接方式

### 方式 A：直连（推荐；tailnet 任意机器或同一 WiFi）
```bash
ssh radxa@100.64.0.12          # 鸭子本体 Tailscale（2026-10-28 起，任何网络可用）
ssh radxa@192.168.8.161        # 或 LAN 地址（密码找管理员要；配好钥匙后免密）
# 网页中控: http://100.64.0.12:8080 或 http://192.168.8.161:8080
```
LAN 地址对 tailnet 机器也开放（经 GL 子网路由，见 §2），无需在同一 WiFi。
IP 不对就先扫：`scripts/duck/find-duck.sh 192.168.8`

### 方式 B：经路由器跳板（异地，Tailscale 里）
```bash
ssh -J root@100.64.0.8 radxa@192.168.8.161
# 前提: 路由器上装了你的公钥；本仓库工具已内置:
DUCK_HOST=192.168.8.161 DUCK_JUMP=root@100.64.0.8 scripts/duck/ssh-duck.sh
```
注意：路由器走东京 DERP 中继、偶发抖动，命令失败重试即可。这是鸭子本体 Tailscale
（方式 A 的 `100.64.0.12`）不在线时的兜底。

### 方式 C：后台隧道（异地 + 长时间传输，推荐）
```bash
scripts/duck/tunnel-duck.sh &     # 建立并自动重连 127.0.0.1:2222 → 鸭子:22
# local/duck.env 里 DUCK_TUNNEL=1 后，所有 duck-*.sh 自动走隧道
```

### 方式 D（应急）：USB 线
Type-C 连电脑，鸭子以 RNDIS 网卡出现，地址 `192.168.7.2`（ssh root@192.168.7.2，
2026-10-14 实测可用）。详见 [docs/01_BOARD_BOOT.md](../docs/01_BOARD_BOOT.md)。

## 4 网页中控（Microduck Studio / kissqy 中控）

- 正常使用：浏览器打开 `http://192.168.8.161:8080`（mediad 提供，机器人名 duck-a437）；
  tailnet 机器（含异地）直接开 **`http://100.64.0.12:8080`**（2026-10-28 起首选）。
- 首次配网/重刷镜像后：连热点 `Microduck-kissqy`（密码见镜像说明），访问 `http://10.42.0.1:8088`。
- 两个直达地址都打不开（本体 tailscale 与子网路由同时哑火）时，退回 SSH 端口转发
  `ssh -N -L 8080:192.168.8.161:8080 root@100.64.0.8`。
- 页面能开但横幅报「signalling port (8443) did not answer」：**不是网络/防火墙问题**。8080 是
  mediad 启动早期就绑定的，8443（信令）要等摄像头管线起来才绑——mediad 崩溃循环时永远走不到
  那一步（板上 `ss -tln` 里没有 8443，外部表现为 connection refused 而非超时）。处置见 §5。

## 5 排障速查

| 症状 | 原因与办法 |
|---|---|
| ping/ssh 全超时 | 鸭子没电/关机/换网了。充电开机后等 ~2 分钟，`find-duck.sh` 重扫 |
| 能 ping 通 ssh 拒绝 | sshd 未起（极端情况），USB 方式 D 进去 `systemctl status ssh` |
| 跳板报 timeout | GL 路由器中继抖动，等 30s 重试；或改用隧道方式 C |
| IP 变了 | `find-duck.sh` 重扫；或登录路由器 100.64.0.8 看 `/tmp/dhcp.leases` |
| 8080 打不开 | `journalctl -u mediad -n 30`（历史上它有崩溃重启循环，见手册 15） |
| 8080 能开、页面报 8443 未应答 | 不是防火墙。板上 `ss -tln \| grep 8443` 为空 = mediad 崩溃循环没绑到 8443。根因（2026-10-27 抓到）：相机 overlay 不对，journal 报 `none has an imx219 entity … DUCK_CAMERA_OVERLAY may name the wrong module for this camera`。**已处置（2026-10-27 16:20）**：`media.source = "test"`（推 256x144@5 测试图样，管线照常起，8443 信令恢复，实测 WS 握手 101 + welcome）。注意 8443 说的是 `ws://`（明文 WebSocket），用 `https://` 探它会握手失败，别误判。恢复真相机：改回 `"camera"` 并修 overlay；改前配置备份在板上 `/etc/robot/robotd.toml.bak-20261027-camoff` |
| 整机 ping 不通（路由器同 LAN 也不通） | 板子假死/掉电重启。2026-10-27 一小时内三次（15:37、约16:05、约16:11），疑似 mediad 崩溃风暴高载（load 18+）诱发。2026-10-27 16:20 已把 `media.source` 切到 `test` 止住风暴（load 回落到 ~1）。**但 2026-10-28 上午又两次（09:17、09:22，此时已是 test 源）**——自发重启另有原因，电源/散热嫌疑加大（09:34 实测板温 59°C、室温常载），持续观察；`tailscaled` 已设自启，重启后自动回 tailnet |
| `100.64.0.12` 连不上/状态 offline（LAN 地址正常） | 鸭子本体 tailscale 不在线。先看板上 `tailscale status`；若卡在 NeedsLogin/offline，多半是控制面瞬断（下行）。也可看 §6 复装说明 |
| 板上 curl `https://hs-nosla.haoqi90.top` 连接超时（几分钟后自愈） | 控制面在鸭子所在校园网出口偶发 SNI 级瞬断（2026-10-28 装机时实测：纯 TCP 连 443 通，带 SNI 的 HTTPS 会触发短暂黑洞、约几分钟自愈）。tailscaled 会自动重连，无需处理；期间用方式 B/C 兜底。同理 Tokyo DERP 也偶发抖动，属同链路特性 |

## 6 建议但尚未实施（见 docs/manual/17 优化清单）

- ~~给鸭子本体装 Tailscale~~ ✅ **已完成（2026-10-28）**：v1.104.4（pkgs.tailscale.com apt 源，开机自启），
  `--login-server https://hs-nosla.haoqi90.top` 加入 `home` 命名空间（管理员发 preauth key 注册，
  headscale 节点 ID 17），hostname `microduck`，tailnet IP **`100.64.0.12`**。实测：GL↔鸭子
  WireGuard 直连 10–50ms；work-pc 直连 462ms / DERP(tokyo) 140ms；从 GL 经 `100.64.0.12:8080`
  可打开网页中控。状态存档：[snapshots/2026-10-28_runtime](snapshots/2026-10-28_runtime/README.md)。
  复装提醒：**不要用 tailscale.com**（会进另一个 tailnet、与所有现有节点互不可见）；鸭子保持默认
  `--accept-routes=false`（理由见 §2）。
- ~~GL 路由器通告子网路由 `192.168.8.0/24`~~ ✅ 已完成（2026-10-27 实测可用，见 §2）。
- 鸭子上 `avahi-daemon` 让 `microduck.local` 可解析（现在 mDNS 没开）。
