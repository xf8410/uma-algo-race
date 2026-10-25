# -*- coding: utf-8 -*-
"""从汇总 JSON 里挑全场最强 shard，导出其 CHAMPION.toml 为新暖启锚。

用法：
  python tools/pick_champion.py results/ga_full_248_10seed.json \
      --out data/seeds/seed_ga_best.toml
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("summary")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    runs = data.get("runs") or []
    if not runs:
        raise SystemExit("汇总里没有 runs")
    best = max(runs, key=lambda r: r["best"])
    src = Path(best["dir"]) / "CHAMPION.toml"
    if not src.exists():
        raise SystemExit(f"找不到 {src}")
    text = src.read_text(encoding="utf-8").lstrip()
    # 去掉旧头两行注释，换成新锚说明
    lines = [ln for ln in text.splitlines() if not ln.startswith("#")]
    header = (
        f"# GA 暖启新锚：{data['algo']} seed={best['seed']} "
        f"best={best['best']}（基线 {data['baseline']}，Δ{best['best']-data['baseline']:+.1f}）\n"
        f"# 来源：{args.summary}\n"
    )
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(header + "\n".join(lines).lstrip() + "\n", encoding="utf-8")
    print(f"champion seed={best['seed']} best={best['best']} -> {args.out}")


if __name__ == "__main__":
    main()
