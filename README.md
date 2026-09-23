# Microduck 生态研究工作区

围绕 [Pollen Robotics](https://github.com/pollen-robotics) 的 microduck 双足机器人（~800 g、~25 cm 高）
建立的本地研究环境。搭建于 2026-09-23，纯 CPU 环境（无 NVIDIA GPU：可以 **play** policy，不能本地训练）。

## 目录结构

| 路径 | 内容 |
|---|---|
| `microduck_rl/` | 官方 RL 训练仓库（Python 3.12 + uv，已配好依赖） |
| `microduck/` | 官方机器人运行时仓库（Rust：robotd 守护进程、robotctl 等，浅克隆仅供阅读） |
| `policies/official/` | 从 HF `pollen-robotics/microduck-policies` 下载的 10 个官方 ONNX policy |
| `notes/` | 研究笔记，从 [00_快速上手.md](notes/00_快速上手.md) 开始读 |
| `play.sh` | 一键启动器，在 CPU MuJoCo 里键盘操控官方 policy |
| `update.sh` | 一键同步三个官方来源（两个 GitHub 仓库 + HF policies）到最新 |

## 30 秒上手

```bash
cd ~/research/microduck
./play.sh walk        # 弹出 MuJoCo 窗口, 在终端里按方向键让小鸭子走路
```

详细说明（含全部模式、键盘控制表、常见问题）：**[notes/00_快速上手.md](notes/00_快速上手.md)**
