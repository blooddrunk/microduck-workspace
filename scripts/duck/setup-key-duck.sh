#!/usr/bin/env bash
# setup-key-duck.sh —— 一次性把本机公钥装到鸭子上（之后所有 duck-*.sh 免密可用）
#
# 这是本工具集唯一会写鸭子文件的操作，且只追加 ~/.ssh/authorized_keys 一行，
# 不碰任何服务、配置或运行中的进程。
#
# 用法（会提示输入一次鸭子密码）：
#   scripts/duck/setup-key-duck.sh
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

PUBKEY_FILE="${PUBKEY_FILE:-$HOME/.ssh/id_ed25519.pub}"
if [[ ! -f "$PUBKEY_FILE" ]]; then
  echo "未找到公钥 $PUBKEY_FILE；先运行: ssh-keygen -t ed25519" >&2
  exit 1
fi

# 注意：这里必须允许密码交互，所以不用 lib.sh 的 BatchMode 参数
JUMP_ARGS=()
[[ -n "${DUCK_JUMP}" ]] && JUMP_ARGS=(-J "$DUCK_JUMP")

echo ">>> 将把本机公钥追加到 $(duck_ssh_target):~/.ssh/authorized_keys"
read -r -p "确认继续? [y/N] " ans
[[ "$ans" == "y" || "$ans" == "Y" ]] || exit 1

cat "$PUBKEY_FILE" | ssh "${JUMP_ARGS[@]}" -p "$DUCK_PORT" \
  -o StrictHostKeyChecking=accept-new \
  "$(duck_ssh_target)" \
  'mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && sort -u -o ~/.ssh/authorized_keys ~/.ssh/authorized_keys'

echo ">>> 完成。验证免密登录："
duck_run 'echo OK: $(whoami)@$(hostname)'
