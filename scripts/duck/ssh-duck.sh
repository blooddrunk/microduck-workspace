#!/usr/bin/env bash
# ssh-duck.sh —— 一键登录鸭子（自动加载 local/duck.env，支持跳板）
# 用法：
#   scripts/duck/ssh-duck.sh                      # 交互式登录
#   DUCK_HOST=192.168.10.50 scripts/duck/ssh-duck.sh   # 临时换个 IP
#   scripts/duck/ssh-duck.sh 'systemctl status robotd --no-pager'   # 只执行一条远程命令
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

if [[ $# -gt 0 ]]; then
  duck_run "$@"
else
  duck_shell
fi
