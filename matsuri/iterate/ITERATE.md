# 迭代到更高分 · Runbook

> 目标：以 `champion/genome_g*.toml` 为暖启起点，在**骏大祭本口径内**冲出比
> 当前冠军更高的分数，并通过门禁后登记进 `ANCHOR_MATSURI.md`。
> 本文件只写真实可执行的命令与判定，不写占位、不承诺未跑出的分数。

## 〇、开工前必须知道的两个事实

1. **口径**：一切在 `ANCHOR_MATSURI.md` 定义的可比组内比较。
   新分数必须报 `局面档@search_n` + `seed0` + `games` + σ，否则不登记。
2. **前置二进制**：`ga_trainer.py` 需要 `cardtest` release：
   ```bash
   cargo build --release -p matsuri-tools --bin cardtest
   ```
   它属于**上游剧本仓 + 配套引擎仓 `umaai-next`** 的配对编译（引擎仓
   `rust-toolchain.toml` 钉死 Rust 1.99.0）。本命名空间只搬运工具与数据，
   **不含、也不假装含有编译好的引擎**。
3. **先过隔离门禁**（改动本目录数据后必跑，防止另一套参数面混进来）：
   ```bash
   python3 matsuri/iterate/verify_isolation.py
   ```
   返回 0 才继续；它会校验数据文件零跨口径字段、genome 单表结构、
   台账口径标签齐全、`SOURCE.yaml` 的 18 项 SHA256 与实物一致。

## 一、暖启搜索（把冠军当起点继续 CMA-ES）

在**上游剧本仓根目录**执行（`tools/ga_trainer.py` 是上游脚本原样副本，
其相对路径假设 `data/matsuri_config.toml`、`decks/`、`target/release/` 都在仓根）：

```bash
# 把本命名空间的冠军 genome 放到上游仓能读到的位置
cp <本目录>/champion/genome_g0269_default.toml /tmp/g0269.toml

python3 tools/ga_trainer.py search \
  --out logs/ga/matsuri-warm-g0269 \
  --start /tmp/g0269.toml \
  --decks decks/speed_build.csv \
  --profile default \
  --seed-offset 20000000 \
  --lam 48 --sigma 0.05 \
  --max-minutes 100 --threads 8
```

关键参数含义（对齐 `ga_trainer.py` 的 argparse）：

| 参数 | 作用 | 为什么这么给 |
|---|---|---|
| `--start` | 暖启起点片段，叠加到 default 之上 | 从已定档冠军出发，比从零搜索收敛快 |
| `--sigma 0.05` | 起始步长（上游默认 0.1） | 已在最优点附近，用更小步长做局部精修 |
| `--seed-offset 20000000` | 三段种子整体平移 | **不同轮次绝不复用种子**，避免过拟合旧种子块 |
| `--decks` | 夹具首行=被调卡组，`*_shadow`=影子 | 门禁要求影子卡组同向 |
| `--max-minutes` | 限时，支持 `--resume` 断点续跑 | 长任务可分段 |

一键版本见 `warmstart.sh`（它把上面的参数固化，别直接复制粘贴）。

## 二、验收（看结果前把规则定死）

```bash
python3 tools/ga_trainer.py confirm --out logs/ga/matsuri-warm-g0269 --start /tmp/g0269.toml --games 2500
python3 tools/search_check.py   # 搜索档 N=8192 配对验收
```

**门禁**（照抄上游 `deck_param_scan.md` §10.1，跑之前固定，不许事后放宽）：

- 只认**复核分最高**的那一个候选；
- 验收块上对「现值」和对「起点」都 `z > 2.58`；
- 友人出行走满率 ≥ `max(现值, 起点) − 0.002`（硬需求，扣罚系数 100000）；
- 影子卡组对现值、对起点的 Δ **均为正**；
- 搜索档 `search_check.py`：`t ≥ 1.96` 落库；`0<t<1.96` 补局一次后以全部对数定；`t ≤ 0` 不落。

用 `gate.py` 做机械判定（避免人眼看数字放松标准）：

```bash
python3 iterate/gate.py --candidate 88300 --current 87557.1 --start 83793.9 \
                        --se 260 --n 39 --shadow-delta 120 \
                        --friend-full 0.9990 --current-friend-full 0.9988 \
                        --start-friend-full 0.9980 --search-t 3.2
```

> 后三个走满率/搜索档参数是**可选项**：不提供时对应项判 `SKIP`，
> 结论会是「条件通过，不得登记」；只有全部补齐且 5/5 全 PASS 才返回 0。
> 完整参数模板见 `warmstart.sh` 末行。

## 三、判定「更高分」的正确说法

| 想说的 | 该怎么写 |
|---|---|
| ✅ | 「`a-normal@8192` 组，暖启后均分 X，对现值 87557.1 的配对 Δ=+Y，t=Z>2.58，影子同向」 |
| ❌ | 「刷到 92000，超过实验室最高分 79402」——跨口径，错 |
| ❌ | 「比 91535.7 高」——那是 b-ideal 理想 buff 档，不同可比组 |
| ❌ | 只报一个裸分数，不给 seed/games/σ |

**必须超过的对手是同可比组内的现值**：
`a-normal@8192` → 87557.1；或参数冠军的配对增益 g0269 +898。

## 四、收账与合流

1. 通过门禁后，把结果写进 `ANCHOR_MATSURI.md` §一/§三，
   同时在 `champion/scoreboard.csv` 追加一行（`metric_type=paired_delta` 或 `absolute`，
   带 `comparable_group`）；
2. 新冠军 genome 另存 `champion/genome_<新名>.toml`，**不覆盖旧的三份**（本仓
   `AGENTS.md`：好种子不删、杈上迭代不 force-push）；
3. 在 `playbook/notes/` 或本目录写一条战报，注明起点、种子偏移、门禁数值；
4. PR 回 `main`，**用户点头才合并**。新锚线数值同步进 `ANCHOR_MATSURI.md`。

## 五、本轮交付的诚实边界

本轮完成的是：**数据搬迁 + 口径隔离 + 最高分结构化蒸馏 + 可加载冠军 genome +
真实可跑的迭代命令与门禁脚本**。

本轮**没有**实跑 CMA-ES，因此**没有产生任何新分数**，也不宣称超过上游。
原因：配对引擎（`umaai-next` @ 配套 commit + Rust 1.99.0 + `cardtest` release）
不在本仓内，且上游 GA 单轮为百万局量级、限时 100 分钟。
待引擎就绪后，按 §一 → §四 即可复现并真正冲分。
