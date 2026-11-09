# 最高分蒸馏报告

> 目标：回答「上游这批迭代分数里，最高分是什么、能不能拿来继续迭代」。
> 结论先行：**数值最高的 91535.7 不是可迭代的冠军；真正可迭代的是三份 GA 冠军 genome。**

## 一、蒸馏了什么

从上游 `47e177df` 的五类来源里，把「分数」与「产生分数的参数」拆开：

| 来源 | 提供了什么 |
|---|---|
| `baselines/a-normal.json` / `b-ideal.json` | 4 个绝对分锚（score/PT/σ/局数/种子） |
| `baselines/README.md` | 口径定义、档间差、判定与重录纪律 |
| `data/matsuri_config.toml` | 三档 GA 冠军的**完整 74 维参数**（定档本体） |
| `data/plan/deck_param_scan.md` §10.2 | 冠军的配对 Δ / t / 走满率 / 门禁口径 |
| `scripts/ga_trainer.py` + `search_check.py` | 产生冠军的搜索器与验收器 |

产物：`scoreboard.csv`（7 条，每条带 `comparable_group` 口径标签）
+ `genome_g0269_default.toml` / `genome_g0109_stamina.toml` / `genome_g0339_wisdom.toml`。

## 二、为什么「最高分」不能直接拿来迭代

`91535.7` 是 `b-ideal` 档（`uma=106302`，小切 + 心情盾 2）在 `search_n=8192`、
`seed0=73200` 起 **10 局**的均分。它高，是因为叠了三样**局外条件**：

- 理想马娘（狄杜斯）+ 局外 buff（小切 PT×1.04、盾 2）；
- 搜索档比手写档本身就有 +3150.4 的固有增益；
- 样本仅 10 局，σ=765.1。

它是一个**观测值**，不是一组可迁移的决策参数。拿它当「冠军」去暖启，
等于把「换个更强的马娘 + 开 buff」当成算法进步——这正是本仓 `BASELINE.md` §三
反复警告的「跨口径比大小」和「mock 景观王 ≠ 真王」。

## 三、真正可迭代的冠军：三份 GA genome

上游 `ga_trainer.py` 用 74 维 CMA-ES（39 训练员旋钮 + 融合 5 随机键 +
6 教诲窗口×5 键），以 λ=48、σ₀=0.1、手写档、3 马娘×4 种马 CRN 配对搜索，
经「复核分最高 + 对现值/起点 z>2.58 + 影子卡组同向 + 友人走满率」门禁后定档。

| genome | 档 | 蒸馏出的参数 | 搜索档配对 Δ | t | 文件 |
|---|---|---|---|---|---|
| **g0269** | default / 21101 | `pt_favor_rate=1.931954`, `free_race_urgency=1.764718`, 6 教诲窗口, 完整 weights/dynamic/overflow/endgame | +898 ±259 | 3.47 | `genome_g0269_default.toml` |
| g0109 | stamina / 12101 | `pt_favor_rate=2.130577`, 全套独立旋钮 | +621 ±262 | 2.37 | `genome_g0109_stamina.toml` |
| g0339 | wisdom / 11102 | `pt_favor_rate=1.799203`，`status_weights` 第 5 维（智）压到 0.024016（config L247） | +553 ±194 | 2.85 | `genome_g0339_wisdom.toml` |

**蒸馏动作**：把 `matsuri_config.toml` 里 `[decks.default]` / `[decks.stamina_build]` /
`[decks.wisdom_build]` 三段各自抽成**只含一个 `[decks.<档>]` 表**的片段
（段名改为 `champion_g0269` 等），保留 fusion / advice / trainer 全部 13 组旋钮，
并用 `tomllib` 逐个验证可解析、单表、含 `pt_favor_rate`。

这样切是因为上游 `ga_trainer.py::load_point()` 要求 `--start` 片段
「必须只含一个 `[decks.<档>]` 表」，会 `merge` 到默认层之上。
**这三份片段可以直接喂给 `--start` 做暖启，不需要任何手工改格式。**

## 四、蒸馏产物校验记录

```
genome_g0269_default.toml : 单表 ✓  trainer 13 组 ✓  fusion.year3=3 ✓  advice 6 窗口 ✓  95 行
genome_g0109_stamina.toml : 单表 ✓  trainer 13 组 ✓  fusion.year3=3 ✓  advice 6 窗口 ✓  71 行
genome_g0339_wisdom.toml  : 单表 ✓  trainer 13 组 ✓  fusion.year3=3 ✓  advice 6 窗口 ✓  72 行
```

字段隔离校验：三份 genome 均 **0 次**命中拉面参数面字段
（`pt_tradeoff`/`ramen_*`/`vital_rest`/`shining_bonus`/`status_rate`）。

## 五、「蒸馏」的边界（如实说明）

本轮蒸馏是**对上游已验证数据的结构化提纯**：把散在 JSON / TOML / Markdown 里的
分数与参数收敛成机器可读台账 + 可加载 genome，并写明每个数字的可比组。
**没有重新跑任何一局评测**，因此不产生新分数、不宣称超过上游。
真正「更高分」必须调用 `cardtest` 实跑，路径见 `iterate/ITERATE.md`。
