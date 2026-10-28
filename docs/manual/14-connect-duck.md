# 14 · 连接鸭子：网络与 SSH（初学者版）

> 目标读者：拿到一台笔记本、要第一次登录鸭子的队友。
> 你只需要会：连 WiFi、开终端、敲命令。全部命令都可以复制粘贴。

## 0 先懂一张图（鸭子在哪个网络里）

```
   你的电脑 ──(任何网络)── Tailscale ── GL-MT3600BE 路由器(100.64.0.8)
        │                                │ WiFi: GL-MT3600BE-5e4
        └────────→ 🦆 鸭子 192.168.8.161 ＝ Tailscale 100.64.0.12
```

- 鸭子通过 WiFi `GL-MT3600BE-5e4` 上网，拿到的地址是 `192.168.8.161`。
- **鸭子本体也装了 Tailscale（2026-10-28 起）**：你电脑只要装了 Tailscale 并加入同一个 tailnet，
  在任何网络都能直连 `100.64.0.12`（异地也一样），下面方法 B/C 只是它不在线时的兜底。
- 鸭子的身份证（换网络也不会变的）：

| 标识 | 值 |
|---|---|
| WiFi 网卡 MAC | `cc:c8:37:3d:3c:93`（前缀 `cc:c8:37` 是 Radxa） |
| SSH 主机名 | `microduck` |
| 机器人名 | `duck-a437`（网页中控里显示的名字） |
| Tailscale IP | `100.64.0.12`（tailnet 内固定，换 WiFi 不变） |

## 1 准备工作（每台电脑一次）

```bash
# 1) 生成 SSH 密钥（有 id_ed25519 的跳过）
ssh-keygen -t ed25519        # 一路回车

# 2) 在本仓库建立本机配置（local/ 不会提交到网上）
cp scripts/duck/duck.env.example local/duck.env
# 编辑 local/duck.env，至少填 DUCK_HOST=192.168.8.161

# 3) 把公钥装到鸭子上（会要一次鸭子密码，找管理员要）
scripts/duck/setup-key-duck.sh

# 4) 验证
scripts/duck/ssh-duck.sh 'hostname'     # 应输出: microduck
```

> 为什么要装公钥？鸭子密码是共享的，装公钥后你的电脑免密登录，脚本才能自动化；
> 以后离职/换电脑，删除鸭子上 `~/.ssh/authorized_keys` 里你那行即可。

## 2 三种连接方式（按场景选）

### 方式 A · 直连（最简单：tailnet 或现场 WiFi）

装了 Tailscale 的电脑（加入 `hs-nosla.haoqi90.top` 这个 tailnet，找管理员拉你进来）在任何网络：

```bash
ssh radxa@100.64.0.12             # 异地也能连
```

没装 Tailscale 就到现场，手机/电脑连上 WiFi `GL-MT3600BE-5e4`（密码找管理员），然后：

```bash
scripts/duck/ssh-duck.sh                 # 登录进鸭子 shell
scripts/duck/ssh-duck.sh 'uptime'        # 或只跑一条命令
```

> 鸭子 IP 变了怎么办：`scripts/duck/find-duck.sh 192.168.8` 会扫整个网段，
> 输出里 22 端口开放的 IP 逐个试，`hostname` 回显 `microduck` 的就是。
> （Tailscale IP `100.64.0.12` 不会变，能连它就不用扫。）

### 方式 B · 异地跳板（偶尔用）

```bash
DUCK_HOST=192.168.8.161 DUCK_JUMP=root@100.64.0.8 scripts/duck/ssh-duck.sh
```

原理：先登录 GL 路由器（它 24 小时挂在 Tailscale 里），再从它连鸭子。
缺点：路由器的 Tailscale 走东京中继、偶发超时，失败就重试一两次。

### 方式 C · 异地隧道（长时间干活/传文件，推荐）

```bash
scripts/duck/tunnel-duck.sh &      # 后台保持一条到鸭子的转发（断线自动重连）
# local/duck.env 里写 DUCK_TUNNEL=1 后，所有工具自动改走 127.0.0.1:2222
scripts/duck/ssh-duck.sh           # 现在等于登录鸭子
```

### 方式 D · USB 应急线

Type-C 数据线把鸭子接电脑，它会以"USB 网卡"出现，地址固定 `192.168.7.2`
（2026-10-14 实测）。WiFi 全挂了时用这招。

## 3 连上之后：网页中控

- 你的电脑在 tailnet 里（装了 Tailscale）：浏览器直接开 **`http://100.64.0.12:8080`**，
  现场异地都行（2026-10-28 起首选）。
- 现场同一 WiFi 下，也可以开 **`http://192.168.8.161:8080`**（不是 8088！
  8088 只是刚刷完镜像首次配网时热点模式用的）。
- 两个都不行（鸭子本体 tailscale 掉线 + 中继抖动）时兜底：
  `ssh -N -L 8080:192.168.8.161:8080 root@100.64.0.8`，然后本机浏览器开 `http://127.0.0.1:8080`。
- 具体怎么用网页让鸭子动起来，见[手册 16](16-web-and-policies.md)。

## 4 常见故障对照表

| 症状 | 大概率原因 | 处理 |
|---|---|---|
| ssh 一直 timeout | 鸭子没电/关机/换 WiFi | 上电等 2 分钟 → `find-duck.sh` 重扫 |
| ssh 提示 `Permission denied (publickey)` | 公钥没装好/换电脑了 | 重跑 `setup-key-duck.sh` |
| `ssh radxa@100.64.0.12` 超时 | 鸭子本体 tailscale 掉线（板子重启中/控制面瞬断）| 等 2 分钟重试；期间用方式 B/C 或现场地址 |
| 跳板方式频繁超时 | 路由器 Tailscale 中继抖 | 换方式 C 隧道（自动重连） |
| `find-duck.sh` 扫不到 | 不在同一网段 | 你在异地 → 用方式 B/C；或先连 VPN/手机热点到现场网 |
| 网页 8080 打不开 | mediad 崩溃循环（已知问题） | `journalctl -u mediad -n 30` 看日志，见手册 15 §6 |

## 5 深入阅读

- 完整网络档案（含 tailnet 拓扑、历史 IP）：[duck/network.md](../../duck/network.md)
- 刷机与首次启动：[docs/01_BOARD_BOOT.md](../01_BOARD_BOOT.md)
- 工具脚本用法总表：[scripts/duck/README.md](../../scripts/duck/README.md)
