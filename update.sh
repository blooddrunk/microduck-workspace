#!/usr/bin/env bash
# 一键同步三个官方来源到最新：
#   1. microduck      (github.com/pollen-robotics/microduck, main, 浅克隆)
#   2. microduck_rl   (github.com/pollen-robotics/microduck_rl, develop)
#   3. 官方 policies  (huggingface.co/pollen-robotics/microduck-policies)
# 用法: ./update.sh
set -u
cd "$(dirname "$0")"

fail=0

echo "== 1/3 microduck (Rust 运行时, main) =="
git -C microduck pull --ff-only || fail=1

echo
echo "== 2/3 microduck_rl (RL 训练, develop) =="
git -C microduck_rl pull --ff-only || fail=1

echo
echo "== 3/3 HF 官方 policies =="
if [ -x microduck_rl/.venv/bin/hf ]; then
    microduck_rl/.venv/bin/hf download pollen-robotics/microduck-policies \
        --local-dir policies/official || fail=1
else
    echo "跳过：找不到 microduck_rl/.venv/bin/hf（先按 notes/00_快速上手.md 装好 uv 环境）"
    fail=1
fi

echo
if [ "$fail" -eq 0 ]; then
    echo "✅ 三个来源均已同步到最新："
    echo "   microduck     $(git -C microduck     log --oneline -1)"
    echo "   microduck_rl  $(git -C microduck_rl  log --oneline -1)"
else
    echo "❌ 有来源同步失败，见上方报错"
fi
exit "$fail"
