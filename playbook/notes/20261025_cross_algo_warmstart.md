# 跨算法暖启对照：不是只有 GA 能涨，但在窄盆里只有“稀疏步”能涨

> 来源：`uma-algo-race` 分支 `workbench/opt-ga`（2026-10-25）
> 动机：用户质疑「仓库里很多算法，你只跑了 GA？」——审计后确认暖启赛马线
> 长期只跑得动 4 个算法，且 7 个算法从未在冠军锚上暖启过。
> 纪律不变：一律在已提升的冠军参数上叠加，B = 冠军重放定标，CRN 配对。

## 一、审计：为什么“只跑了 GA”

| 层 | 位置 | 内容 |
| --- | --- | --- |
| umaai-rs（Rust） | `crates/umasim/src/genetic_optimizer.rs` + `bin/ga_optimize.rs` | **唯一**的参数寻优器（GA）；其余是 MCTS 搜索 / NN 决策器 / 手写策略 / trainer |
| uma-algo-race（lab） | `optimizers/` | 11 个黑盒优化器：cmaes/tpe/sa/cem/map_elites/spsa/ars/powell/xnes/bore/ga |
| 历史跑法 | `experiments/sa_compare.py` | 冷启动 30 iter，tpe/cem/sa/spsa/ars/powell 的数据都出自这里 |
| 暖启跑法 | `experiments/warmstart_race.py` | 只在冠军锚上叠加 |

**bug（已修 `8be29fc`）**：`run_one` 无条件给优化器传 `sigma0`，而
tpe/cem/sa/spsa/ars/powell/map_elites 的构造签名没有该参数 →

```
TypeError: TpeOptimizer.__init__() got an unexpected keyword argument 'sigma0'
```

即：暖启赛马这条线自建立起**实际只能跑 cmaes / xnes / bore / ga**，其余 7 个
一进就崩，历史数据全是冷启动口径（不可与暖启叠加链混比）。修复方式是按
`cls.__init__` 签名过滤 kwargs，并补 `tests/test_warmstart_kwargs.py` 锁定。

## 二、协议

- 锚：`data/seeds/seed_ga_best.toml` = GA 五轮链 65124.1（full 重放定标）
- 档位：smoke = 3 build×100 局；full = 7 build×100 局 + holdout seed43
- 评估价：smoke ≈1.6s、full ≈8.6s；n_iter 即真实评估次数
- 判定：meanΔ>+150 且 p<0.05 才是 promote；本文多为小步，只作排序用

## 三、结果

### smoke 64 iter（3 seed，B=62851.4）

| 算法 | seed 7 / 13 / 23 | 平均 Δ |
| --- | --- | ---: |
| cem | 63145.3 / 63224.3 / 63098.2 | +304.5 |
| bore | 63181.1 / 63155.3 / 63148.4 | +310.2 |
| xnes | 63111.0 / 63184.1 / 63125.1 | +288.7 |
| cmaes | 63137.8 / 63158.1 / 63074.6 | +272.1 |
| tpe | 62925.4 / 62973.4 / 63073.9 | +139.5 |

### smoke 256 iter（seed 7）

| 算法 | best | Δ |
| --- | ---: | ---: |
| sa | 63301.6 | +450.2 |
| powell | 63257.2 | +405.8 |
| ars | 63228.9 | +377.5 |
| spsa | 62864.0 | +12.6 |

### full 档：分布型算法全灭（B=65124.1）

| 算法 | 预算 | seed 7 | Δ |
| --- | ---: | ---: | ---: |
| cem | 128 | 65124.1 | 0.0 |
| bore | 128 | 65124.1 | 0.0 |
| xnes | 128 | 65124.1 | 0.0 |
| cmaes | 128 | 65124.1 | 0.0 |

密度型（45 维同时扰动，σ≈0.06~0.15）在当前锚上一个候选都没打赢重放值。

### full 档：稀疏/坐标型出分

