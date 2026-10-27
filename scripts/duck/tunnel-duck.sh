#!/usr/bin/env bash
# tunnel-duck.sh —— 维持一条到鸭子的后台 SSH 隧道（断线自动重连）
#
# 适用：鸭子在 GL 路由器（Tailscale 可达但中继偶发抖动）后面的 192.168.8.x 网段。
# 原理：ssh -N -L 127.0.0.1:2222:<鸭子IP>:22 root@<路由器Tailscale IP>
#       只要成功连上一次，之后本机所有工具都走 127.0.0.1:2222（见 local/duck.env 的 DUCK_TUNNEL=1）。
# 前提：路由器上已装好本机公钥（set by setup: 见 docs/manual/14-connect-duck.md）。
#
# 用法：
#   scripts/duck/tunnel-duck.sh &          # 后台常驻；日志在 /tmp/duck-tunnel.log
#   DUCK_REAL_IP=192.168.8.161 DUCK_ROUTER=root@100.64.0.8 scripts/duck/tunnel-duck.sh
set -euo pipefail

ROUTER="${DUCK_ROUTER:-root@100.64.0.8}"
REAL_IP="${DUCK_REAL_IP:-192.168.8.161}"
LOCAL_PORT="${DUCK_TUNNEL_PORT:-2222}"
MAX_RETRY="${DUCK_TUNNEL_RETRIES:-30}"

for i in $(seq 1 "$MAX_RETRY"); do
  echo "[tunnel] attempt $i $(date +%T)"
  ssh -N -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
      -o ExitOnForwardFailure=yes -L "127.0.0.1:${LOCAL_PORT}:${REAL_IP}:22" "$ROUTER"
  echo "[tunnel] dropped (exit=$?), 5s 后重连"
  sleep 5
done
echo "[tunnel] 达到最大重试次数，退出" >&2
