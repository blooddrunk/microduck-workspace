# 2026-10-28 · 鸭子本体 Tailscale 装机与网络韧性实测

**做了什么**：按 [手册 17 §4](../docs/manual/17-team-workflow.md)（原"待评审后执行"项）在鸭子本体
安装 Tailscale 并加入团队自建 Headscale，完成双向往返验证。操作通道：本机密钥 SSH
`radxa@192.168.8.161`（GL LAN）+ Headscale 服务器 CLI（root，一次性密码通道，临时文件已删）+
GL 路由器只读复核。除安装/注册与两次 `tailscaled` stop/start（应对黑洞窗口）外，
未动任何运行时服务，未发送任何机器人控制命令。

## 结果（一句话）

鸭子在 tailnet 固定为 **`100.64.0.12`**（headscale v0.29.3 `home` 命名空间，节点 ID 17，
v1.104.4，`tailscaled` 开机自启，常驻内存实测 ~34MB）。任何 tailnet 机器可直达 SSH(22) 与
网页中控(8080)，不再依赖 GL 中继；有意保持 `--accept-routes=false`（鸭子在 GL 通告的
192.168.8.0/24 内，接受会成环）。

## 实测数据（09:31–09:33 清晰窗口）

- 鸭子→GL：WireGuard 直连 via 172.17.50.238:41641，10ms；鸭子→work-pc：DERP(东京) 140ms、
  直连建立后 462ms；鸭子→my-workspace-router：DERP(东京) 318ms。
- GL→鸭子：直连 50ms（LAN 端点）；`wget http://100.64.0.12:8080` 取回 mediad 网页 HTML。
- netcheck：UDP true，出口 112.17.79.156（校园网中国移动），最近 DERP "Bitsflow Tokyo"。

## 过程中的两个新发现（已进优化清单）

1. **Headscale 服务器 IP 从校园网出口被间歇性整 IP 黑洞**（非 SNI 精准阻断：同 IP 换域名
   不通、GL 新建连接超时、百度正常、服务器健康、本机经宿主 VPN 不受影响）。窗口几分钟～
   21 分钟，自愈。鸭子不重启时已建立连接可熬过窗口；重启撞窗口则延迟回网——当日 10:06:30
   实证约 21 分钟窗口后无人工干预自愈（2ms 直连、网页恢复）。→ 手册 17 §3 P1 #6、
   CHECKLIST P1。
2. **板子自发重启 2026-10-28 上午 4 次**（09:17/09:22/09:45/09:53，间隔 5–8 分钟；
   `media.source` 已是 test 仍发生 → 与 mediad 风暴无直接关系，电源/散热嫌疑；
   09:34 板温 59.4°C；09:53 后至 10:17 稳定）。→ 手册 17 §3 P0 #5、CHECKLIST P0。

## 产物

| 路径 | 内容 |
|---|---|
| `duck/network.md` | §1 增加 tailscale IP 身份行；§2/§3/§4/§6 与 §5 排障表全面同步 |
| `duck/snapshots/2026-10-28_runtime/` | 装机记录 + 注册信息 + 实测数据 + 黑洞/重启观察（含隐私核对） |
| 手册 14/15/16/17、`docs/manual/README.md`、`scripts/duck/README.md` | 连接方式/巡检项/网页地址/清单状态同步 |

## 隐私核对

- [x] 无密码（鸭子 sudo、服务器 root）、无 preauth key（一次性、装机时已消耗）、无私钥
- [x] 出现的 IP 仅为 tailnet 内网段与团队已知路由器/出口信息，与 network.md 已公开内容同级