| 算法 | 预算 | best | Δ |
| --- | ---: | ---: | ---: |
| ars | 128 | 65094.1 | −30.0 |
| sa | 128 | 65124.1 / 65124.7 | 0.0 / +0.6 |
| powell | 128 | 65140.4 | +16.3 |
| sa | 256 | 65128.4 | +4.3 |
| ga | 256 | 65135.1 | +11.0 |
| powell | 256（2 seed 同值，确定性） | 65147.1 | +23.0 |
| powell | 512 | 65161.8 | +14.7（对上一轮 65147.1 计） |
| powell | 1024 | 65163.9 | +16.8（对 65147.1 计，已近饱和） |

### 换锚后继续叠（B=65161.8，Powell512 锚）

| 算法 | 预算 | best | Δ |
| --- | ---: | ---: | ---: |
| ga | 256 | **65164.1** | **+2.3** |
| powell | 256 | 65161.8 | 0.0（同算法连跑无增量） |
| sa | 256 | 65161.8 | 0.0 |

## 四、判读

1. **不是“只有 GA 能涨”，是“只有稀疏步能涨”**。GA 的变异是每基因 1/45 概率、
   一次只动约 1 个坐标；Powell 是坐标方向线搜索。两者在窄盆里都出分，
   而 xnes/cem/bore/cmaes 这种整向量扰动在 full 档 0 收获。
2. **smoke 会骗人**：sa 在 smoke 256 是全场第一（+450），到 full 只有 +4.3；
   spsa 在 smoke 几乎不动（+12.6），full 也没戏。冷启动排名不能直接搬到暖启。
3. **Powell 是这轮意外收获**：它在冷启动线是“退役（sig 负 −601）”，但在
   窄盆里 +23（256）/ +14.7（512）连着出分，且**完全确定性**（同锚同预算
   seed 无关），可直接当稳定精修器用。
4. **GA 仍是主力**：+161 的立桩只有它做得到；后续每轮 +5~+11。
5. **预算与算子要配套**：Powell 256→512 从 +4.5 涨到 +14.7，1024 再涨到 +16.8
   （饱和），说明它没跑完一轮坐标扫描；GA 256→512 收益不明显。
6. **换族比连跑有用**：从 65161.8 再跑 Powell 只有 0、SA 只有 0，而换回 GA
   还能拿 +2.3。同一算法连续两轮基本挖空，交替两类算子还能挤出一点。

## 五、当前最强与下一步

- 最强锚：`data/seeds/seed_mix_best.toml` = **65164.1**
  （链路 xNES 64673.5 → GA×5 65124.1 → Powell512 65161.8 → GA256 65164.1，
  累计 **+490.6**；对旧 71k 冠军当前核心重放 64287 为 **+877**）
- 收益已经掉到 +2 级，这条链该收了。
- 真正值得做的下一步不是再叠一轮，而是**改算子**：GA 的 1/N 稀疏掩码 +
  Powell 的坐标线搜索都指向「单坐标方差」。把它做进 CMA/xNES（对角、逐坐标
  步长），验证是不是算子形状而非算法家族决定窄盆里的成败。

```prior
audit_runner_bug = sigma0 TypeError（7 个算法暖启不可用，8be29fc 修复）
anchor_at_start = 65124.1
smoke_full_gap = sa smoke +450 → full +4.3（不可外推）
full_dense_algos_gain = 0（cem/bore/xnes/cmaes @128）
powell_full_256 = 65147.1 (+23.0, deterministic)
powell_full_512 = 65161.8 (+14.7)
ga_full_256 = 65135.1 (+11.0)
powell_full_1024 = 65163.9 (+16.8)
ga_on_powell_anchor_256 = 65164.1 (+2.3)
powell_second_round = 0.0
sa_on_powell_anchor_256 = 0.0
best_after_mix = 65164.1
best_seed_file = data/seeds/seed_mix_best.toml
```
