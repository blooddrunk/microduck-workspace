# AGENTS.md —— 本仓库 AI 协作规则（agent 与人通用）

> 一句话：**公开仓库 + 一只会动的真鸭子**。安全与隐私优先，结论必须有证据。
> 本文件只放不变的红线与高频陷阱；操作细节以文末「权威文档索引」为准，不要凭记忆复述。

## 0 红线（违反即事故）

1. **鸭子是通电动真格的机器人**（`motion_enabled=true`，一上电给指令就会动）：
   - 未经用户明确要求 + 现场确认，**永不**执行 `robotctl` 运动类命令、网页/手柄操控、
     `systemctl restart/stop` 运行时服务、写 `/etc/robot/`。安全流程见 `docs/03`。
   - 远程操作一律只读优先：`scripts/duck/status-duck.sh`。特权操作前先问自己
     「这会让鸭子动 / 断掉别人的会话吗」，有疑虑就停。
2. **密钥永不入库**（公开仓库）：密码、token、`.env`、私钥、大文件（权重/数据集）只进
   `local/` 或 `.evidence/`（已 gitignore）。提交前过一遍待提交内容。
3. **板上数据先脱敏再提交**：`duck/snapshots/` 与 `records/` 须过隐私核对
   （无密码/私钥/公网可定位信息/序列号）。
4. **板子会自发重启，SSH 说断就断**（已知问题，见 `duck/network.md` §5）：
   远程命令要幂等、可重入；改完必须复核；动板子前 `w` 看谁在线。

## 1 连接鸭子（2026-10-28 起）

```bash
ssh radxa@100.64.0.12        # 首选：本体 Tailscale（任何网络，需先入 tailnet）
ssh radxa@192.168.8.161      # 现场，或经 GL 子网路由的 tailnet 机器
scripts/duck/tunnel-duck.sh &   # 兜底通道（无 tailnet / 黑洞窗口期）
# 日常工具统一走 scripts/duck/*.sh（读 local/duck.env 配置）
```

## 2 高频陷阱（勿误诊）

- **连不上 ≠ 鸭子挂了**，分层测再下结论（GL `192.168.8.1` → 鸭子 → 外网 → 控制面）：
  ① 板子又在重启（等 2 分钟）；② 192.168.8.x 整段不可达 = WiFi/宿主闪断；
  ③ 仅 `hs-nosla.haoqi90.top` 超时 = 控制面 IP 黑洞窗口（几分钟～20+ 分钟自愈）。
  黑洞窗口里 tailscale 掉线是正常现象，**等它自动回网，不要反复折腾配置**。
- **8443 报错不是防火墙**：8080 能开而页面横幅报 signalling 8443 未应答 = mediad 崩溃循环
  （历史上已用 `media.source="test"` 缓解）；板上 `ss -tln | grep 8443` 为空即坐实。
- **tailscale 永不登 tailscale.com**：复装必须
  `--login-server https://hs-nosla.haoqi90.top`，否则进错 tailnet、与所有节点互不可见；
  鸭子保持默认 `--accept-routes=false`（它在 GL 通告的子网内，接受会成环）。
- 板温 55–60°C 属正常范围（`thermal_zone`，毫摄氏度）；>80°C 才是异常。

## 3 改动后必做的同步（文档即状态）

- 动了板上配置/标定/策略 → `pull-duck.sh` 重新快照 + 更新 `duck/README.md` 一页纸 +
  `records/` 脱敏记录（模板 `records/TEMPLATE.md`；结论只写 PASS/FAIL/BLOCKED，
  无证据一律 BLOCKED）。
- 网络相关新结论 → 并入 `duck/network.md` §5 排障表（唯一权威，别在别处复制细节）。
- 新进展/新问题 → 同步 `CHECKLIST.md` 与手册 17 §3 清单（完成项打 ✅ 并写日期与证据链接）。
- 新增上板应用 → `apps/<名字>/`（拷 `_template/` 起步；`.env*`/`.venv/` 已被 gitignore 与
  push-duck.sh 双重挡住）。

## 4 提交规范

- Conventional Commits（`feat:`/`fix:`/`docs:`/`chore:` + 适当前缀），直接提交 main；
  跨主题改动拆成多个逻辑提交；push 仅在用户明确要求时执行。
- 中文文档、中文 commit body 与仓库惯例一致。

## 5 权威文档索引（细节看这里）

| 主题 | 文件 |
|---|---|
| 鸭子当前状态 / 网络身份证 / 排障表 | `duck/README.md` · `duck/network.md` |
| 新人操作（连接 / 巡检 / 网页操控 / 协作清单） | `docs/manual/14–17` |
| 运维工具与只读约定 | `scripts/duck/README.md` |
| 应用正本与部署流 | `apps/README.md` |
| 优先级与待办 | `README.md` · `CHECKLIST.md` · `ROADMAP.md` |
| 存证与记录规范 | `records/TEMPLATE.md` · `records/field/README.md` |
| 硬件验收与安全闸门（参考层） | `docs/00–13` |
