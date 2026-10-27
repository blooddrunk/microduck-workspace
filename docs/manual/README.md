# 实用手册系列（初学者友好）

> 这套手册面向**第一次接触这只鸭子的新队友**：怎么连上它、怎么看懂它的状态、怎么让它动起来、
> 怎么和团队协作开发。硬件验收/分级通电等安全流程仍以 [docs/00–13](../00_START_HERE.md) 为准；
> 手册是日常操作层，不替代安全闸门。
>
> 最后更新：2026-10-27（基于当日只读巡检实测）。

## 手册导航

| 编号 | 手册 | 什么时候看 |
|---|---|---|
| 14 | [连接鸭子：网络与 SSH](14-connect-duck.md) | 第一次要登录鸭子 / 连不上了 |
| 15 | [鸭子状态巡检手册](15-duck-state-check.md) | 想知道鸭子现在物理/网络/运行时状态 |
| 16 | [网页中控与策略运行](16-web-and-policies.md) | 想让鸭子站起来走两步 |
| 17 | [多人协作、同步与优化清单](17-team-workflow.md) | 要写代码/改配置/提建议 |

## 30 秒版（老手直接抄）

```bash
# 连接（隧道模式，异地可用）
scripts/duck/tunnel-duck.sh &           # 一次，保持后台
scripts/duck/ssh-duck.sh                # 登录
scripts/duck/status-duck.sh --save      # 只读巡检并留档
scripts/duck/pull-duck.sh               # 快照拉回仓库 duck/snapshots/

# 让鸭子动（现场、有人扶着）
# 手机/电脑连 GL-MT3600BE-5e4 → 浏览器 http://192.168.8.161:8080 → 手柄/按钮控制
```

## 鸭子是谁（速记卡）

- 名字 `duck-a437`（SSH 主机名 `microduck`），Radxa ZERO 3W + 15× 飞特 HD-1910 + 头部 ToF + 摄像头 + IMU
- 系统：Armbian 26.2.1 + kissqy R5 运行时（robotd 等服务）
- 状态：已组装、已标定（`motion_enabled=true`）、能走能翻滚，语音控制在研
- 网络身份与连接方式见 [duck/network.md](../../duck/network.md)
