#!/bin/sh
# pad-preflight.sh —— 手柄连接预检（设计为在鸭子板上运行；只读，绝不改动任何状态）
#
# 回答三个问题（对应 docs/manual/18-xbox-gamepad.md §3 的链路图）：
#   1. 内核有没有手柄相关驱动（xpad / hid-microsoft / hidp / joydev / uhid）？
#   2. 蓝牙适配器在不在、有没有已配对/已连接的手柄？
#   3. padd / gamesir-xboxd / btd 服务活着吗，robotctl 看到手柄了吗？
#
# 只读合同：不 systemctl start/stop/restart、不 robotctl 运动命令、不 bluetoothctl 扫描/配对、
#           不写任何文件。systemctl is-active / robotctl pad status 均为查询。
#
# 用法：ssh 上鸭子后  sh ~/microduck-tools/remote/pad-preflight.sh
# 依赖：coreutils + bluetoothctl + robotctl（板上都有）；任何一段缺工具只降级不失败。
set -u

hr() { printf '%s\n' "--------------------------------------------------------------"; }
have() { command -v "$1" >/dev/null 2>&1; }

echo "== pad-preflight @ $(hostname) $(date '+%F %T') · kernel $(uname -r) =="

echo; echo "[1] 内核手柄驱动（已加载 / 模块文件在板 / 内建）"
# modinfo 在板上非登录 shell 不在 PATH，兜底 /usr/sbin
MODINFO=$(command -v modinfo || echo /usr/sbin/modinfo)
for m in xpad hid-microsoft hidp joydev uhid; do
  if grep -q "^$m " /proc/modules 2>/dev/null; then
    printf '  %-14s 已加载\n' "$m"
  else
    ko=$([ -x "$MODINFO" ] && "$MODINFO" -n "$m" 2>/dev/null || true)
    if [ -n "$ko" ] && [ -f "$ko" ]; then
      printf '  %-14s 在板(未加载,设备出现时自动)  %s\n' "$m" "$ko"
    elif grep -q "/$m\.ko" "/lib/modules/$(uname -r)/modules.builtin" 2>/dev/null; then
      printf '  %-14s 内建(=y, 恒可用)\n' "$m"
    else
      printf '  %-14s ?? 无 .ko 也未加载(可能内建未列,连上设备即见分晓)\n' "$m"
    fi
  fi
done
echo "  说明: 真 Xbox 手柄蓝牙走 hid-microsoft(常见)或 hid-generic, USB 走 xpad;"
echo "        GameSir Nova 2 Lite 不吃内核驱动, 由 gamesir-xboxd 桥接(见[4])."

echo; echo "[2] 蓝牙适配器与配对状态"
if have bluetoothctl; then
  timeout 8 bluetoothctl show 2>/dev/null | grep -E "Controller|Powered" | sed 's/^/  /'
  echo "  已配对设备:"
  timeout 8 bluetoothctl devices 2>/dev/null | sed 's/^/    /' || echo "    (无)"
  echo "  已连接设备:"
  conn=$(timeout 8 bluetoothctl devices Connected 2>/dev/null || true)
  [ -n "$conn" ] && printf '%s\n' "$conn" | sed 's/^/    /' || echo "    (无)"
else
  echo "  !! bluetoothctl 不可用"
fi
echo "  aic-bluetooth 服务: $(systemctl is-active aic-bluetooth 2>/dev/null || echo unknown)（AIC8800 蓝牙晚挂载, 开机约 73s 后就绪属正常）"

echo; echo "[3] 输入节点（/proc/bus/input/devices 里的手柄类设备）"
nodes=$(grep -B1 -A4 -iE 'xbox|gamesir|dualsense|pro controller|gamepad' /proc/bus/input/devices 2>/dev/null \
        | grep -E '^(N:|P:|S:|H:)' || true)
if [ -n "$nodes" ]; then printf '%s\n' "$nodes" | sed 's/^/  /'
else echo "  (当前没有手柄类输入节点 —— 未连接手柄时正常)"; fi

echo; echo "[4] 运行时服务"
for s in robotd padd gamesir-xboxd btd bluetooth; do
  printf '  %-14s %s\n' "$s" "$(systemctl is-active $s 2>/dev/null || echo unknown)"
done

echo; echo "[5] robotctl 手柄视图"
if have robotctl; then
  echo "  -- pad status:"
  robotctl pad status 2>&1 | sed 's/^/     /'
  echo "  -- pad bindings（一键技能绑定）:"
  robotctl pad bindings 2>&1 | sed 's/^/     /'
else
  echo "  !! robotctl 不在 PATH"
fi

echo; echo "[6] padd 最近日志（robotctl logs, 免 sudo；开头一行 driving= 完整按键表）"
if have robotctl; then
  robotctl logs padd -n 12 2>&1 | sed 's/^/  /'
fi

hr
echo "结论看什么: [1]xpad/hid-microsoft 在板 + [2]适配器 Powered + [4]padd active + [5]'none paired'"
echo "           => 环境就绪, 到现场按手册 18 §4 配对即可; 异常项按手册 18 §7 排查。"
