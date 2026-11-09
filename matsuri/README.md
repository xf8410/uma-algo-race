# matsuri/ — 骏大祭（新剧本）独立命名空间

> 建立于 2026-11-09，分支 `workbench/seed-matsuri-champion-20261109`。
> 数据来自上游 `umaai-project/umaai-matsuri` @ `47e177df`（2026-11-09 17:02 +0800）。

## 一句话

把**骏大祭剧本**的最新迭代分数数据、GA 冠军参数与迭代工具同步进实验室，
**在完全独立的口径下**蒸馏最高分，并搭建继续冲更高分的暖启脚手架。

## 硬纪律：口径隔离（本目录存在的前提）

本仓 `lab/`、`BASELINE.md`、`data/seeds/seed_*.toml` 属于**拉面 / 71k 老家口径**：
固定模拟器 `bench_base`、`lab/space.py` 70 字段（`pt_tradeoff` / `ramen_*` / `vital_rest`）、
绝对锚 71415.6 / 71692 / 79402、优化器 TPE / xNES / CMA-ES 赛马。

本目录属于**骏大祭 / 官方评分口径**：考场 `cardtest`、参数面 `matsuri_config.toml`
74 维（`pt_favor_rate` / `status_weights` / `endgame.*`）、基线 83793.9 ~ 91535.7、
搜索器为上游 `ga_trainer.py` 的 74 维 CMA-ES。

| 项 | `lab/`（拉面，禁止混入） | `matsuri/`（本目录） |
|---|---|---|
| 考场 | `bench_base` | `cardtest` |
| 参数面 | 70 字段 `lab/space.py` | 74 维 `matsuri_config.toml` |
| 训练员 | RecommendedRamenTrainer | 骏大祭手写训练员 |
| 分数口径 | 7 卡组×60 局精评 / smoke | 官方评分，固定马娘×种子×`search_n` |
| 锚点表 | `BASELINE.md`（唯一权威） | `ANCHOR_MATSURI.md`（本口径唯一权威） |
| 优化器 | TPE/xNES/CMA-ES/TPE 赛马 | `ga_trainer.py` 74 维 CMA-ES |

**三条不可违反**：

1. `BASELINE.md` 与 `ANCHOR_MATSURI.md` 是两张**互不相认**的表。
   跨口径换算因子不存在；任何「91535.7 比 79402 高」的陈述都是错的。
2. 本目录的**数据文件**禁止出现 `pt_tradeoff` / `ramen_*` / `vital_rest` /
   `shining_bonus` / `status_rate` / `bench_base` 等拉面参数面字段及其锚点分数，
   由 `iterate/verify_isolation.py` 门禁强制（本地可跑，也可接入 CI）。
3. `lab/space.py`、`lab/genome.py`、`optimizers/*`、`experiments/*` 一行不改、不引用。
   本目录的脚手架只用 `tools/ga_trainer.py`（上游原样搬运）。

## 目录导览

| 路径 | 内容 |
|---|---|
| `README.md` | 本文件：口径边界与纪律 |
| `SOURCE.yaml` | 数据来源登记：commit、每个文件的 SHA256、同步时间 |
| `ANCHOR_MATSURI.md` | **新开的骏大祭口径锚线**（本口径唯一权威表，比大小先对口径） |
| `baseline/` | 上游 `baselines/` 原样（a-normal / b-ideal JSON + README） |
| `data/matsuri_config.toml` | 上游 GA 定档全参数（三档冠军的源） |
| `data/decks/` | 上游 5 份卡组夹具 CSV |
| `data/plan/` | 上游本轮计划书 / 参数扫描 / 定卡文档 |
| `tools/ga_trainer.py` | 上游 74 维 CMA-ES 搜索器（原样） |
| `tools/search_check.py` | 上游搜索档配对验收（原样） |
| `champion/CHAMPION.md` | **蒸馏报告**：最高分是什么、怎么来、为什么它才是可迭代的 |
| `champion/scoreboard.csv` | 机器可读分数台账（每条带 `comparable_group` 口径标签） |
| `champion/genome_g*.toml` | **蒸馏产物**：三份可被 `--start` 直接加载的冠军 genome |
| `iterate/ITERATE.md` | 迭代到更高分的 runbook（步骤、命令、门禁、判定） |
| `iterate/gate.py` | 分数门禁判定脚本（真实可跑） |
| `iterate/verify_isolation.py` | **口径隔离门禁**：扫数据文件、验 genome/台账/SOURCE SHA256 |
| `iterate/warmstart.sh` | 暖启启动脚本（真实命令，非占位） |

## 树杈纪律

按本仓 `AGENTS.md`：`main` 只收账，实验/新数据一律上 `workbench/` 树杈。
本目录整包落在 `workbench/seed-matsuri-champion-20261109`，**未触碰 `main`**。
跑出显著结论后由用户点头再 PR 合流；本轮不合并。
