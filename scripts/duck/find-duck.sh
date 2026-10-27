#!/usr/bin/env bash
# find-duck.sh —— 在局域网里找到鸭子（无需装 nmap）
#
# 原理：并发探测每个 IP 的 SSH(22) 和网页中控(8088) 端口，再对本机 ARP 表
#       匹配 Radxa 无线网卡 MAC 前缀 cc:c8:37（2026-10-14 实测我们这只鸭子）。
#
# 用法：
#   scripts/duck/find-duck.sh                       # 扫默认网段（自动取本机网段 /24）
#   scripts/duck/find-duck.sh 192.168.8.0/24        # 指定网段（只支持 /24 写法）
#   scripts/duck/find-duck.sh 192.168.8             # 同上的简写
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

if [[ $# -ge 1 ]]; then
  BASE="${1%.0/24}"; BASE="${BASE%/24}"
else
  # 取本机默认路由所在网段
  BASE="$(ip route | awk '/default via/ {split($3,a,"."); print a[1]"."a[2]"."a[3]; exit}')"
fi
echo ">>> 扫描 ${BASE}.1-254 的 22/8088 端口…"

scan_ip() {
  local ip="$1"
  for port in 22 8088; do
    if timeout 1 bash -c "echo >/dev/tcp/$ip/$port" 2>/dev/null; then
      printf "%s:%s OPEN\n" "$ip" "$port"
    fi
  done
}
export -f scan_ip

RESULTS="$(seq 1 254 | xargs -P 64 -I{} bash -c 'scan_ip '"$BASE"'.{}' 2>/dev/null || true)"
echo "$RESULTS"

echo "--- ARP 表中匹配 Radxa 无线 MAC 前缀 (cc:c8:37) 的设备 ---"
ip neigh | grep -i "cc:c8:37" || echo "（本机 ARP 表暂无；open 端口的 IP 里没扫到时，可先 ping 一遍再重试）"

if echo "$RESULTS" | grep -q ":22 OPEN"; then
  echo "提示：对候选 IP 逐个试: scripts/duck/ssh-duck.sh 加 DUCK_HOST=<ip> 'hostname'，回显 radxa 主机名即为鸭子。"
fi
