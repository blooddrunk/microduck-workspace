# 16 · 网页中控与策略运行：让鸭子站起来走两步

> 目标：安全地用网页/手柄驱动鸭子，理解"策略"是什么、现在装了哪些、怎么换。
> ⚠️ 前提三件事：鸭子放地上有支撑/有人扶、周围 1 米清空、知道急停怎么按。

## 1 急停与安全（先读这个，再碰鸭子）

- **网页中控里有急停/释放按钮**；实体手柄（GameSir，经 `gamesir-xboxd` 桥接）断开或超时，
  robotd 的 deadman 会**自动把速度清零并卸力**（日志里的 `intents went stale` 就是它在工作）。
- `motion_enabled = true` 表示一上电、给指令就会动。**拿起鸭子前先在网页里松开使能。**
- 绝对不要：隔着网线远程"试试能不能走"而现场没人；在桌上/高处测试；舵机卡死还持续给指令。
- 更完整的分级通电/运动安全合同：[docs/03](../03_POWER_INTEGRATION.md)。

## 2 打开网页中控

1. 打开网页中控（任选其一）：
   - tailnet 机器（**推荐**，现场/异地都行）：**`http://100.64.0.12:8080`**
   - 现场：手机/电脑连 WiFi `GL-MT3600BE-5e4`（和鸭子同一网络）后开 `http://192.168.8.161:8080`
2. 首次使用会让你配对/登录（按页面提示；蓝牙 PIN 用 `robotctl system pin` 可查）。

> 兜底（鸭子本体 tailscale 掉线 + 中继抖动时）：端口转发
> `ssh -N -L 8080:192.168.8.161:8080 root@100.64.0.8` 后访问 `http://127.0.0.1:8080`。
> （但**异地遥控鸭子是被禁止的**——现场必须有人。）

中控能做什么（R5 版实测功能面）：实时状态面板（关节角/电池/温度）、虚拟手柄走路、
技能按钮（坐下/捡东西/踢球/翻滚）、相机画面（mediad 正常时）、标定引导。

## 3 用手柄走路（推荐，响应最快）

- 实体 GameSir 手柄配对后由 `gamesir-xboxd` 桥接成 Xbox 输入，`padd` 把输入变成意图喂给 robotd。
- 网页里的虚拟手柄走常驻 SSH 通道（R157 之后不再有 webpad 服务）。
- 第一次先**原地站立 → 微动摇杆 → 慢走**；发现异常（单腿软、异响、前倾不受控）立即松手，
  deadman 会接管。

## 4 策略（policy）是什么、装了哪些

策略 = 训练出来的神经网络（ONNX，约 780KB 一个），robotd 以 50Hz 读 IMU/关节/指令，
推理出 14 个关节目标角。当前装配（`/etc/robot/feetech-ft5/robotd.toml`，2026-10-27 实测）：

| 模式/技能 | 模型目录（/opt/robot/feetech-ft5-r5/models/ 下 hash） | 训练出处 |
|---|---|---|
| `mode = "walk"`（主行走） | `1cbf8730…` VelStand-Rough-Backlash | 2026-10-01 自训 |
| sitstand 坐站 | `1c94934c…` SitStand-Flat | 2026-10-01 自训 |
| ground_pick 捡东西 | `b14e3a8b…` GroundPick-Flat-Backlash | 2026-10-01 自训 |
| kick_left / kick_right 踢球 | `ee0376c9…` / `67ad09d8…` | 2026-10-01 自训 |
| roulade 前滚翻 | `59e15d7b…` Roulade-Flat | 2026-10-01 自训 |
| roller_* 轮滑技能 | `roller/{crouch,standup,spin}/` | 随镜像 |

增益参数：`gain = 5`、`action_scale = 0.7`（站立 1.0）——动得更稳但更保守可调小，
**改这些要现场试、一次只改一个**。

> "2026-10-01 自训"指这些模型出自 microduck-training-studio（kissqy 训练台）的
> rsl_rl 训练日志；完整 provenance 见
> [duck/snapshots/2026-10-27_runtime/models/provenance-manifests.txt](../../duck/snapshots/2026-10-27_runtime/models/provenance-manifests.txt)。
> 权重文件在本机 `local/duck-policies-20261027/`（不入公开仓库）。

## 5 换一个策略上机（高危操作，两人一组）

1. **现场**：鸭子坐下/趴下、松使能，断开手柄。
2. 把新 `policy.onnx` 放到鸭子 `/opt/robot/feetech-ft5-r5/models/<新hash>/policy.onnx`
   （hash 目录名随意但唯一；同目录放 manifest.json 记录来源）。
3. 改 `/etc/robot/feetech-ft5/robotd.toml` 对应模式指向新路径（先 `cp` 备份原 toml）。
4. `sudo systemctl restart robotd`（唯一需要重启的服务），看 `journalctl -u robotd -f` 无报错。
5. 现场扶着鸭子、低增益先试站立，再逐步放开。
6. 完成后 `scripts/duck/pull-duck.sh` 把新配置存档进仓库。

**回滚**：把 toml 里路径改回旧 hash（`.previous.toml`/`.saved.toml` 是历史档），restart robotd。

## 6 语音控制现状（在研）

- 板上常驻 `voice_chat.py --wake-keep 20`（来源 `~/zhangtong/duck-voice`）：
  唤醒词 → ASR → `intent.py` 解析 → 转成 robotd 指令。
- 代码组件：`stt.py`（讯飞流式 `stt_xfyun.py` + 大模型中文识别）、`tts.py`、`duck.py`、
  `audio_io.py`，systemd 单元 `duck-voice.service`。
- 已拉回仓库侧（不入库，含 `.env` 密钥）的位置：`.evidence/duck-sync-*/code/`。
- 注意：语音进程和 mediad 都抢音频设备，是 mediad 崩溃循环的嫌疑之一（手册 15 §6）。
