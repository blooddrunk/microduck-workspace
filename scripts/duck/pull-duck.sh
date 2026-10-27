#!/usr/bin/env bash
# pull-duck.sh —— 把鸭子的实况拉回仓库（对鸭子完全只读，绝不 --delete）
#
# 三档内容，可组合：
#   scripts/duck/pull-duck.sh                # 默认：sanitized 快照 -> duck/snapshots/<日期>_runtime/
#                                            #   （小体量文本：系统/网络/服务/文件树/标定 toml，
#                                            #     不含任何密码；人工审阅后才 git commit）
#   scripts/duck/pull-duck.sh --code         # 追加：家目录白名单代码 -> .evidence/duck-sync-<ts>/（不入库）
#   scripts/duck/pull-duck.sh --policies     # 追加：策略权重 -> local/duck-policies-<ts>/（不入库）
#
# 白名单在 local/duck.env 的 DUCK_PULL_DIRS 里改（默认 .config/microduck,microduck,duck,projects）。
# 排除项固定包含：venv/缓存/.git/数据集/视频/模型大文件（模型走 --policies 单独拉）。
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

DO_CODE=0; DO_POLICIES=0
for a in "$@"; do
  case "$a" in
    --code) DO_CODE=1 ;;
    --policies) DO_POLICIES=1 ;;
    *) echo "未知参数: $a（可用: --code --policies）" >&2; exit 2 ;;
  esac
done

TS_DATE="$(date +%F)"
SNAP_DIR="$REPO_ROOT/duck/snapshots/${TS_DATE}_runtime"
EVID_DIR="$REPO_ROOT/.evidence/duck-sync-$(date -u +%Y%m%dT%H%M%SZ)"
RSYNC_RSH="$(rsync_ssh_args)"

# ---- 1) sanitized 快照（提交到 duck/snapshots/ 的候选内容）----------------
mkdir -p "$SNAP_DIR/calibration"
collect() { # collect <输出文件名> <远程命令>
  local out="$SNAP_DIR/$1"; shift
  printf '>>> %s\n' "$out"
  duck_run "$1" > "$out" 2>&1 || echo "[该段采集失败，见文件内容]" >> "$out"
}

collect system.txt   'uname -a; grep PRETTY /etc/os-release; uptime; free -h; df -h /'
collect network.txt  'ip -br address; echo ---; ip route; echo ---; nmcli -t -f ACTIVE,SSID,SIGNAL dev wifi 2>/dev/null || true'
# 注意：上面只取 SSID 名称，不读任何 WiFi 密码
collect services.txt 'systemctl list-units --type=service --state=running --no-legend --plain --no-pager; echo ---FAILED---; systemctl --failed --no-pager --plain --no-legend; for u in robotd padd mediad tofd btd configd gamesir-xboxd; do systemctl show $u.service --property=LoadState,ActiveState,SubState,MainPID,NRestarts 2>/dev/null | sed "s/^/[$u] /"; done'
collect files-tree.txt "find \"\$HOME\" -maxdepth 3 -not -path '*/.cache*' -not -path '*/node_modules*' -not -path '*/.venv*' 2>/dev/null | sort | head -300; echo '--- /etc,/opt 运行时目录 ---'; ls -la /etc/microduck /opt/microduck 2>/dev/null"
collect sizes.txt     "du -sh \"\$HOME\"/* 2>/dev/null | sort -h; echo ---; for d in /opt/microduck/policies \$HOME/policies \$HOME/.config/microduck/policies; do [ -d \$d ] && du -sh \$d; done"

# 标定 toml（小文件、核心档案）：逐个拉回
CAL_LIST="$(duck_run "find /etc /opt \$HOME -maxdepth 4 -name '*calibration*.toml' 2>/dev/null | head -10" || true)"
if [[ -n "$CAL_LIST" ]]; then
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    safe="$(echo "$f" | tr '/' '_' | sed 's/^_//')"
    printf '>>> calibration/%s\n' "$safe"
    duck_run "cat '$f'" > "$SNAP_DIR/calibration/$safe" 2>/dev/null || true
  done <<< "$CAL_LIST"
fi

# 运行时配置（/etc/robot 全部 toml）与策略 provenance（models/*/manifest 等 json）
mkdir -p "$SNAP_DIR/etc-robot" "$SNAP_DIR/models"
for f in /etc/robot/robotd.toml /etc/robot/feetech-ft5/robotd.toml \
         /etc/robot/feetech-ft5/robotd.previous.toml /etc/robot/feetech-ft5/robotd.saved.toml; do
  if duck_run "test -r '$f'"; then
    safe="$(echo "$f" | sed 's|^/etc/robot/||; s|/|_|g')"
    printf '>>> etc-robot/%s\n' "$safe"
    duck_run "cat '$f'" > "$SNAP_DIR/etc-robot/$safe" || true
  fi
