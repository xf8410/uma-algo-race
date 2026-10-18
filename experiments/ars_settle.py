# -*- coding: utf-8 -*-
"""ARS 晋级裁决：10 seed × 60 iter vs cmaes 同场 CRN 配对。

run4 结论（tier1_settle）：ars mean 63438.3±44.1 全场最稳，range 下界
63388 最高——但 5 seed × 30 iter 的 Δ+42.2 不显著。本实验加预算裁决：
双倍 seed 双倍 iter，若配对 Δ 显著为正（p<0.05）→ promote 进
BASELINE 主战表；仍 n.s. → ars 定格 promote_mild 观察位。
"""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lab.evaluator import Evaluator  # noqa: E402
from optimizers import REGISTRY  # noqa: E402
from experiments.sa_compare import run_one, paired_t  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", default="7,13,23,31,47,101,103,107,109,113")
    p.add_argument("--n-iter", type=int, default=60)
    p.add_argument("--uma", type=int, default=111501)
    p.add_argument("--out", default="results/ars_settle.json")
    args = p.parse_args()

    seeds = [int(s) for s in args.seeds.split(",")]
    ev = Evaluator(uma=args.uma, cache_path="data/eval_cache_ars_settle.json")
    per = {}
    for name in ["ars", "cmaes"]:
        runs = []
        for seed in seeds:
            r = run_one(name, REGISTRY[name], ev, args, seed)
            print(f"[ars-settle] {name} seed={seed} best={r['best']:.1f} ({r['elapsed_sec']}s)", flush=True)
            runs.append(r)
        per[name] = runs
    deltas = [a["best"] - c["best"] for a, c in zip(per["ars"], per["cmaes"])]
    mean, std, t, pv = paired_t(deltas)
    print(f"配对 Δ(ars-cmaes): mean={mean:+.1f} std={std:.1f} t={t:.3f} p={pv:.4f}")
    verdict = "promote" if (pv < 0.05 and mean > 0) else "promote_mild_hold"
    print(f"裁决: {verdict}")
    import json
    Path(args.out).parent.mkdir(exist_ok=True)
    Path(args.out).write_text(json.dumps({"per": per, "deltas": deltas, "mean": mean,
                                          "std": std, "t": t, "p": pv, "verdict": verdict},
                                         ensure_ascii=False, indent=1))
    print(f"已写 {args.out}")


if __name__ == "__main__":
    main()
