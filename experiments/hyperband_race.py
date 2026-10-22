# -*- coding: utf-8 -*-
"""Hyperband 变精度赛马：多精度 SuccessiveHalving 早停（第三梯队）。

用户纪律（2026-10-20 延续）：
  * 加算法 = 在冠军参数上叠加，不许独狼跑
  * 纯 CPU；没有提高 → 换下一个

为什么 Hyperband 要专门 runner（不塞进 warmstart_race）：
  warmstart_race/compare 都是「固定精度」评估（smoke=3build×100局 /
  full=7build×100局）。Hyperband 的价值 100% 在「多精度早停」——用少局数粗筛
  大把候选、只对幸存者加局数精评。固定精度下它会退化成重复评估的锦标赛，
  浪费预算。故这里按 requested_resource 用变 runs 评估。

协议（CRN 配对，与 warmstart_race 对齐 + 变精度）：
  1. 读冠军种子 TOML → 暖启向量 w；重放定标 B = evaluate(w, smoke)
     （smoke = 3 build × 100 局 × seed42）
  2. 每 seed：HyperbandOptimizer 变精度搜索（资源 runs 从 min→max，
     builds 固定 SCREEN_BUILDS=3 build；满资源 runs=max_resource=100 局
     恰好等于 smoke 档精度，故满资源分数与 B 同口径可比）
  3. 每 seed 的「满资源评估过的冠军」score 与 B 配对，单样本 t 检验
  4. 判读：p<0.05 且 meanΔ>+150 → promote 候补；否则换下一个

输出：results/hyperband_<stamp>/result.json + report.md + txt 日志 + CHAMPION.toml
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lab.genome import decode, toml_to_vector, genome_to_toml  # noqa: E402
from lab.space import free_dim  # noqa: E402
from lab.evaluator import (Evaluator, FAIL_PENALTY, SCREEN_BUILDS,  # noqa: E402
                           SMOKE_SEEDS)
from optimizers.hyperband_opt import HyperbandOptimizer  # noqa: E402

SIG_THRESHOLD = 150.0


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


DIM = free_dim()


class _MockEvaluator:
    """mock：合成分数（候选熵噪声），只验接线/调度不验成绩（不跑 bench_base）。"""

    def __init__(self):
        self.n = 0

    def evaluate(self, genome, level="smoke"):
        return {"score": 63323.0, "hash": "mock"}

    def _run_bench(self, toml_text, seed, runs, builds=None):
        import hashlib
        self.n += 1
        h = int(hashlib.md5(toml_text.encode("utf-8")).hexdigest()[:8], 16)
        mean = 63000.0 + (h % 3000) + runs * 0.5   # 不同候选不同分（可验证淘汰方向）
        return mean, 0.0


def run_hyperband(ev, seed, warm, eta, min_resource, max_resource, sigma0):
    """单个 seed 的变精度 Hyperband 搜索 → 满资源冠军。

    返回 dict：best（满资源冠军分，与 sm=oke 基线同精度）、best_genome、curve、n_evals。
    """
    t0 = time.time()
    opt = HyperbandOptimizer(DIM, seed=seed, center=warm, eta=eta,
                             min_resource=min_resource,
                             max_resource=max_resource, sigma0=sigma0)
    full_pool = []   # (x, score)：满资源（runs=max_resource）评估过的候选
    curve = []
    n = 0
    while True:
        try:
            x = opt.ask()
        except RuntimeError:
            break
        resource = opt.requested_resource
        runs = max(1, int(round(resource)))
        genome = decode(x)
        toml_text = genome_to_toml(genome)
        m, fr = ev._run_bench(toml_text, SMOKE_SEEDS[0], runs, builds=SCREEN_BUILDS)
        score = m - FAIL_PENALTY * fr
        opt.tell(x, score)
        n += 1
        if runs >= int(round(max_resource)):
            full_pool.append((x, score))
        curve.append({"i": n, "runs": runs, "score": round(score, 1)})

    best_x, best_score = None, -float("inf")
    for x, s in full_pool:
        if s > best_score:
            best_x, best_score = x, s
    if best_x is None:
        best_x, best_score = None, opt.best  # 兜底（不应发生）
    return {
        "best": round(best_score, 1) if best_score is not None else None,
        "best_x": best_x,
        "best_genome": decode(best_x) if best_x is not None else None,
        "curve": curve, "n_evals": n, "full_pool_size": len(full_pool),
        "elapsed_sec": round(time.time() - t0, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="7,13,23,31,47")
    ap.add_argument("--eta", type=int, default=3)
    ap.add_argument("--min-resource", type=float, default=10.0,
                    help="最低评估局数（粗筛）")
    ap.add_argument("--max-resource", type=float, default=100.0,
                    help="满精度局数（= smoke 档，与基线同口径）")
    ap.add_argument("--sigma0", type=float, default=0.15)
    ap.add_argument("--seed-file", default=str(ROOT / "data/seeds/seed_xnes_best.toml"))
    ap.add_argument("--uma", type=int, default=111501)
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()

    seed_list = [int(s) for s in args.seeds.split(",") if s.strip()]

    # 1) 冠军暖启向量（xNES 新锚）
    seed_text = Path(args.seed_file).read_text(encoding="utf-8")
    warm = toml_to_vector(seed_text)
    print(f"[hb] 暖启种子: {Path(args.seed_file).name}  dim={len(warm)}  "
          f"非默认位={sum(1 for v in warm if abs(v - 0.5) > 1e-9)}/{len(warm)}")

    # 2) 基线定标（smoke 档，= Hyperband 满资源同精度）
    if args.mock:
        ev = _MockEvaluator()
        baseline = 63323.0
        print(f"[hb] MOCK 模式：假评估器，基线取常数 {baseline}")
    else:
        ev = Evaluator(uma=args.uma)
        out = ev.evaluate(decode(warm), level="smoke")
        baseline = out["score"]
        print(f"[hb] 冠军重放定标 B = {baseline}（smoke，口径漂移以本数为准）")

    # 3) 多 seed 变精度赛马
    results = {
        "seeds": seed_list, "eta": args.eta, "min_resource": args.min_resource,
        "max_resource": args.max_resource, "sigma0": args.sigma0,
        "baseline": baseline, "runs": [],
    }
    for seed in seed_list:
        r = run_hyperband(ev, seed, warm, args.eta, args.min_resource,
                          args.max_resource, args.sigma0)
        r["seed"] = seed
        results["runs"].append(r)
        print(f"[hb] seed={seed}: best={r['best']} "
              f"(满资源池 {r['full_pool_size']} 个, {r['n_evals']} evals, "
              f"{r['elapsed_sec']}s)")

    # 4) 统计（满资源冠军 vs 基线，配对）
    bests = [r["best"] for r in results["runs"] if r["best"] is not None]
    deltas = [b - baseline for b in bests]
    mean_d, std_d, t_d, p_d = paired_t_vs_const(deltas)
    sig = (p_d is not None and p_d < 0.05 and mean_d > 0)
    verdict = ("promote 候补" if sig and mean_d > SIG_THRESHOLD
               else "mild 观察" if sig else "n.s.（换下一个）")
    stats = {
        "bests": [round(b, 1) for b in bests],
        "mean_best": round(float(np.mean(bests)), 1),
        "std_best": round(float(np.std(bests, ddof=1)), 1) if len(bests) > 1 else 0.0,
        "delta_vs_baseline": [round(d, 1) for d in deltas],
        "mean_delta": round(mean_d, 1), "std_delta": round(std_d, 1),
        "t": round(t_d, 3) if (t_d is not None and t_d == t_d) else None,
        "p": round(p_d, 4) if (p_d is not None and p_d == p_d) else None,
        "sig_positive": sig, "verdict": verdict,
    }
    t_str = f"{t_d:.2f}" if t_d is not None else "n/a"
    p_str = f"{p_d}" if p_d is not None else "n/a"
    print(f"[hb] hyperband: mean Δ={mean_d:+.1f} ± {std_d:.1f} "
          f"(t={t_str}, p={p_str}) → {verdict}")
    results["stats"] = stats

    # 5) 落盘
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "results" / f"hyperband_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "result.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    champ = max((r for r in results["runs"] if r.get("best_genome")),
                key=lambda r: r["best"], default=None)
    for r in results["runs"]:
        if r.get("best_genome"):
            gpath = out_dir / f"best_seed{r['seed']}.toml"
            gpath.write_text(genome_to_toml(r["best_genome"]), encoding="utf-8")
    if champ:
        (out_dir / "CHAMPION.toml").write_text(
            f"# 全场最强：hyperband seed={champ['seed']} best={champ['best']}\n"
            + genome_to_toml(champ["best_genome"]), encoding="utf-8")
        print(f"[hb] 冠军导出 {out_dir / 'CHAMPION.toml'}"
              f"（seed={champ['seed']} best={champ['best']}）")

    report = [
        f"# Hyperband 变精度赛马",
        "",
        f"- 暖启种子: `{Path(args.seed_file).name}`（重放定标 B={baseline}，smoke 档）",
        f"- 协议: {len(seed_list)} seed × 变精度 SH（eta={args.eta}, "
        f"runs {args.min_resource}→{args.max_resource}，builds={SCREEN_BUILDS}）",
        f"- 满资源 runs={args.max_resource} 局 = smoke 档精度，与 B 同口径",
        "",
        "| 指标 | 值 |",
        "| --- | --- |",
        f"| mean best | {stats['mean_best']} |",
        f"| mean Δ vs B | {stats['mean_delta']:+} |",
        f"| std Δ | {stats['std_delta']} |",
        f"| t | {stats['t']} |",
        f"| p | {stats['p']} |",
        f"| 判定 | {stats['verdict']} |",
    ]
    (out_dir / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    txt = [
        "=" * 62,
        f"Hyperband 变精度赛马运行日志   {time.strftime('%Y%m%d_%H%M%S %Z')}",
        f"暖启种子: {Path(args.seed_file).name}（叠加链 GA→TPE→xNES→hyperband）",
        "=" * 62,
        "",
        "【协议】",
        f"  多精度 SH: eta={args.eta}, runs={args.min_resource}→{args.max_resource}, "
        f"builds={SCREEN_BUILDS}",
        f"  种子: {seed_list}（CRN: bench seed=42 配对）",
        f"  基线: 冠军重放定标 B={baseline}（smoke 档）",
        "",
        "【成绩】",
        f"  mean best={stats['mean_best']}  mean Δ={stats['mean_delta']:+} "
        f"(t={t_str}, p={p_str}) → {verdict}",
        f"  各 seed best: {stats['bests']}",
        "",
        "【结论】",
        f"  {verdict}（阈值 +{SIG_THRESHOLD:.0f}，p<0.05）",
        "  判读口径: BASELINE.md 分层协议——smoke 出头才够格挑战绝对锚",
        "=" * 62,
    ]
    logs_dir = ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)
    txt_path = logs_dir / f"hyperband_{stamp}.txt"
    txt_path.write_text("\n".join(txt) + "\n", encoding="utf-8")
    print(f"[hb] txt 日志写入 {txt_path}")


if __name__ == "__main__":
    main()