done
duck_run 'for d in /opt/robot/feetech-ft5-r5/models/*/; do echo "### $d"; for f in manifest.json deployment-contract.json deployment-runtime.json deployment-profile.toml deployment-execution.json training-request.json; do [ -r "$d$f" ] && { echo "--- $f"; cat "$d$f"; }; done; done 2>/dev/null' \
  > "$SNAP_DIR/models/provenance.txt" || true
duck_run 'head -40 /opt/robot/feetech-ft5-r5/BUILD.json 2>/dev/null' > "$SNAP_DIR/models/build-version.txt" || true

cat > "$SNAP_DIR/README.md" <<EOF
# ${TS_DATE} 鸭子运行时快照（sanitized）

- 采集方式：\`scripts/duck/pull-duck.sh\`（对鸭子只读；未发送任何控制命令）
- 目标：${DUCK_USER}@${DUCK_HOST}${DUCK_JUMP:+ （经跳板 ${DUCK_JUMP}）}
- 内容：system/network/services/files-tree/sizes + calibration toml
- 提交前人工核对：不应包含密码、私钥、个人路径中的真实姓名等。
EOF

echo ">>> sanitized 快照完成: $SNAP_DIR（审阅后可 git commit）"

# ---- 2) 家目录代码白名单（raw，只进 .evidence/）---------------------------
if [[ $DO_CODE -eq 1 ]]; then
  IFS=',' read -ra DIRS <<< "${DUCK_PULL_DIRS:-.config/microduck,microduck,duck,projects}"
  DEST="$EVID_DIR/code"
  mkdir -p "$DEST"
  for d in "${DIRS[@]}"; do
    [[ -z "$d" ]] && continue
    echo ">>> rsync 拉取 ~/$d -> $DEST/$d"
    rsync -a --info=stats1 --max-size=8m -e "$RSYNC_RSH" \
      --exclude '.git' --exclude '__pycache__' --exclude '.venv' --exclude 'node_modules' \
      --exclude '.cache' --exclude '.claude*' --exclude '*.mp4' --exclude '*.bag' --exclude 'datasets' \
      "$(duck_ssh_target):~/$d/" "$DEST/$d/"
  done
  echo ">>> raw 代码已拉到 $DEST（.evidence/ 不入库；需要沉淀的部分人工拷贝/脱敏到 duck/ 或上游）"
fi

# ---- 3) 策略权重（大文件，只进 local/）------------------------------------
# 板上策略的真实位置（2026-10-27 实测）：
#   /opt/robot/feetech-ft5-r5/models/<hash>/policy.onnx  kissqy R5 部署的 HD1910 策略
#   /opt/robot/feetech-ft5-r5/roller/                     滑轮技能策略
#   /opt/robot/policies/releases/seed-v5/                 官方 XL330 风格种子策略（随镜像）
#   /opt/robot/detector/releases/seed-duck-v1/            duck_detect.onnx
if [[ $DO_POLICIES -eq 1 ]]; then
  DEST="$REPO_ROOT/local/duck-policies-$(date +%Y%m%d)"
  mkdir -p "$DEST"
  echo ">>> rsync 拉取 /opt/robot 策略 -> $DEST"
  rsync -a --info=stats1 --max-size=15m -e "$RSYNC_RSH" \
    "$(duck_ssh_target):/opt/robot/feetech-ft5-r5/models/" "$DEST/feetech-ft5-r5-models/"
  rsync -a --info=stats1 --max-size=15m -e "$RSYNC_RSH" \
    "$(duck_ssh_target):/opt/robot/feetech-ft5-r5/roller/" "$DEST/feetech-ft5-r5-roller/"
  rsync -a --info=stats1 --max-size=15m -e "$RSYNC_RSH" \
    "$(duck_ssh_target):/opt/robot/policies/releases/" "$DEST/official-seed-releases/"
  rsync -a --info=stats1 --max-size=15m -e "$RSYNC_RSH" \
    "$(duck_ssh_target):/opt/robot/detector/releases/" "$DEST/duck-detect/"
  echo ">>> 策略已拉到 $DEST（local/ 不入库；公开仓库不放第三方权重，许可与体积原因）"
fi
