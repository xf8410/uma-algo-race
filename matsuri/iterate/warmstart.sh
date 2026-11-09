#!/usr/bin/env bash
# 骏大祭暖启搜索启动脚本（真实命令，无占位）。
#
# 前提：在【上游剧本仓根目录】执行，且已编译 cardtest：
#   cargo build --release -p matsuri-tools --bin cardtest
# 配套引擎仓 umaai-next 需为与本剧本 commit 配对的版本（Rust 1.99.0）。
# 本命名空间里的 tools/ga_trainer.py 是上游脚本原样副本，其相对路径
# 假设 data/matsuri_config.toml、decks/、target/release/ 都在仓根。
#
# 用法:  bash warmstart.sh <genome.toml> [decks.csv] [minutes]
# 例:    bash warmstart.sh ../champion/genome_g0269_default.toml decks/speed_build.csv 100
set -euo pipefail

GENOME="${1:-../champion/genome_g0269_default.toml}"
DECKS="${2:-decks/speed_build.csv}"
MINUTES="${3:-100}"
TAG="$(basename "${GENOME%.toml}")"
OUT="logs/ga/matsuri-warm-${TAG}"

# 种子偏移每轮换新，绝不复用（CRN 纪律）
SEED_OFFSET="${SEED_OFFSET:-20000000}"

if [ ! -f "$GENOME" ]; then
  echo "找不到 genome: $GENOME" >&2; exit 2
fi
if [ ! -x target/release/cardtest ]; then
  echo "缺少 target/release/cardtest；先执行：" >&2
  echo "  cargo build --release -p matsuri-tools --bin cardtest" >&2
  exit 2
fi

echo "起点 genome : $GENOME"
echo "卡组夹具   : $DECKS"
echo "输出目录   : $OUT"
echo "种子偏移   : $SEED_OFFSET"
echo "限时(分钟) : $MINUTES"

python3 tools/ga_trainer.py search \
  --out "$OUT" \
  --start "$GENOME" \
  --decks "$DECKS" \
  --profile default \
  --seed-offset "$SEED_OFFSET" \
  --lam 48 --sigma 0.05 \
  --max-minutes "$MINUTES" --threads 8

echo "搜索完成。下一步验收（门禁见 ITERATE.md §二）："
echo "  python3 tools/ga_trainer.py confirm --out $OUT --start $GENOME --games 2500"
echo "  python3 tools/search_check.py"
echo "  python3 iterate/gate.py --candidate <分> --current 87557.1 --start 83793.9 --se <SE> --n <对数> --shadow-delta <Δ> --friend-full <率> --current-friend-full <率> --start-friend-full <率> --search-t <t>"
