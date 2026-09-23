#!/usr/bin/env bash
# 便捷启动器：在 CPU MuJoCo 里 play 官方 policy
# 所有官方 policy 均为 61 维观测版, 必须带 --new-cmd-obs
# 用法:
#   ./play.sh walk          # 最简单:走路 policy(推荐第一次用这个)
#   ./play.sh velstand      # 走路+站立+摔倒爬起(官方默认步态)
#   ./play.sh full          # 全家桶:走路+起坐+捡东西+踢球+翻滚
#   ./play.sh sitstand      # 走路+起坐(Y 键切换)
#   ./play.sh kick          # 走路+踢球(场景里有一个球, K/L 触发)
#   ./play.sh roulade       # 走路+前滚翻(R 触发)
#   ./play.sh roller        # 轮滑模式(脚底带轮子)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RL="$ROOT/microduck_rl"
P="$ROOT/policies/official"

case "${1:-velstand}" in
  walk)
    exec_cmd=(--new-cmd-obs --walking "$P/alpha_walking.onnx" --standing "$P/alpha_stand.onnx") ;;
  velstand)
    exec_cmd=(--new-cmd-obs --walking "$P/velstand.onnx") ;;
  sitstand)
    exec_cmd=(--new-cmd-obs --walking "$P/velstand.onnx" --sitstand "$P/alpha_sitstand.onnx") ;;
  kick)
    exec_cmd=(--new-cmd-obs --walking "$P/velstand.onnx" --kick-left "$P/ball_kick_left.onnx" --kick-right "$P/ball_kick_right.onnx") ;;
  roulade)
    exec_cmd=(--new-cmd-obs --walking "$P/velstand.onnx" --roulade "$P/roulade.onnx") ;;
  full)
    exec_cmd=(--new-cmd-obs --walking "$P/velstand.onnx" --sitstand "$P/alpha_sitstand.onnx" \
              --ground-pick "$P/alpha_ground_pick.onnx" \
              --kick-left "$P/ball_kick_left.onnx" --kick-right "$P/ball_kick_right.onnx" \
              --roulade "$P/roulade.onnx") ;;
  roller)
    exec_cmd=(--new-cmd-obs --roller --walking "$P/roller.onnx" --action-scale 0.8) ;;
  *)
    echo "未知模式: $1"; echo "可用: walk | velstand | sitstand | kick | roulade | full | roller"; exit 1 ;;
esac

cd "$RL"
echo ">>> cd $RL && uv run scripts/infer_policy.py ${exec_cmd[*]}"
exec ~/.local/bin/uv run scripts/infer_policy.py "${exec_cmd[@]}"
