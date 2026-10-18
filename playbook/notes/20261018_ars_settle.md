# ARS 晋级裁决收账：定格 promote_mild 观察位（run 2）

> 来源：uma-algo-race workbench/opt-ars-10seed run 2（10 seed × 60 iter CRN 配对，12h）
> 日期：2026-10-18
> 优先级：high（run4 候补的正式裁决——负结果也是结论）

## 裁决数据

| 项 | 值 |
|---|---|
| 配对 Δ(ars−cmaes) | **+3.7**（std 82.6，t=0.143，p=0.8896） |
| ars 10 seed mean | ≈63486（best 63388~63564） |
| cmaes 10 seed mean | ≈63483（best 63350~63547） |
| 裁决 | **promote_mild_hold**（不晋级主战表） |

## 判读

1. **run4 的 +42.2 是噪声**：5 seed 下 ARS 领先 CMA-ES 42 分，10 seed × 双倍
   iter 后缩到 +3.7（p=0.89）——run4 那口气优势没有在大样本下存活。
   这正是"5 seed n.s. 不 promote，加预算裁决"流程的价值：挡掉了一次假晋级。
2. **ARS 的稳定性叙事保留但降级**：std 82.6 与 cmaes 相当（run4 里 44 vs 77 的
   差距也没守住），"全场最稳"是 5 seed 小样本假象。
3. **定格 promote_mild 观察位**：与 cmaes_n60 同级（该笔记先例：显著但量级
   <150 只 mild）。后续如果跑 ensemble/混合策略，ARS 当低方差基座候补。

## 下一步（对 BASELINE.md 主战表无影响）

- 参数面结论加固：**tpe/cem/ars/cmaes 在 smoke 口径 30-60 eval 预算内
  统计不可分**——参数面边际收益挤干的第三块证据（sa/powell/spsa 退役 +
  ars/cem/cmaes/tpe 打平）
- 重心正式转向：#6 Hyperband 调度（同样算力多筛 3-5 倍）与
  #10 GBDT 叶子评估器（决策面，5.6 万局数据现成）

```prior
ars_delta_10seed = 3.7
ars_p = 0.8896
verdict = promote_mild_hold
run4_delta_was_noise = true
param_face_saturated_evidence_count = 3
```
