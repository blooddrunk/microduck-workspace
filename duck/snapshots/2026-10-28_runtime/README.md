# 2026-10-28 网络变更增量快照：鸭子本体安装 Tailscale

- 内容：把鸭子本体加入团队自建 Headscale（`hs-nosla.haoqi90.top`）的装机记录、
  注册信息与双向连通实测数据。对应 CHECKLIST P0 项「鸭子本体安装 Tailscale」。
- 操作方式：`ssh radxa@192.168.8.161`（本机已装公钥）+ Headscale 服务器 CLI + GL 路由器只读复核；
  除安装/注册本身外未发送任何机器人控制命令。
- 详细档案见 [duck/network.md](../../network.md)（§2/§6 已同步更新）。

## 内容

| 文件 | 说明 |
|---|---|
| `tailscale-status.txt` | 版本/IP/注册信息/偏好项/连通性实测/控制面瞬断观察/当日板子状态 |

## 一句话结论

鸭子在 tailnet 里固定为 **`100.64.0.12`**（headscale 节点 ID 17，`home` 命名空间），
任何 tailnet 机器可直达其 SSH(22) 与网页中控(8080)；`tailscaled` 已设开机自启，
板子重启后自动回网。异地协作不再依赖 GL 路由器中继（B/C 方式降级为兜底）。

## 隐私核对（提交前人工过目）

- [x] 无任何密码（鸭子 sudo 密码、服务器 root 密码均未出现）
- [x] 无 preauth key（一次性、装机时已消耗，且未写入任何文件）
- [x] 无私钥/authorized_keys 内容
- [x] `tailscale status` 输出仅含 tailnet 内网 IP 与主机名（与 network.md 已公开信息同级）
