# -*- coding: utf-8 -*-
"""warmstart_race.run_one 的签名兼容测试。

历史 bug：runner 无脑传 sigma0，导致 tpe/cem/sa/spsa/ars/powell/map_elites
（签名里没有 sigma0）在暖启赛马里直接 TypeError，赛马实际只跑得动
cmaes/xnes/bore/ga 四个。这里锁死「按签名过滤」的行为。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from experiments.warmstart_race import run_one  # noqa: E402


class _NoSigma0:
    """模拟 TpeOptimizer：不吃 sigma0。"""

    def __init__(self, dim, seed=7, center=None):
        self.dim = dim
        self.center = list(center or [0.5] * dim)
        self.best = -float("inf")

    def ask(self):
        return list(self.center)

    def tell(self, x, score):
        self.best = max(self.best, score)


class _WithSigma0:
    def __init__(self, dim, seed=7, sigma0=0.06, center=None):
        self.dim = dim
        self.sigma0 = sigma0
        self.best = -float("inf")

    def ask(self):
        return [0.5] * self.dim

    def tell(self, x, score):
        self.best = max(self.best, score)


class _Eval:
    def evaluate(self, genome, level="smoke"):
        return {"score": 123.0}


class RunOneKwargsTest(unittest.TestCase):
    def test_optimizer_without_sigma0_is_supported(self):
        out = run_one("tpe", _NoSigma0, _Eval(), seed=7, n_iter=3,
                      warm=[0.5] * 45, sigma0=0.15)
        self.assertEqual(out["best"], 123.0)

    def test_sigma0_still_passed_when_supported(self):
        holder = {}

        class _Spy(_WithSigma0):
            def __init__(self, dim, seed=7, sigma0=0.06, center=None):
                super().__init__(dim=dim, seed=seed, sigma0=sigma0,
                                 center=center)
                holder["sigma0"] = self.sigma0

        run_one("xnes", _Spy, _Eval(), seed=7, n_iter=2,
                warm=[0.5] * 45, sigma0=0.15)
        self.assertEqual(holder["sigma0"], 0.15)

    def test_unknown_opt_kwargs_are_dropped(self):
        out = run_one("ga", _NoSigma0, _Eval(), seed=7, n_iter=2,
                      warm=[0.5] * 45, sigma0=0.15, opt_kwargs={"pop": 8})
        self.assertEqual(out["best"], 123.0)


if __name__ == "__main__":
    unittest.main()
