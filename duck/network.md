# duck/network.md —— 鸭子的网络身份证（怎么找到它、连上它）

> 最后核实：2026-10-27。IP 会变，MAC 和流程不变。连不上先跑 `scripts/duck/find-duck.sh`。

## 1 身份标识（不变的锚点）

| 标识 | 值 |
|---|---|
| WiFi MAC（wlan0） | `cc:c8:37:3d:3c:93`（Radxa AIC8800；扫描网段时按前缀 `cc:c8:37` 匹配） |
| USB 网卡 MAC（usb0/RNDIS） | `96:26:7b:02:60:1f` |
| 主机名 | `microduck`（DHCP 里也注册这个名字） |
| 机器人名 / 序列号 | `duck-a437` / `e98b5305836f874a`（`robotctl system info`） |

## 2 网络拓扑（2026-10-27 实测）

```
                      Tailscale（tailnet: hs-nosla.haoqi90.top）
   ┌────────────────────┬─────────────────────┬───────────────────┐
   │                    │                     │                   │
work-pc(你)         GL-MT3600BE          my-workspace-router    home-router(iStoreOS)
100.64.0.4          100.64.0.8           100.64.0.10            100.64.0.5
当前在192.168.10.x   ▲ LAN 192.168.8.1/24  通告192.168.10.0/24    通告192.168.100.0/24
                    │ WAN 172.17.50.238/22
                    │ (Tailscale中继东京,偶发抖动)
              WiFi: GL-MT3600BE-5e4
                    │
              🦆 microduck = 192.168.8.161
                 (另常驻: lutao笔记本.133 / zt主机.238 / LAPTOP-56HVUEDS.236)
```

- 鸭子历史 IP：`192.168.31.86`（2026-10-14，小米路由）→ `192.168.8.161`（现在，GL 路由）。
  换路由/重配网后 IP 会变，以 [find-duck.sh](../scripts/duck/find-duck.sh) 结果为准。
- GL-MT3600BE **没有**向 Tailscale 通告 192.168.8.0/24 子网路由 → tailnet 其他机器不能直达鸭子，
  必须跳板或隧道（见下）。

## 3 三种连接方式

### 方式 A：和鸭子同一 WiFi（最简单，现场用）
```bash
ssh radxa@192.168.8.161        # 密码找管理员要；配好钥匙后免密
# 网页中控: http://192.168.8.161:8080
```
IP 不对就先扫：`scripts/duck/find-duck.sh 192.168.8`

### 方式 B：经路由器跳板（异地，Tailscale 里）
```bash
ssh -J root@100.64.0.8 radxa@192.168.8.161
# 前提: 路由器上装了你的公钥；本仓库工具已内置:
DUCK_HOST=192.168.8.161 DUCK_JUMP=root@100.64.0.8 scripts/duck/ssh-duck.sh
```
注意：路由器走东京 DERP 中继、偶发抖动，命令失败重试即可。

### 方式 C：后台隧道（异地 + 长时间传输，推荐）
```bash
scripts/duck/tunnel-duck.sh &     # 建立并自动重连 127.0.0.1:2222 → 鸭子:22
# local/duck.env 里 DUCK_TUNNEL=1 后，所有 duck-*.sh 自动走隧道
```

### 方式 D（应急）：USB 线
Type-C 连电脑，鸭子以 RNDIS 网卡出现，地址 `192.168.7.2`（ssh root@192.168.7.2，
2026-10-14 实测可用）。详见 [docs/01_BOARD_BOOT.md](../docs/01_BOARD_BOOT.md)。

## 4 网页中控（Microduck Studio / kissqy 中控）

- 正常使用：浏览器打开 `http://192.168.8.161:8080`（mediad 提供，机器人名 duck-a437）。
- 首次配网/重刷镜像后：连热点 `Microduck-kissqy`（密码见镜像说明），访问 `http://10.42.0.1:8088`。
- 手机/笔记本连上 `GL-MT3600BE-5e4` 同一 WiFi 即可用；异地用不了（无公网回源），
  想异地用网页可加 SSH 端口转发：`ssh -N -L 8080:192.168.8.161:8080 root@100.64.0.8`。

## 5 排障速查

| 症状 | 原因与办法 |
|---|---|
| ping/ssh 全超时 | 鸭子没电/关机/换网了。充电开机后等 ~2 分钟，`find-duck.sh` 重扫 |
| 能 ping 通 ssh 拒绝 | sshd 未起（极端情况），USB 方式 D 进去 `systemctl status ssh` |
| 跳板报 timeout | GL 路由器中继抖动，等 30s 重试；或改用隧道方式 C |
| IP 变了 | `find-duck.sh` 重扫；或登录路由器 100.64.0.8 看 `/tmp/dhcp.leases` |
| 8080 打不开 | `journalctl -u mediad -n 30`（历史上它有崩溃重启循环，见手册 15） |

## 6 建议但尚未实施（见 docs/manual/17 优化清单）

- 给鸭子本体装 Tailscale（`curl -fsSL https://tailscale.com/install.sh | sh`），
  之后从任何 tailnet 机器直达，不再依赖路由器中继——多人异地协作的根本解法。
- GL 路由器通告子网路由 `192.168.8.0/24`（需路由器管理 + tailnet 控制台批准）。
- 鸭子上 `avahi-daemon` 让 `microduck.local` 可解析（现在 mDNS 没开）。
