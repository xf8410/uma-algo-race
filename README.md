# 赛马娘算法赛马场 v2（uma-algo-race）

**一句话：固定模拟器黑盒上的优化器赛马，树杈纪律运行——每算法每种子一根 workbench/ 杈，好种子输了也不删，main 只收账。**

## 为什么从 uma-algo-lab 搬家

1. lab 主干曾被 .venv 污染（2816 文件）+ AI 直推 main 越过审查
2. 历史锚点散在报告仓里，比赛没有统一基准表
3. 需要正式的树杈工作流（对齐 nn-lab 49 杈 / umaai-rs 41 杈的用户工作流）

## 树杈纪律（AGENTS.md 是硬约束）

```
main ── 只收账（锚点+已收账算法+结论）
 ├─ workbench/opt-<算法>    新优化器（每算法一杈）
 ├─ workbench/race-<主题>   赛马与收账跑批
 └─ workbench/seed-<名>     策略/基因组种子变体（输了不删）
```

## 历史锚点（BASELINE.md 唯一权威）

| 锚 | 分数 | 口径 |
|---|---|---|
| GA r8 冠军 | **71415.6** | 7 卡组 × 60 局精评（71k 老家） |
| TPE best | 71692（≈71554） | 同口径 CRN 配对 |
| GA E2b 自搜 | 79402（折算） | 考场变严疑点未定标 |
| lab smoke 基准 | 63323（center cold） | 3 初筛卡组 × 100 局 |

**跨口径不可比**。新算法先在 smoke 出头 → full 档 + holdout → 才挑战绝对锚。

## 快速开始

```bash
pip install -r requirements.txt
export UMA_BENCH_BIN=/path/to/bench_base
python experiments/sa_compare.py --optimizers ars,cmaes,tpe --budget 60 --uma 111501
```

## 存档战绩（2026-10-18）

tpe 63499 现任冠军 | ars 63438±44 晋级候补 | cem/cmaes 活跃 | sa/powell/spsa 退役（各带档案结论）
