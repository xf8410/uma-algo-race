# -*- coding: utf-8 -*-
"""BORE：密度比贝叶斯优化（Bayesian Optimization by Density-Ratio Estimation）。

入选理由（docs/blackbox-selection.md #5）：TPE 的亲戚但分类器用 GBDT——
把采集函数变成"好/坏二分类"，对 45 维混合空间比 optuna 默认更对症。

实现（Tiao et al. 2021，小预算实用变体，与原论文的偏差已标注）：
- 维护历史 H = [(xᵢ, yᵢ)]；γ = 历史 top 25% 分位线，y ≥ γ 记"好"
- 分类器：sklearn GradientBoostingClassifier（GBDT 家族，纯 CPU）
- 采集：采样 240 个候选（50% 全域均匀 + 50% 围绕历史最优点 N(σ0)），
  取分类器 P(好) 最大者 —— 与原论文"从先验采大样本取 argmax"同构，
  增加局部候选是小预算下的实用强化（原论文候选池=先验分布）
- 冷启动（历史 < 8 条）：center 锚点 + 围绕 center 的 σ0 探索
- 首发固定评估 center（warm-start 锚点，与 cmaes/xnes 同款）
"""
import numpy as np
from typing import List

from .base import Optimizer


class BoreOptimizer(Optimizer):
    name = "bore"

    def __init__(self, dim: int, seed: int = 7, sigma0: float = 0.15, center=None):
        super().__init__(dim, seed, center)
        self.sigma0 = float(sigma0)
        self.rng = np.random.default_rng(seed)
        self.hist_x: List[np.ndarray] = []
        self.hist_y: List[float] = []
        self._first = True
        self._n_cand = 240
        self._warmup = 8

    # -- Optimizer 接口 ---------------------------------------------------
    def ask(self) -> List[float]:
        if self._first:
            self._first = False
            return list(self.center)
        # 冷启动：围绕 center 探索
        if len(self.hist_x) < self._warmup:
            x = np.asarray(self.center, dtype=float) + \
                self.rng.normal(0.0, self.sigma0, self.dim)
            return [min(1.0, max(0.0, float(v))) for v in x]
        # BORE 主循环：好/坏分类 → 采候选 → argmax P(好)
        from sklearn.ensemble import GradientBoostingClassifier
        y_arr = np.asarray(self.hist_y)
        gamma = np.quantile(y_arr, 0.75)
        label = (y_arr >= gamma).astype(int)
        if label.sum() == 0 or label.sum() == len(label):
            # 分位线退化（全同分）：退回探索
            x = np.asarray(self.center, dtype=float) + \
                self.rng.normal(0.0, self.sigma0, self.dim)
            return [min(1.0, max(0.0, float(v))) for v in x]
        clf = GradientBoostingClassifier(
            n_estimators=50, max_depth=3, random_state=int(self.rng_seed))
        clf.fit(np.stack(self.hist_x), label)
        # 候选池：一半全域均匀，一半围绕历史最优
        n_uni, n_loc = self._n_cand // 2, self._n_cand - self._n_cand // 2
        cands = [self.rng.uniform(0.0, 1.0, self.dim) for _ in range(n_uni)]
        best_x = self.hist_x[int(np.argmax(y_arr))]
        cands += [best_x + self.rng.normal(0.0, self.sigma0, self.dim)
                  for _ in range(n_loc)]
        cands = [np.clip(c, 0.0, 1.0) for c in cands]
        P = clf.predict_proba(np.stack(cands))[:, 1]
        x = cands[int(np.argmax(P))]
        return [min(1.0, max(0.0, float(v))) for v in x]

    def tell(self, x: List[float], score: float) -> None:
        self.log(x, score)
        self.hist_x.append(np.asarray(x, dtype=float))
        self.hist_y.append(float(score))
