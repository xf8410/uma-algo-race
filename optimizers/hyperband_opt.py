# -*- coding: utf-8 -*-
"""Hyperband：多臂 SuccessiveHalving 早停（Li et al. 2018）。

入选理由：与 GA/TPE/xNES/BORE 这些「分布面搜索」互补——Hyperband 走「多精度早停」，
用便宜的粗评先筛掉大把候选，只对少数幸存者加精度精评，省算力。

实现（纯 CPU，手写，numpy 即可）：
- 资源维度 = 评估精度（每 build 模拟局数）。r 小 = 快速粗评（噪声大但便宜），
  r 大 = 满精度精评。
- 外层 bracket 循环：s ∈ {s_max … 0}，每个 bracket 预算 B = (s_max+1)·R。
- 内层 SuccessiveHalving：n 个候选从资源 r0 起步，每轮按分数保留 top ⌊n/η⌋，
  幸存者资源 ×η，直到只剩 1 个或达到满资源 R。
- 候选生成：center 暖启锚（首法固定评估 center，与 cmaes/xnes/bore 同款）
  + 围绕 center 的高斯扰动 σ0。

适配说明（重要）：
- 标准 Optimizer 接口 ask() 只吐候选向量、不吐资源；compare.py 是「固定精度」评估
  （smoke=3build×100局 / full=7build×100局）。
- 为此本优化器额外暴露 `requested_resource`：每次 ask 后给出该候选需要的评估局数。
  compare.py 忽略它（此时 Hyperband 退化为「固定精度 SuccessiveHalving」，仍可用）；
  experiments/hyperband_run.py 读取它，用Evaluator 的变 runs 做真·多精度早停。
"""
import math
import numpy as np
from typing import List, Optional

from .base import Optimizer


class HyperbandOptimizer(Optimizer):
    name = "hyperband"

    def __init__(self, dim: int, seed: int = 7, center=None,
                 eta: int = 3, min_resource: float = 10.0,
                 max_resource: float = 100.0, sigma0: float = 0.15):
        super().__init__(dim, seed, center)
        self.eta = int(eta)
        self.min_resource = float(min_resource)
        self.max_resource = float(max_resource)
        self.sigma0 = float(sigma0)
        self.rng = np.random.default_rng(seed)

        # s_max = 多少个 bracket；B = 每 bracket 总资源预算
        s_max = int(math.floor(math.log(max_resource / min_resource) / math.log(self.eta)))
        self.s_max = max(1, s_max)
        self.B = (self.s_max + 1) * self.max_resource

        # 一次性排好所有 bracket 的首轮参数
        self._brackets = self._plan_brackets()

        # 状态机
        self._bi = 0                       # 当前 bracket 下标
        self._round = 0                    # 当前 SH 轮次（0-based）
        self._population: List[np.ndarray] = []   # 本轮候选向量
        self._scores: List[float] = []     # 本轮已收分数
        self._resource: float = self.max_resource  # 本轮资源（评估局数）
        self._ask_pos = 0                  # 本轮已 ask 到第几个
        self._done = False
        self._start_bracket(0)

    # -- 规划 -----------------------------------------------------------
    def _plan_brackets(self) -> List[dict]:
        """Li et al. 2018：每 bracket 的 (n0, r0, rounds)。

        n0 = ceil((B/R) · η^s / (s+1))，r0 = R · η^{-s}，rounds = s+1。
        """
        out: List[dict] = []
        for s in range(self.s_max, -1, -1):
            n0 = int(math.ceil((self.B / self.max_resource)
                               * (self.eta ** s) / (s + 1)))
            n0 = max(1, n0)
            r0 = self.max_resource / (self.eta ** s)
            out.append({"s": s, "n0": n0, "r0": r0, "rounds": s + 1})
        return out

    def _sample(self) -> np.ndarray:
        """围绕 center 的高斯扰动候选（暖启锚局部探索）。"""
        x = np.asarray(self.center, dtype=float) + \
            self.rng.normal(0.0, self.sigma0, self.dim)
        return np.clip(x, 0.0, 1.0)

    def _start_bracket(self, bi: int) -> None:
        b = self._brackets[bi]
        pop = [np.asarray(self.center, dtype=float)]          # 首法 = center 锚
        pop += [self._sample() for _ in range(b["n0"] - 1)]   # 其余采样
        self._population = pop
        self._resource = float(b["r0"])
        self._scores = []
        self._ask_pos = 0
        self._round = 0

    # -- Optimizer 接口 ---------------------------------------------------
    @property
    def requested_resource(self) -> float:
        """本次 ask 候选所需的评估精度（局数）。

        compare.py 固定精度下忽略此值；hyperband_run.py 用它做多精度早停。
        """
        return self._resource

    def ask(self) -> List[float]:
        if self._done:
            raise RuntimeError("hyperband: 所有 bracket 已跑完")
        if self._ask_pos >= len(self._population):
            raise RuntimeError("hyperband: ask 越界（前一轮 tell 未触发淘汰）")
        x = self._population[self._ask_pos]
        self._ask_pos += 1
        return [min(1.0, max(0.0, float(v))) for v in x]

    def tell(self, x: List[float], score: float) -> None:
        self.log(x, score)
        self._scores.append(float(score))
        if len(self._scores) >= len(self._population):
            self._advance()

    def _advance(self) -> None:
        """一轮收齐分数后：SuccessiveHalving 淘汰 → 幸存者下一轮（资源 ×η）。

        标准 SH 最后一轮是「1 个幸存者 @ 满资源 R」的最终精评；故只当
        幸存者已用满资源评估过才结束本 bracket（否则资源顶到 R 再精评一次）。
        """
        b = self._brackets[self._bi]
        idx = np.argsort(self._scores)[::-1]             # 分数降序（最大化）
        n_keep = max(1, len(self._population) // self.eta)
        survivors = [self._population[i] for i in idx[:n_keep]]
        self._round += 1
        at_max = self._resource >= self.max_resource - 1e-9
        # 满资源且只剩一个幸存者，或已跑满轮次 → 本 bracket 结束
        if (n_keep == 1 and at_max) or self._round >= b["rounds"]:
            self._bi += 1
            if self._bi >= len(self._brackets):
                self._done = True
            else:
                self._start_bracket(self._bi)
            return
        # 幸存者进入下一轮，资源 ×η；若只剩一个则直接顶到满资源做最终精评
        self._population = survivors
        self._resource = self.max_resource if n_keep == 1 else self._resource * self.eta
        self._scores = []
        self._ask_pos = 0