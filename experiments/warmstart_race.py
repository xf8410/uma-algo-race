# -*- coding: utf-8 -*-
"""第二梯队暖启赛马：新算法在「已加起来的最高分」上叠加（非独狼跑）。

用户纪律（2026-10-20）：
  * 加算法 = 在已经有的、已经提升过的冠军参数之上叠加，不许从零独狼跑
  * 纯 CPU，不碰 GPU；没有提高 → 立马换下一个算法
  * 基线用当前冠军重放定标（口径警示纪律：跨 commit 先重放，不拿旧数比）

协议（CRN 配对）：
  1. 读冠军种子 TOML（默认 data/seeds/seed_tpe_best.toml，71692 同口径冠军）
     → 暖启向量 w；重放定标 B = evaluate(w)（smoke，seed42 CRN）
  2. 每算法 × 每 seed：Optimizer(dim, seed, center=w, sigma0) 暖启跑 n_iter
  3. 配对 Δ_s = best_s − B（同场同码），单样本 t 检验
  4. 判读：p<0.05 且 meanΔ>+150 → promote 候补；n.s. → 档案结论换下一个

输出：results/warmstart_<stamp>/result.json + report.md
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lab.genome import decode, toml_to_vector, apply_fixed  # noqa: E402
from lab.space import free_dim  # noqa: E402
from lab.evaluator import Evaluator  # noqa: E402
from optimizers import REGISTRY  # noqa: E402

SIG_THRESHOLD = 150.0   # promote_mild 量级线（playbook 20261014 先例：<150 只 mild）


def paired_t_vs_const(deltas):
    """best_s − B 的单样本 t 检验（B 为确定值）；n<2 不给 t/p。"""
    arr = np.array(deltas, dtype=float)
    n = len(arr)
    mean = float(np.mean(arr))
    if n < 2:
        return mean, 0.0, None, None
    std = float(np.std(arr, ddof=1))
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


def run_one(name, cls, ev, seed, n_iter, warm, sigma0):
    t0 = time.time()
    opt = cls(dim=DIM, seed=seed, center=warm, sigma0=sigma0)
    curve = []
    for i in range(n_iter):
        x = opt.ask()
        genome = decode(x)
        out = ev.evaluate(genome, level="smoke")
        opt.tell(x, out["score"])
        curve.append({"i": i, "score": out["score"], "best": opt.best})
    return {
        "name": name, "seed": seed, "best": opt.best, "curve": curve,
        "elapsed_sec": round(time.time() - t0, 1),
    }


DIM = free_dim()


class _MockEv:
    """mock：合成景观（center 二次峰 + 噪声），只验行为不验成绩。"""

    def __init__(self, warm):
        self.warm = np.asarray(warm)
        self.n = 0

    def evaluate(self, genome, level="smoke"):
        self.n += 1
        # 需要向量而非 genome——mock 只在 wiring 测试里用 genome 长度判合法性
        return {"score": 63000.0 + 500.0 * self.n / max(1, self.n), "hash": f"mock{self.n}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--algos", default="xnes,bore")
    ap.add_argument("--n-iter", type=int, default=30)
    ap.add_argument("--seeds", default="7,13,23,31,47")
    ap.add_argument("--sigma0", type=float, default=0.15,
                    help="暖启探索步长（playbook v3 先例 sigma0=0.15）")
    ap.add_argument("--seed-file", default=str(ROOT / "data/seeds/seed_tpe_best.toml"))
    ap.add_argument("--uma", type=int, default=111501)
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()

    algos = [a.strip() for a in args.algos.split(",") if a.strip()]
    seed_list = [int(s) for s in args.seeds.split(",") if s.strip()]
    for a in algos:
        if a not in REGISTRY:
            print(f"[warm] 错误：{a} 不在 REGISTRY ({list(REGISTRY.keys())})")
            sys.exit(1)

    # 1) 冠军暖启向量（toml_to_vector 内部自带 toml_to_value + apply_fixed）
    seed_text = Path(args.seed_file).read_text(encoding="utf-8")
    warm = toml_to_vector(seed_text)
    print(f"[warm] 暖启种子: {Path(args.seed_file).name}  dim={len(warm)}  "
          f"非默认位={sum(1 for v in warm if abs(v - 0.5) > 1e-9)}/{len(warm)}")

    # 2) 基线定标（冠军重放）
    if args.mock:
        ev = _MockEv(warm)
        baseline = 63323.0
        print(f"[warm] MOCK 模式：基线取常数 {baseline}")
    else:
        ev = Evaluator(uma=args.uma)
        out = ev.evaluate(decode(warm), level="smoke")
        baseline = out["score"]
        print(f"[warm] 冠军重放定标 B = {baseline}（历史 tpe 63499.0，口径漂移以本数为准）")

    # 3) 赛马
    results = {"algos": algos, "seeds": seed_list, "n_iter": args.n_iter,
               "sigma0": args.sigma0, "baseline": baseline, "runs": []}
    for name in algos:
        cls = REGISTRY[name]
        for seed in seed_list:
            r = run_one(name, cls, ev, seed, args.n_iter, warm, args.sigma0)
            results["runs"].append(r)
            print(f"[warm] {name} seed={seed}: best={r['best']} "
                  f"({r['elapsed_sec']}s)")

    # 4) 统计
    stats = {}
    for name in algos:
        bests = [r["best"] for r in results["runs"] if r["name"] == name]
        deltas = [b - baseline for b in bests]
        mean_d, std_d, t_d, p_d = paired_t_vs_const(deltas)
        sig = (p_d is not None and p_d < 0.05 and mean_d > 0)
        stats[name] = {
            "bests": [round(b, 1) for b in bests],
            "mean_best": round(float(np.mean(bests)), 1),
            "std_best": round(float(np.std(bests, ddof=1)), 1),
            "delta_vs_baseline": [round(d, 1) for d in deltas],
            "mean_delta": round(mean_d, 1), "std_delta": round(std_d, 1),
            "t": round(t_d, 3) if t_d == t_d else None,
            "p": round(p_d, 4) if p_d is not None else None,
            "sig_positive": sig,
        }
        verdict = ("promote 候补" if sig and mean_d > SIG_THRESHOLD
                   else "mild 观察" if sig else "n.s.（换下一个）")
        stats[name]["verdict"] = verdict
        print(f"[warm] {name}: mean Δ={mean_d:+.1f} ± {std_d:.1f} "
              f"(t={t_d:.2f}, p={p_d}) → {verdict}")

    results["stats"] = stats
    results["total_elapsed_sec"] = round(
        sum(r["elapsed_sec"] for r in results["runs"]), 1)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "results" / f"warmstart_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "result.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# 暖启赛马（{', '.join(algos)}）——在冠军参数上叠加",
        "",
        f"- 暖启种子: `{Path(args.seed_file).name}`（重放定标 B={baseline}）",
        f"- 协议: {len(seed_list)} seed × {args.n_iter} iter，sigma0={args.sigma0}",
        f"- 总用时: {results['total_elapsed_sec']}s",
        "",
        "| 算法 | mean best | std | mean Δ vs B | std Δ | t | p | 判定 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name in algos:
        s = stats[name]
        lines.append(f"| {name} | {s['mean_best']} | {s['std_best']} | "
                     f"{s['mean_delta']:+} | {s['std_delta']} | {s['t']} | "
                     f"{s['p']} | {s['verdict']} |")
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n[warm] 报告写入 {out_dir}/report.md")


def _parse(toml_text):
    from lab.genome import toml_to_value
    return toml_to_value(toml_text)


if __name__ == "__main__":
    main()
