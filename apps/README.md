# apps/ —— 应用正本目录

**代码正本放这里，鸭子板上只有部署副本。** 这是 [手册 17 §1](../docs/manual/17-team-workflow.md)
约定的落地：板上目录是"运行现场"，任何要在鸭子上长驻/上板运行的应用程序（语音、视觉、
操控辅助、巡检 agent 等），其可版本化的正本一律放 `apps/<名字>/`，经
[push-duck.sh](../scripts/duck/push-duck.sh) 白名单部署上板。

## 什么放这里，什么不放

| 内容 | 放不放 | 应放位置 |
|---|---|---|
| 在鸭子上运行的应用代码（Python/Bash 服务、CLI） | ✅ | `apps/<名字>/` |
| 应用自带的 systemd unit、部署说明 | ✅ | `apps/<名字>/deploy/` |
| 硬件/仿真教程、操作手册 | ❌ | `docs/`、`docs/manual/` |
| 只读诊断与验证脚本（不部署上板的） | ❌ | `scripts/` |
| 鸭子实况快照、标定档案 | ❌ | `duck/snapshots/` |
| 模型权重、数据集等大件 | ❌ | `local/`（不入库），记录里写路径与 SHA256 |
| 密钥、`.env`、令牌 | ❌ 永不 | 各人 `local/`；板上密钥只在板上 |

## 单应用布局契约

```
apps/<名字>/                 # 小写连字符命名（duck-voice、sherpa-asr…）
├── README.md               # 必备：做什么、依赖、本机怎么跑、怎么上板、怎么回滚
├── requirements.txt        # Python 应用必备（含版本锚定）；Bash 应用可省略
├── deploy/                 # 可选：systemd unit 模板、上板步骤、回滚步骤
└── （源码）
```

新建应用直接拷贝 [_template/](_template/) 起步。**`.env*`、`.venv/` 已被根 `.gitignore`
统一排除**——本地调试用的密钥文件随便放，但永远进不了 Git。

## 部署流（仓库 → 鸭子）

```bash
# 1) 本机 local/duck.env 的白名单加上应用目录（逗号分隔）：
#    DUCK_PUSH_DIRS=scripts/duck/remote,apps/duck-voice
# 2) 演练 → 确认 → 执行（只进鸭子 ~/microduck-tools/<名字>/，自动排除 .env/.venv/__pycache__）：
scripts/duck/push-duck.sh
scripts/duck/push-duck.sh --apply
```

在鸭子家目录直接改了应用代码的，收工前 `pull-duck.sh --code` 拉回，人工把改动合入
`apps/` 正本再 commit——不要让板上副本漂移成新正本。

## 与板上个人开发子目录的关系（2026-10-28 决定）

鸭子家目录里按人命名的开发目录（`~/zhangtong/`、`~/voice/`、`~/shishaodong/`）
**保持不变**：本次只建架构、不搬迁。各负责人愿意把项目版本化时，自行拷入
`apps/<名字>/`（清理密钥与大件后 commit），届时更新 [CHECKLIST](../CHECKLIST.md)
对应条目并按手册 16 §5 流程重新部署。
