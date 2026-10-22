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
from .hyperband_opt import HyperbandOptimizer

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
    # 2026-10-23 第三梯队：multi-fidelity 早停（blackbox-selection 补位）。
    # 与分布面搜索互补，用「少局数粗筛 + 幸存者加精度」省算力；固定精度下退化 SH。
    "hyperband": HyperbandOptimizer,
}
