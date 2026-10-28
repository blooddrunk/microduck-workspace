#!/usr/bin/env bash
# push-duck.sh —— 把仓库里“允许上鸭”的内容推到鸭子（白名单 + 默认演练）
#
# 安全合同（多人协作的底线）：
#   1. 只推 local/duck.env 里 DUCK_PUSH_DIRS 白名单中的目录（默认 scripts/duck/remote），
#      目标固定为鸭子家目录 ~/microduck-tools/——绝不写 /etc、/opt、系统服务。
#   2. 默认 DRY-RUN：只打印将发生的变更；确认无误后加 --apply 才真正执行。
#   3. 永不 --delete、永不 restart/stop 服务；推上去的脚本要不要在鸭子执行，由人决定。
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1
[[ $# -gt 0 && "${1:-}" != "--apply" ]] && { echo "用法: push-duck.sh [--apply]"; exit 2; }

IFS=',' read -ra DIRS <<< "${DUCK_PUSH_DIRS:-scripts/duck/remote}"
RSYNC_RSH="$(rsync_ssh_args)"
FLAGS="-av"          # 默认 dry-run 由下面 APPLY 控制
[[ $APPLY -eq 1 ]] || FLAGS="$FLAGS -n"

for d in "${DIRS[@]}"; do
  [[ -z "$d" ]] && continue
  SRC="$REPO_ROOT/$d"
  if [[ ! -d "$SRC" ]]; then
    echo "跳过（本地不存在）: $d"
    continue
  fi
  # 白名单校验：解析后必须仍在仓库内，防止配置写 ../ 逃逸
  case "$(realpath "$SRC")" in
    "$REPO_ROOT"/*) ;;
    *) echo "拒绝（越出仓库白名单）: $d" >&2; exit 2 ;;
  esac
  NAME="$(basename "$d")"
  echo ">>> rsync $FLAGS $( [[ $APPLY -eq 1 ]] && echo '[执行]' || echo '[演练]' ) $d -> 鸭子:~/microduck-tools/$NAME/"
  # 密钥与本机缓存默认不上板：apps/ 正本里的 .env 属于开发机，鸭子侧密钥在板上单独维护
  rsync $FLAGS --info=stats1 \
    --exclude='.env' --exclude='.env.*' --exclude='.venv/' --exclude='__pycache__/' \
    -e "$RSYNC_RSH" "$SRC/" "$(duck_ssh_target):~/microduck-tools/$NAME/"
done

if [[ $APPLY -eq 0 ]]; then
  echo
  echo "以上为演练（dry-run）。确认后执行: scripts/duck/push-duck.sh --apply"
fi
