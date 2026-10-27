#!/usr/bin/env bash
# scripts/duck/lib.sh —— 鸭子连接公共库（被其他 duck-*.sh source，不直接运行）
#
# 目标：多人协作时每人只需维护一份本机配置 local/duck.env（已被 .gitignore 忽略），
#       所有鸭子脚本共享同一套连接逻辑：直连 / 经路由器跳板（-J）/ 自定义端口。
#
# 安全约定：
#   * 本库只构造 ssh/scp/rsync 命令行，绝不保存密码（这是公开仓库！）。
#   * 默认全部走只读操作；唯一例外是显式运行 setup-key-duck.sh 或 push-duck.sh --apply。
#   * 密码登录只在首次 setup 时人工输入；日常统一用 SSH 密钥。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# ---- 配置加载顺序：环境变量 > local/duck.env > 默认值 --------------------
DUCK_USER="${DUCK_USER:-radxa}"
DUCK_HOST="${DUCK_HOST:-}"          # 鸭子 IP 或主机名，例如 192.168.8.161
DUCK_PORT="${DUCK_PORT:-22}"
DUCK_JUMP="${DUCK_JUMP:-}"          # 可选跳板，例如 root@100.64.0.8（GL 路由器的 Tailscale IP）
DUCK_SSH_OPTS="${DUCK_SSH_OPTS:-}"  # 额外 ssh 选项，例如 '-o ConnectTimeout=5'

# local/duck.env 不入库，模板见 scripts/duck/duck.env.example
if [[ -z "${DUCK_HOST}" && -f "$REPO_ROOT/local/duck.env" ]]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/local/duck.env"
fi

# ---- 组装 ssh / rsync 参数 ------------------------------------------------
# 两种连接模式：
#   direct（默认）：直连 DUCK_HOST:DUCK_PORT，可选经 DUCK_JUMP 跳板。
#   tunnel：连本机 127.0.0.1:DUCK_TUNNEL_PORT（由 tunnel-duck.sh 维持的后台隧道）。
#           适合路由器 Tailscale 中继不稳定、或鸭子在异地网段的场景。
if [[ "${DUCK_TUNNEL:-0}" == "1" ]]; then
  DUCK_HOST=127.0.0.1
  DUCK_PORT="${DUCK_TUNNEL_PORT:-2222}"
  DUCK_JUMP=""
fi

duck_ssh_target() {
  if [[ -z "${DUCK_HOST}" ]]; then
    echo "错误：未配置鸭子地址。请设置环境变量 DUCK_HOST 或复制 scripts/duck/duck.env.example 到 local/duck.env 后填写。" >&2
    exit 2
  fi
  echo "${DUCK_USER}@${DUCK_HOST}"
}

# ssh 公共参数（bash 数组，供 "${SSH_CMD[@]}" 展开）
ssh_common_args() {
  local -a args=(-p "$DUCK_PORT"
    -o BatchMode=yes                 # 只用密钥，避免脚本卡在密码提示
    -o ConnectTimeout="${DUCK_CONNECT_TIMEOUT:-8}"
    -o StrictHostKeyChecking=accept-new)
  if [[ -n "${DUCK_JUMP}" ]]; then
    args+=(-J "$DUCK_JUMP")
  fi
  if [[ -n "${DUCK_SSH_OPTS}" ]]; then
    # shellcheck disable=SC2206
    args+=(${DUCK_SSH_OPTS})
  fi
  echo "${args[@]}"
}

# 运行远程命令：duck_run 'uname -a'
duck_run() {
  local -a args
  # shellcheck disable=SC2206
  args=($(ssh_common_args))
  ssh "${args[@]}" "$(duck_ssh_target)" "$@"
}

# 交互式登录：duck_shell
duck_shell() {
  local -a args
  # shellcheck disable=SC2206
  args=($(ssh_common_args))
  exec ssh "${args[@]}" "$(duck_ssh_target)"
}

# rsync 的 -e 参数（与 ssh 公共参数同一套跳板/端口配置，作为单个字符串传给 rsync）
rsync_ssh_args() {
  local extra="${DUCK_SSH_OPTS:+ $DUCK_SSH_OPTS}"
  echo "ssh -p $DUCK_PORT${DUCK_JUMP:+ -J $DUCK_JUMP}${extra} -o BatchMode=yes -o ConnectTimeout=${DUCK_CONNECT_TIMEOUT:-8} -o StrictHostKeyChecking=accept-new"
}
