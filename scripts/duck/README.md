# scripts/duck —— 鸭子一键工具集

> 配套手册：[docs/manual/17-team-workflow.md](../../docs/manual/17-team-workflow.md)（多人协作与同步流程）。
> 所有工具对鸭子**只读优先**：唯一例外是 `setup-key-duck.sh`（追加一把公钥）与 `push-duck.sh --apply`（白名单目录推到家目录），都需人工确认。

## 30 秒上手（新人第一次）

```bash
# 1) 生成本机密钥（已有可跳过）
ssh-keygen -t ed25519

# 2) 建立本机配置（不入库）
cp scripts/duck/duck.env.example local/duck.env
$EDITOR local/duck.env          # 填 DUCK_HOST：tailnet 成员可直接写 100.64.0.12；否则扫网段填 LAN IP

# 3) 装公钥（输入一次鸭子密码）并验证
scripts/duck/setup-key-duck.sh
scripts/duck/ssh-duck.sh 'hostname'

# 4) 日常：一键巡检 / 拉快照
scripts/duck/status-duck.sh --save
scripts/duck/pull-duck.sh
```

## 工具一览

| 脚本 | 方向 | 作用 | 对鸭子的写入 |
|---|---|---|---|
| `find-duck.sh [网段]` | 本机 | 扫 22/8088 端口 + ARP 匹配 Radxa MAC 前缀，找到鸭子当前 IP | 无 |
| `ssh-duck.sh [命令]` | 双向 | 登录或执行单条远程命令（自动带配置/跳板） | 无 |
| `tunnel-duck.sh` | 本机 | 后台维持 127.0.0.1:2222 → 鸭子:22 的自动重连隧道（无 tailnet / 黑洞窗口期兜底；`DUCK_TUNNEL=1` 后所有工具自动走它） | 无 |
| `status-duck.sh [--save]` | 拉 | 9 段只读巡检（系统/网络/服务/标定/设备/日志/电源…），`--save` 留档 `.evidence/` | 无 |
| `pull-duck.sh [--code --policies]` | 拉 | sanitized 快照进 `duck/snapshots/`；`--code`/`--policies` 拉大件到不入库目录 | 无 |
| `push-duck.sh [--apply]` | 推 | 白名单目录推到 `~/microduck-tools/`；默认 dry-run；自动排除 `.env*`/`.venv`/`__pycache__` | 仅家目录白名单路径 |
| `setup-key-duck.sh` | 推 | 一次性安装本机公钥（之后全部免密） | 仅 `~/.ssh/authorized_keys` |

## 约定（多人协作的关键）

1. **配置各管各的**：IP、跳板、白名单都写在 `local/duck.env`（`.gitignore` 已忽略），别提交。
2. **密码永不入库**：这是公开仓库。鸭子密码、路由器密码、WiFi 密码都不写进脚本和文档正文。
3. **拉取不删除**：rsync 一律不带 `--delete`，鸭子上的东西只增不删。
4. **快照先审后提交**：`pull-duck.sh` 生成的 `duck/snapshots/<日期>_runtime/` 须人工核对无隐私后再 commit。
5. **运行时红线**：巡检脚本不 start/stop/restart 任何服务、不 `robotctl` 控制舵机、不打开串口/I2C。需要动运行时 → 先在群里打招呼、按 [docs/03](../../docs/03_POWER_INTEGRATION.md) 的分级通电流程来。

## `remote/` 子目录

放"设计为在鸭子板上运行"的脚本（比如离线语音模型安装器）。它默认在 `push-duck.sh` 白名单里；
推上去之后在鸭子 `~/microduck-tools/` 下手动执行，执行前先 `bash -n` 检查语法、读懂每一行。
