#!/usr/bin/env bash
# status-duck.sh —— 鸭子运行时一键巡检（严格只读，绝不发送任何控制命令）
#
# 设计原则（与 scripts/diagnose_radxa.py 的白名单一致）：
#   * 只执行读取类命令：看系统/网络/服务状态、列出设备与文件、tail 日志。
#   * 不 open 串口/I2C、不 i2cdetect、不 systemctl start/stop/restart、
#     不 robotctl / 不碰舵机、不写任何文件（--save 只写本机 .evidence/）。
#
# 用法：
#   scripts/duck/status-duck.sh            # 打印到终端
#   scripts/duck/status-duck.sh --save     # 同时留档到 .evidence/duck-status-<时间戳>/
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

# 远程只读脚本（POSIX sh）。每条命令都容错，避免某一项缺失导致整体中断。
REMOTE_STATUS_SCRIPT='
section() { printf "\n===== %s =====\n" "$1"; }
run() { printf "\$ %s\n" "$*"; "$@" 2>&1 || printf "  [不可用/失败: %s]\n" "$*"; }

section "1 身份与系统"
run hostname
run uname -a
grep PRETTY_NAME /etc/os-release 2>/dev/null || true
cat /etc/armbian-release 2>/dev/null | head -5 || true
run uptime
run date

section "2 资源（内存/磁盘/温度/负载）"
run free -h
run df -h /
for z in /sys/class/thermal/thermal_zone*; do
  [ -r "$z/temp" ] && printf "%s: %s mC\n" "$z" "$(cat "$z/temp")"
done 2>/dev/null || true
ps aux --sort=-%cpu 2>/dev/null | head -6 || true

section "3 网络（当前鸭子视角）"
run ip -br address
run ip route
(nmcli -t -f ACTIVE,SSID,SIGNAL,CHAN dev wifi 2>/dev/null || iwgetid -r 2>/dev/null || true)
cat /etc/resolv.conf 2>/dev/null | grep -v "^#" | head -5 || true

section "4 运行时服务（发现 + 关键单元详情）"
systemctl list-units --type=service --state=running --no-legend --plain --no-pager 2>/dev/null \
  | grep -Ei "robot|duck|padd|media|tof|btd|config|gamesir|aic|voice|hotspot|console|web" || true
for u in robotd padd mediad tofd btd configd gamesir-xboxd; do
  systemctl show "$u.service" --no-pager \
    --property=LoadState,ActiveState,SubState,MainPID,NRestarts,ExecMainStartTimestamp 2>/dev/null \
    | sed "s/^/[$u] /" || true
done
run systemctl --failed --no-pager --plain --no-legend

section "5 关键文件与标定（只列目录/大小/安全开关，不改内容）"
for p in /etc/microduck /etc/robotd /opt/microduck "$HOME/.config/microduck" "$HOME/microduck" "$HOME/duck"; do
  if [ -e "$p" ]; then ls -la "$p" 2>/dev/null | head -15; fi
done
find /etc /opt "$HOME" -maxdepth 4 \( -name "*calibration*.toml" -o -name "robotd*.toml" \) 2>/dev/null | head -10
for f in $(find /etc /opt "$HOME" -maxdepth 4 -name "*calibration*.toml" 2>/dev/null | head -3); do
  printf -- "--- %s (只读 grep 安全相关字段) ---\n" "$f"
  grep -nE "motion_enabled|imu_mount|version|serial" "$f" 2>/dev/null | head -10
done
command -v robotctl >/dev/null 2>&1 && run robotctl --help | head -15 || true

section "6 策略/模型目录（体积清单）"
for d in /opt/microduck/policies "$HOME/policies" "$HOME/.config/microduck/policies"; do
  [ -d "$d" ] && { du -sh "$d" 2>/dev/null; ls -la "$d" 2>/dev/null | head -12; }
done

section "7 硬件设备节点（只列出，不打开）"
run lsusb
ls -la /dev/ttyS* /dev/ttyUSB* /dev/ttyACM* /dev/video* /dev/i2c-* 2>/dev/null || true

section "8 日志尾部（只读）"
if systemctl cat robotd.service >/dev/null 2>&1; then
  journalctl -u robotd -n 20 --no-pager -q 2>/dev/null || true
fi
journalctl -p warning -n 10 --no-pager -q 2>/dev/null || true

section "9 电源（若 HAT/系统暴露 sysfs）"
for f in /sys/class/power_supply/*; do
  [ -d "$f" ] || continue
  printf "%s: " "$f"
  for k in type capacity voltage_now status; do
    [ -r "$f/$k" ] && printf "%s=%s " "$k" "$(cat "$f/$k")"
  done
  printf "\n"
done 2>/dev/null || true
printf "\n[巡检结束] 以上均为只读采集，未向舵机/IMU发送任何命令。\n"
'

do_save=0
[[ "${1:-}" == "--save" ]] && do_save=1

OUT="$(duck_run "$REMOTE_STATUS_SCRIPT")" || { echo "连接鸭子失败（检查 DUCK_HOST / 跳板 / 密钥）" >&2; exit 3; }
echo "$OUT"

if [[ $do_save -eq 1 ]]; then
  TS="$(date -u +%Y%m%dT%H%M%SZ)"
  DIR="$REPO_ROOT/.evidence/duck-status-$TS"
  mkdir -p "$DIR"
  printf '%s\n' "$OUT" > "$DIR/status.txt"
  {
    echo "collected_utc: $TS"
    echo "target: ${DUCK_USER}@${DUCK_HOST}:${DUCK_PORT}"
    echo "jump: ${DUCK_JUMP:-none}"
    echo "mode: read-only allowlist (scripts/duck/status-duck.sh)"
  } > "$DIR/meta.txt"
  echo ">>> 已留档: $DIR（.evidence/ 不入库，脱敏摘要才提交 records/field/）"
fi
