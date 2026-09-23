# 官方 Policy 清单

来源：<https://huggingface.co/pollen-robotics/microduck-policies>（下载于 2026-09-23）
`manifest.json` 是真机的加载契约（schema 2）：每个 policy 统一为 **输入 61 维观测 → 输出 14 维关节动作**，控制频率 50 Hz。
**10 个 ONNX 已逐一实测输入均为 `[1, 61]`**，因此在 `infer_policy.py` 里加载任何一个都需要 `--new-cmd-obs`（61 维新版观测布局；不加则默认旧版 51 维，会报维度错误）。

## 与 play.sh / infer_policy.py 参数的对应关系

| 文件 | 能力 | play.sh 模式 | infer_policy.py 参数 | 触发键 |
|---|---|---|---|---|
| `alpha_walking.onnx` | 早期版本走路步态 | `walk` | `--new-cmd-obs --walking` | 方向键 |
| `alpha_stand.onnx` | 早期版本站立 | `walk` | `--new-cmd-obs --standing` | 自动（零速指令时） |
| `velstand.onnx` | **官方默认**：走路+站立+摔倒自恢复，三合一 | `velstand` 及其它 | `--new-cmd-obs --walking` | 方向键 |
| `alpha_sitstand.onnx` | 坐下↔站起（姿态标志驱动） | `sitstand` | `--sitstand`（已含 --new-cmd-obs） | Y |
| `alpha_ground_pick.onnx` | 蹲下用嘴尖点地再站起（相位驱动） | `full` | `--ground-pick` | G |
| `ball_kick_left.onnx` | 左脚踢球（场景会加载一个球） | `kick` | `--kick-left` | K |
| `ball_kick_right.onnx` | 右脚踢球 | `kick` | `--kick-right` | L |
| `roulade.onnx` | 前滚翻（越过头顶翻滚落回脚上） | `roulade` | `--roulade` | R |
| `roller.onnx` | 轮滑滑行（脚底带被动轮的机器人模型） | `roller` | `--roller --walking --action-scale 0.8` | 方向键 |
| `roller_crouch.onnx` | 轮滑中下蹲（相位驱动） | — | 不支持（由真机 daemon 驱动，`infer_policy.py` 无对应入口） | — |

## manifest.json 里值得注意的语义

- `kind`：`perpetual` = 持续运行（步态类）；`episodic` = 播放固定时长后自己回到站立；`scripted` = 由命令槽位驱动（sitstand 用 `twist.vx` 槽传 1.0/0.0 表示坐/站）。
- `slot`：装入真机 daemon 的哪个槽位（如 `walk`），运行时可热切换。
- `mode: "roller"`：需要换机器人模型 `scene_rollers.xml`（`--roller` 就是干这个的）。
- 这些 policy 的观测归一化已烘焙进 ONNX 图内——**只能用官方导出的 ONNX，不能手转 checkpoint**，否则真机/仿真看到的都是未归一化观测。
