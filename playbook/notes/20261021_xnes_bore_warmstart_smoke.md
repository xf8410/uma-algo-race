# xNES/BORE 暖启赛马：smoke 5 seed 双双显著出线（run 2）

> 来源：uma-algo-race workbench/opt-xnes-bore-warmstart，warmstart-race run 2（workflow_dispatch 全协议）
> 日期：2026-10-20
> 优先级：high（第二梯队两个新算法在冠军参数上叠加的首次真 bench）

## 背景（用户纪律 2026-10-20）

- 「加算法 = 在已经有的、已经提升过的冠军参数之上叠加，不许独狼跑」
  → 暖启种子 = `data/seeds/seed_tpe_best.toml`（TPE best，71k 口径 71692），
  所有算法从同一冠军向量出发，sigma0=0.15（playbook v3 先例）
- 「没有提高，立马换算法」→ 判读阈值 Δ>+150 且 p<0.05（promote_mild 线）
- 纯 CPU，不碰 GPU（xNES=分布自然梯度，BORE=GBDT 分类器采集，均无 GPU 依赖）

## 协议

- 5 seed（7/13/23/31/47）× 30 iter，CRN（bench seed=42）配对
- 基线 B = 冠军重放定标（同场同码重放，口径漂移以本数为准）= **62823.4**
  - 口径说明：B 是 71k 冠军 genome 在 smoke 考场（3 初筛 build×100 局）的当前分，
    与 lab smoke 冠军 63499（从 center 优化的产物）不可直接比——B 偏低属口径差非退化
- 首发评估 center（锚点）：所有算法第一个 eval = 暖启点本身（缓存命中 0 局）

## 结果（5 seed × 30 iter，B=62823.4）

| 算法 | mean best | std | mean Δ | t | p | 判定 |
|---|---|---|---|---|---|---|
| xnes | 62996.5 | 49.0 | **+173.1** | 7.906 | 0.0014 | promote 候补 |
| bore | 63014.6 | 75.9 | **+191.2** | 5.631 | 0.0049 | promote 候补 |

per-seed Δ：xnes [+188/+160/+186/+100/+233]，bore [+292/+156/+124/+252/+133]，
**10/10 全正**（两算法各自 5 seed 全正）。

## 判读

1. **双出线**：两算法 Δ>+150 且 p<0.05，按 BASELINE 分层协议升 full 档裁决
   （7 build×100 局 + holdout 43），full 档 10 seed × 30 iter 已 dispatch
2. **ARS 假晋级防线**：5 seed 显著 ≠ 真 promote（ARS 先例 +42 → 10 seed +3.7），
   full 裁决直接上 10 seed 防缩水
3. **xnes vs bore 风格差**：xnes 稳（std 49，5 seed 紧凑），bore 冲（Δ 最高 +292 但
   波动 76）——与理论预期一致（xNES 分布收缩稳、BORE 分类器采集激进）
4. 参数面已知三块挤干证据不变（sa/powell/spsa 退役 + 4 算法打平）：本结果不推翻
   「参数面边际收益有限」——但说明**从 71k 冠军暖启**与从 center 冷启是两个山头，
   暖启线上还有 +150~200 的肉（先前 playbook warmstart v3 的 +46.5 是 cmaes 冷启对照）

## 运行事故与修复（本笔记范围内的工程账）

- run 3 发现 txt 自动留档 push 被 403 静默吞（workflow 缺 permissions: contents: write），
  run 4 修复验证 ✓（race-bot 37713cf 自动入仓）
- run 2 的 txt 因旧 workflow 无 push 权限未入仓（数据完整保存在 result.json/artifact，
  本笔记补账；run 4 起管道正常）
- 首轮 dispatch 忘带 level 参数触发了一次 10 seed smoke（非浪费：与 run 2 的 5 seed
  对照可看 10 seed 稳定性）

```prior
warm_seed_file = seed_tpe_best.toml
warm_baseline_smoke_B = 62823.4
xnes_mean_delta_5seed = 173.1
xnes_p = 0.0014
bore_mean_delta_5seed = 191.2
bore_p = 0.0049
```

## Full 档 10 seed 终裁（run 8，2026-10-21 00:12 UTC 完成）

- B = **64487.2**（tpe_best genome 在 full 考场当前重放，7build×100局）
- 协议：10 seed（7/13/23/31/47/101/103/107/109/113）× 30 iter，CRN，总 3099.7s

| 算法 | mean best | std | Δ vs B | t | p | 终判 |
|---|---|---|---|---|---|---|
| **xnes** | 64641.5 | 27.6 | **+154.3** | 17.68 | <0.001 | **正式 promote**（过 +150 线） |
| bore | 64633.2 | 33.3 | +146.0 | 13.88 | <0.001 | mild 观察（差 4.0 分到线） |

- **双 10/10 全正**：ARS 式缩水未发生（5seed 优势保住了），只是排名反转
  （smoke 时 bore>xnes，full 时 xnes>bore——xNES std 27.6 更稳）
- 最强单 seed：xnes seed=13 → 64673.5（Δ+186.3）

```prior
full_baseline_B = 64487.2
xnes_mean_delta_10seed_full = 154.3
xnes_t_10seed = 17.68
bore_mean_delta_10seed_full = 146.0
verdict_xnes = PROMOTED
verdict_bore = mild_watch
chain_now = GA_r8_71415.6 -> TPE_71692 -> xNES_64641.5_full_mean
```

## 下一步

- [x] full 档 10 seed 裁决出数 → **xNES promote**（2026-10-22 收账）
- [x] 胜者 genome 导出：warmstart_race.py 加 best_x/CHAMPION.toml 导出，单 seed=13
      full 复现 dispatch（确定性保证 = run8 同轨迹）
- [ ] CHAMPION.toml → data/seeds/seed_xnes_best.toml 新暖启锚（PR 进 main 时收）
- [ ] 下一棒新算法从 xNES 锚暖启（MOBO/Thompson-UCB/Hyperband 候选）——
      用户纪律「在已有最高分上叠加」→ 叠加链继续延长

## 关联

- run 2 artifact：warmstart-race-result（result.json + report.md）——smoke 5seed
- run 8 artifact：warmstart-race-result——full 10seed 终裁
- run 6 artifact：10 seed smoke 对照（实测 xnes +169.5±39.6 / bore +195.8±59.3，
  双双 p≈0 保持显著——smoke 5seed→10seed 不缩水；BORE 的 smoke 优势到 full 考场
  缩到 +146（差 4 分落 mild），xNES 两档都稳）
- 代码：optimizers/xnes_opt.py / bore_opt.py / experiments/warmstart_race.py
- 协议出处：BASELINE.md 分层协议 + ARS 10 seed 先例（20261018_ars_settle.md）
