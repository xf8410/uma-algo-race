# -*- coding: utf-8 -*-
from .base import Optimizer
from .cmaes_opt import CmaesOptimizer
from .cem_opt import CemOptimizer
from .ars_opt import ArsOptimizer
from .map_elites_opt import MapElitesOptimizer
from .powell_opt import PowellOptimizer
from .sa_opt import SaOptimizer
from .spsa_opt import SpsaOptimizer
from .tpe_opt import TpeOptimizer
from .xnes_opt import XnesOptimizer
from .bore_opt import BoreOptimizer
from .thompson_ucb_opt import ThompsonUcbOptimizer

REGISTRY = {
    "cmaes": CmaesOptimizer,
    "tpe": TpeOptimizer,
    "sa": SaOptimizer,
    "cem": CemOptimizer,
    "map_elites": MapElitesOptimizer,
    # 2026-10-17 第一梯队新增（docs/blackbox-selection.md）：
    # spsa 一次扰动估全维梯度（2 评估/步）；ars top-k 方向平均；
    # powell 自实现方向集（经典 DFO 对照）
    "spsa": SpsaOptimizer,
    "ars": ArsOptimizer,
    "powell": PowellOptimizer,
    # 2026-10-20 第二梯队补位（blackbox-selection #3/#5，tier1 收账后排队项）：
    # xnes 分布参数自然梯度（CMA-ES 同族对照）；bore 密度比 BO（GBDT 分类器）
    "xnes": XnesOptimizer,
    "bore": BoreOptimizer,
    # 2026-10-23 第三梯队冲高分：局部高斯后验 + 随机乐观 β 的 bandit 采集
    # （μ̂=k 近邻均值, σ̂=邻域 std，α=μ̂+βσ̂ 取 argmax）——贝叶斯后验更新路线
    "thompson_ucb": ThompsonUcbOptimizer,
}
