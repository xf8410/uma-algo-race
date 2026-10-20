# -*- coding: utf-8 -*-
"""xNES：指数自然进化策略（CMA-ES 的信息几何表亲）。

入选理由（docs/blackbox-selection.md #3，2026-10-18 tier1 收账后排位补位）：
直接在分布参数 (μ, Σ=σ²·exp(2B)) 上做自然梯度上升，与 CMA-ES 形成
"同族轻量对照"——若 xNES 显著弱于 CMA-ES，说明协方差自适应是关键，
这本身就是结论。

实现：Wierstra et al. 2014《Natural Evolution Strategies》。
- λ 后代，utility 按 log 排序权重（best 前置，归一化和=1）
- z 空间自然梯度：
    g_μ = Σ uᵢzᵢ
    G_B = ½ Σ uᵢ(zᵢzᵢᵀ − I)，tr = tr(G_B)
- 更新（A = σ·expm(B)）：
    μ ← μ + η_μ · A·g_μ
    σ ← σ · exp(η_B · tr)          （迹部分归 σ）
    B ← B + η_B · (G_B − tr/d·I)   （去迹部分归 B，保对称）
- 学习率取 PyBrain 参考实现：η_μ=1，η_σ=η_B=(3/5)(3+ln d)/(d√d)
- 首发固定评估 center（warm-start 锚点，与 cmaes_opt 同款）
- ask/tell 攒代模式（pool 弹候选 + 平行 z 队列，攒满 λ 条更新一代）
- 候选夹回 [0,1]^d 后仍用原 z 更新（箱约束标准处理）
"""
import numpy as np
from scipy.linalg import expm
from typing import List, Optional

from .base import Optimizer


def _utility_weights(lam: int) -> np.ndarray:
    """log 排序效用：u_k ∝ max(0, ln(λ/2+1) − ln k)，归一化。"""
    k = np.arange(1, lam + 1)
    u = np.maximum(0.0, np.log(lam / 2.0 + 1.0) - np.log(k))
    s = u.sum()
    return u / s if s > 0 else np.full(lam, 1.0 / lam)


class XnesOptimizer(Optimizer):
    name = "xnes"

    def __init__(self, dim: int, seed: int = 7, sigma0: float = 0.06, center=None):
        super().__init__(dim, seed, center)
        self.sigma = float(sigma0)
        self.mu = np.asarray(self.center, dtype=float).copy()
        self.B = np.zeros((dim, dim))            # 对称，初始 0 → Σ = σ²I
        self.lam = max(8, 4 + int(3 * np.log(dim)))
        self.eta_mu = 1.0
        self.eta_B = (3.0 / 5.0) * (3.0 + np.log(dim)) / (dim * np.sqrt(dim))
        self.u_w = _utility_weights(self.lam)
        self.rng = np.random.default_rng(seed)
        self._pool: List[np.ndarray] = []        # 当前代未派发候选
        self._pending_z: List[np.ndarray] = []   # 与 pool 平行的 z
        self._current_z: Optional[np.ndarray] = None
        self._solutions: List[tuple] = []        # 当前代 (z, score)
        self._first = True                       # 首发锚点 = center

    # -- 分布工具 ---------------------------------------------------------
    def _A(self) -> np.ndarray:
        """A = σ·expm(B)（对称矩阵指数，d=45 每代一次可承受）"""
        return self.sigma * expm(self.B)

    def _sample_gen(self) -> None:
        A = self._A()
        zs = [self.rng.standard_normal(self.dim) for _ in range(self.lam)]
        self._pending_z = zs
        self._pool = [self.mu + A @ z for z in zs]

    # -- Optimizer 接口 ---------------------------------------------------
    def ask(self) -> List[float]:
        if self._first:
            self._first = False
            return list(self.mu)
        if not self._pool:
            self._sample_gen()
        self._current_z = self._pending_z.pop(0)
        x = self._pool.pop(0)
        return [min(1.0, max(0.0, float(v))) for v in x]

    def tell(self, x: List[float], score: float) -> None:
        self.log(x, score)
        if self._current_z is None:
            return  # 锚点：只记 best，不进整代更新（与 cmaes_opt 同款）
        self._solutions.append((self._current_z, score))
        self._current_z = None
        if len(self._solutions) >= self.lam:
            self._update()

    def _update(self) -> None:
        sol = sorted(self._solutions, key=lambda t: -t[1])   # score 降序=最大化
        us = self.u_w
        zs = [np.asarray(z) for z, _ in sol]
        g_mu = sum(u * z for u, z in zip(us, zs))
        G_B = 0.5 * sum(u * (np.outer(z, z) - np.eye(self.dim))
                        for u, z in zip(us, zs))
        tr = float(np.trace(G_B))
        A = self._A()
        self.mu = np.clip(self.mu + self.eta_mu * (A @ g_mu), 0.0, 1.0)
        self.sigma = float(np.clip(self.sigma * np.exp(self.eta_B * tr), 1e-4, 0.5))
        self.B = self.B + self.eta_B * (G_B - (tr / self.dim) * np.eye(self.dim))
        self._solutions = []
        self._pool = []
        self._pending_z = []
