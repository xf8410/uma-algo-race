# -*- coding: utf-8 -*-
"""GA：遗传算法（老家 Rust `genetic_optimizer.rs` 的连续子集复刻）。

为什么补 GA（用户 2026-10-24 指令）：
  「继续用 ga 算法迭代手写逻辑」——GA 是手写策略历史最高分（r8 71415.6）
  的产地，但 uma-algo-race 的优化器名单里一直没有它。按暖启纪律把老家 GA
  的选择/交叉/变异算子原样搬进 [0,1]^d 连续空间，从当前冠军（xNES 64641.5，
  `data/seeds/seed_xnes_best.toml`）暖启，检验同一参数面上 GA 还能不能再挤出分。

与老家 Rust GA（crates/umasim/src/genetic_optimizer.rs）的逐项对照：
  - 精英保留      elitism = max(1, round(0.07·pop))（老家 4/60≈7%）
  - 锦标赛选择    tournament_k=3，无放回抽样、分高者胜、并列取下标小者
  - 均匀交叉      crossover_rate=0.9，逐基因 50/50 继承；不交叉则克隆父本 A
  - 高斯变异      每基因变异概率 1/N（老家 pm=1/GENE_COUNT），步长 σ×区间宽
  - σ 退火        σ0=0.15 → σ_min=0.03 线性衰减；连续 `stagnation_gens` 代
                  无提升 → 下一代 σ 回到 σ0（老家停滞回升）
  - 初始化        个体 0 = 暖启冠军向量（对应老家 --seed-genome 注入个体 0），
                  其余 = 冠军 + N(0, σ0)（暖启纪律：不独狼全域随机）

与老家的差异（空间不同，算子语义不变）：
  - 老家 77 基因含 None 态/布局/配卡；本实验室空间是 45 维连续自由字段，
    bool 与 preset 字段固定（space.py），因此 None 激活逻辑不适用
  - 预算由外层 warmstart_race 控制（n_iter 次评估），代数由 pop 大小隐式决定；
    n_iter 不整除时停在当代中途，best 仍为已评估最优
"""
import numpy as np
from typing import List, Optional

from .base import Optimizer


class GaOptimizer(Optimizer):
    name = "ga"

    def __init__(self, dim: int, seed: int = 7, sigma0: float = 0.15,
                 center=None, pop: int = 8, elitism: Optional[int] = None,
                 tournament_k: int = 3, crossover_rate: float = 0.9,
                 sigma_min: float = 0.03, stagnation_gens: int = 5,
                 gens_hint: int = 20):
        super().__init__(dim, seed, center)
        self.sigma0 = float(sigma0)
        self.sigma_min = float(sigma_min)
        self.pop_size = max(4, int(pop))
        if elitism is None:
            elitism = max(1, int(round(0.07 * self.pop_size)))
        self.elitism = max(1, min(int(elitism), self.pop_size - 1))
        self.tournament_k = max(1, min(int(tournament_k), self.pop_size))
        self.crossover_rate = float(crossover_rate)
        self.stagnation_gens = max(1, int(stagnation_gens))
        self.gens_hint = max(1, int(gens_hint))
        self.rng = np.random.default_rng(seed)

        # 当前代：_slots 为待评估候选（含暖启锚点），_scores 与已评估前缀对齐
        self._slots: List[np.ndarray] = []
        self._scores: List[float] = []
        self._issued = 0
        self._gen = 0
        self._best_score = -float("inf")
        self._stagnation = 0
        self._started = False

    # -- 算子 -------------------------------------------------------------
    def _sigma(self) -> float:
        """σ 线性退火 + 停滞回升（老家 sigma_for_gen 同式）。"""
        if self._gen <= 0:
            return self.sigma0
        t = min(1.0, self._gen / max(1, self.gens_hint - 1))
        return self.sigma0 - (self.sigma0 - self.sigma_min) * t

    def _mutate(self, x: np.ndarray, sigma: float) -> np.ndarray:
        child = x.copy()
        mask = self.rng.random(self.dim) < (1.0 / self.dim)
        if mask.any():
            child[mask] += self.rng.normal(0.0, sigma, int(mask.sum()))
        return np.clip(child, 0.0, 1.0)

    def _crossover(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        if self.rng.random() >= self.crossover_rate:
            return a.copy()
        take_b = self.rng.random(self.dim) < 0.5
        return np.where(take_b, b, a)

    def _tournament(self, pop: List[np.ndarray], scores: List[float]) -> np.ndarray:
        n = len(pop)
        k = min(self.tournament_k, n)
        idx = self.rng.choice(n, size=k, replace=False)
        best = int(idx[0])
        for j in idx[1:]:
            j = int(j)
            if scores[j] > scores[best] or (scores[j] == scores[best] and j < best):
                best = j
        return pop[best]

    def _init_population(self, center_score: float) -> None:
        """暖启锚点入种群，其余个体 = center + N(0, σ0)。"""
        center = np.asarray(self.center, dtype=float)
        self._slots = [center.copy()]
        self._scores = [center_score]
        sigma = self._sigma()
        for _ in range(self.pop_size - 1):
            self._slots.append(
                np.clip(center + self.rng.normal(0.0, sigma, self.dim), 0.0, 1.0))
        self._issued = 1

    def _evolve(self) -> None:
        """当代评估完毕：精英保留 + 锦标赛/均匀交叉/高斯变异繁殖下一代。"""
        pop = self._slots
        scores = self._scores
        order = sorted(range(len(pop)), key=lambda i: (-scores[i], i))
        gen_best = scores[order[0]]
        if gen_best > self._best_score + 1e-9:
            self._best_score = gen_best
            self._stagnation = 0
        else:
            self._stagnation += 1

        # 停滞回升：发情（σ 回到 σ0）只持续一代，与老家一致
        if self._stagnation >= self.stagnation_gens:
            self._gen = 0
            self._stagnation = 0

        children: List[np.ndarray] = [pop[i].copy() for i in order[:self.elitism]]
        while len(children) < len(pop):
            a = self._tournament(pop, scores)
            b = self._tournament(pop, scores)
            child = self._crossover(a, b)
            children.append(self._mutate(child, self._sigma()))

        self._gen += 1
        self._slots = children
        self._scores = []
        self._issued = 0

    # -- Optimizer 接口 ---------------------------------------------------
    def ask(self) -> List[float]:
        if not self._started:
            self._started = True
            self._slots = [np.asarray(self.center, dtype=float).copy()]
            self._issued = 1
            return [float(v) for v in self._slots[0]]
        if self._issued >= len(self._slots):
            # 正常不会发生（tell 满代即演化）；防御：无候选时重新采样
            self._init_population(self._best_score)
        x = self._slots[self._issued]
        self._issued += 1
        return [float(v) for v in x]

    def tell(self, x: List[float], score: float) -> None:
        self.log(x, score)
        self._scores.append(float(score))
        if not self._started:
            return
        # 暖启锚点评估完 → 铺开第一代
        if len(self._slots) == 1 and len(self._scores) == 1:
            self._init_population(float(score))
            return
        # 当代全部评估完 → 繁殖
        if len(self._scores) >= len(self._slots):
            self._evolve()
