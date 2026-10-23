# -*- coding: utf-8 -*-
"""Thompson-UCB：局部高斯后验 + 随机乐观系数的 bandit 采集。

入选理由（2026-10-23 第三梯队，冲高分线）：
主人「贝叶斯 / RNG 信念推断 = 高价值」路线——把每轮采样当成对 45 维归一化
空间近邻后验的 bandit 选择。μ̂(x)、σ̂(x) 用 k 近邻历史点估计（朴素贝叶斯局部
模型，规避高维核带宽敏感），采集函数 = μ̂ + β·σ̂，β 每轮从 N(0,1) 抽一次
（随机乐观系数 = 把 Thompson 采样写成 UCB 形式，Rusmevichientong & Tsitsiklis
2010）。既保留 UCB「不确定性优先探索」，又带 Thompson 采样的随机性，避免
过早锁死局部峰。

- 冷启动（历史 < k+1）：center 锚点 + 围绕 center 的 σ0 探索
- 候选池：一半全域均匀 + 一半围绕历史最优 N(σ0)
- 近邻后验：候选 x 找历史 k 近邻，μ̂=邻域均值，σ̂=邻域标准差（有噪声底）
- 采集：α(x)=μ̂(x)+β·σ̂(x)，β~N(0,1)，取 argmax α
- 首发固定评估 center（warm-start 锚点，与 cmaes/xnes/bore 同款）
"""
import numpy as np
from typing import List

from .base import Optimizer


class ThompsonUcbOptimizer(Optimizer):
    name = "thompson_ucb"

    def __init__(self, dim: int, seed: int = 7, center=None,
                 sigma0: float = 0.15, n_cand: int = 256,
                 n_neighbors: int = 5, beta_scale: float = 1.0):
        super().__init__(dim, seed, center)
        self.sigma0 = float(sigma0)
        self.n_cand = int(n_cand)
        self.k = int(n_neighbors)
        self.beta_scale = float(beta_scale)
        self.rng = np.random.default_rng(seed)
        self.hist_x: List[np.ndarray] = []
        self.hist_y: List[float] = []
        self._first = True

    def _local_stats(self, x: np.ndarray, hist_X: np.ndarray,
                     hist_y: np.ndarray):
        """k 近邻局部后验：μ̂=邻域均值，σ̂=邻域标准差（ddof=0）。"""
        dist = np.linalg.norm(hist_X - x, axis=1)
        if len(dist) <= self.k:
            idx = np.arange(len(dist))
        else:
            idx = np.argpartition(dist, self.k - 1)[:self.k]
        ys = hist_y[idx]
        mu = float(np.mean(ys))
        sigma = float(np.std(ys))
        return mu, sigma

    def ask(self) -> List[float]:
        if self._first:
            self._first = False
            return list(self.center)

        hist_X = np.asarray(self.hist_x, dtype=float)
        hist_y = np.asarray(self.hist_y, dtype=float)

        # 冷启动：围绕 center 探索（与 bore/xnes 同款，warm 锚点暖场）
        if len(self.hist_x) < self.k + 1:
            x = np.asarray(self.center, dtype=float) + \
                self.rng.normal(0.0, self.sigma0, self.dim)
            return [min(1.0, max(0.0, float(v))) for v in x]

        # 候选池：一半全域均匀 + 一半围绕历史最优 N(σ0)
        n_uni = self.n_cand // 2
        n_loc = self.n_cand - n_uni
        cands = [self.rng.uniform(0.0, 1.0, self.dim) for _ in range(n_uni)]
        best_x = hist_X[int(np.argmax(hist_y))]
        cands += [best_x + self.rng.normal(0.0, self.sigma0, self.dim)
                  for _ in range(n_loc)]
        cands = [np.clip(c, 0.0, 1.0) for c in cands]

        # 噪声底：全局 y 波动的 5%（邻域全同分时保留微弱探索）
        y_scale = max(float(np.std(hist_y)), 1e-6)
        noise_floor = y_scale * 0.05

        # Thompson-UCB：随机乐观系数 β~N(0, beta_scale)，argmax(μ̂ + β·σ̂)
        beta = self.rng.normal(0.0, self.beta_scale)
        best_alpha = -float("inf")
        best_x = cands[0]
        for c in cands:
            mu, sigma = self._local_stats(c, hist_X, hist_y)
            sigma = max(sigma, noise_floor)
            alpha = mu + beta * sigma
            if alpha > best_alpha:
                best_alpha, best_x = alpha, c
        return [min(1.0, max(0.0, float(v))) for v in best_x]

    def tell(self, x: List[float], score: float) -> None:
        self.log(x, score)
        self.hist_x.append(np.asarray(x, dtype=float))
        self.hist_y.append(float(score))