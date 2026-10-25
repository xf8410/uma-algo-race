# -*- coding: utf-8 -*-
"""汇总分片跑批（每 shard 一个 seed）为单份 10-seed 报告。

用法：
  python tools/aggregate_warmstart.py results/warmstart_* --algo ga \
      --baseline 64673.5 --out results/ga_full_10seed.json

输出 JSON 含 per-seed bests、mean/std、配对 t/p、判定；同时打印 markdown 表。
"""
import argparse
import glob
import json
from pathlib import Path

import numpy as np


def paired_t_vs_const(deltas):
    arr = np.asarray(deltas, dtype=float)
    n = len(arr)
    mean = float(arr.mean())
    if n < 2:
        return mean, 0.0, None, None
    std = float(arr.std(ddof=1))
    if std > 0:
        t = mean / (std / np.sqrt(n))
        try:
            from scipy.stats import t as t_dist
            p = float(2 * (1 - t_dist.cdf(abs(t), df=n - 1)))
        except ImportError:
            p = None
    else:
        t = float("inf") if mean > 0 else 0.0
        p = 0.0 if mean != 0 else 1.0
    return mean, std, t, p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--algo", default="ga")
    ap.add_argument("--level", default=None, help="只收该档位（smoke/full）")
    ap.add_argument("--n-iter", type=int, default=None, help="只收该预算的跑批")
    ap.add_argument("--baseline", type=float, required=True)
    ap.add_argument("--threshold", type=float, default=150.0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    runs = []
    seen = set()
    for pattern in args.dirs:
        for d in sorted(glob.glob(pattern)):
            f = Path(d) / "result.json"
            if not f.exists():
                continue
            data = json.loads(f.read_text(encoding="utf-8"))
            if args.level and data.get("bench_level") != args.level:
                continue
            if args.n_iter is not None and data.get("n_iter") != args.n_iter:
                continue
            for r in data.get("runs", []):
                if r["name"] != args.algo or r["seed"] in seen:
                    continue
                seen.add(r["seed"])
                runs.append({"seed": r["seed"], "best": r["best"],
                             "best_x": r.get("best_x"),
                             "dir": str(d)})
    if not runs:
        raise SystemExit("没有找到任何 shard 结果")
    runs.sort(key=lambda r: r["seed"])
    bests = [r["best"] for r in runs]
    deltas = [b - args.baseline for b in bests]
    mean_d, std_d, t_d, p_d = paired_t_vs_const(deltas)
    sig = p_d is not None and p_d < 0.05 and mean_d > 0
    verdict = ("promote 候补" if sig and mean_d > args.threshold
               else "mild 观察" if sig else "n.s.")
    report = {
        "algo": args.algo, "baseline": args.baseline, "n": len(runs),
        "bests": [round(b, 1) for b in bests],
        "mean_best": round(float(np.mean(bests)), 1),
        "std_best": round(float(np.std(bests, ddof=1)), 1) if len(bests) > 1 else 0.0,
        "delta_vs_baseline": [round(x, 1) for x in deltas],
        "mean_delta": round(mean_d, 1), "std_delta": round(std_d, 1),
        "t": None if t_d is None else round(t_d, 3),
        "p": None if p_d is None else round(p_d, 6),
        "sig_positive": bool(sig), "verdict": verdict,
        "runs": runs,
    }
    print(f"| {args.algo} | {report['mean_best']} | {report['std_best']} | "
          f"{report['mean_delta']:+} | {report['std_delta']} | {report['t']} | "
          f"{report['p']} | {verdict} |")
    print("per-seed:", list(zip([r['seed'] for r in runs], report['bests'])))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("written", args.out)


if __name__ == "__main__":
    main()
