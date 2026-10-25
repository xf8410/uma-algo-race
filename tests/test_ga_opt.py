# -*- coding: utf-8 -*-
"""GA 优化器行为测试（unittest：python -m unittest discover -s tests）。

不依赖真 bench：用可解析的二次景观验证
  1) 首发 = 暖启锚点（warm-start 纪律）
  2) ask/tell 代数推进、精英保留、候选始终在 [0,1]^d
  3) 同 seed 可复现
  4) n_iter 小于种群时不崩
"""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimizers.ga_opt import GaOptimizer  # noqa: E402


def _run(opt, scores, n_iter):
    best, best_x = -float("inf"), None
    for _ in range(n_iter):
        x = opt.ask()
        assert len(x) == opt.dim
        assert all(0.0 <= v <= 1.0 for v in x), "候选越界"
        s = scores(x)
        opt.tell(x, s)
        if s > best:
            best, best_x = s, x
    return best, best_x


class GaOptimizerTest(unittest.TestCase):
    def setUp(self):
        self.dim = 6
        self.center = [0.2, 0.4, 0.6, 0.8, 0.5, 0.3]
        self.target = np.array([0.7, 0.2, 0.9, 0.1, 0.8, 0.4])

    def _fitness(self, x):
        return -float(np.sum((np.asarray(x) - self.target) ** 2))

    def test_first_ask_is_warm_center(self):
        opt = GaOptimizer(self.dim, seed=7, center=self.center)
        x = opt.ask()
        self.assertEqual(x, self.center)

    def test_generation_progress_and_improvement(self):
        opt = GaOptimizer(self.dim, seed=7, center=self.center, pop=6)
        base = self._fitness(self.center)
        best, _ = _run(opt, self._fitness, 30)
        self.assertGreaterEqual(best, base)          # 精英主义不退化
        self.assertGreater(best, base)               # 二次景观应能变好
        self.assertGreater(opt._gen, 1)              # 至少繁殖过两代

    def test_deterministic_for_same_seed(self):
        a = GaOptimizer(self.dim, seed=13, center=self.center, pop=6)
        b = GaOptimizer(self.dim, seed=13, center=self.center, pop=6)
        xs_a, xs_b = [], []
        for _ in range(20):
            xa, xb = a.ask(), b.ask()
            xs_a.append(xa)
            xs_b.append(xb)
            sa, sb = self._fitness(xa), self._fitness(xb)
            a.tell(xa, sa)
            b.tell(xb, sb)
        self.assertEqual(xs_a, xs_b)

    def test_budget_smaller_than_population(self):
        opt = GaOptimizer(self.dim, seed=7, center=self.center, pop=12)
        best, _ = _run(opt, self._fitness, 5)
        self.assertGreaterEqual(best, self._fitness(self.center) - 1e-12)


if __name__ == "__main__":
    unittest.main()
