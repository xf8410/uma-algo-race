# AGENTS.md — uma-algo-race 树杈纪律（硬约束，AI 与人类同守）

## 为什么有这个仓
uma-algo-lab 主干被 .venv 污染过（2816 文件）+ AI 直推 main 越过用户审查。
本仓重来，规矩先立。

## 树杈分支纪律（用户工作流实证：nn-lab 49 杈 / umaai-rs 41 杈 / teacher-lab 15 杈）

1. **main 只收账**：合并后的成果（已收账算法、锚点更新、结论文档）才能进 main。
   任何实验/新算法/半成品**禁止直推 main**。
2. **每根树杈一个主题**：`workbench/opt-<算法>`（新优化器）、`workbench/race-<主题>`
   （赛马/收账）、`workbench/seed-<名>`（策略变体种子）。
3. **好种子不筛选掉**：输了/不显著的分支**不删**——exp-006 系列留了 a~l 12 根杈，
   wisdom/power 方向输了也留着，后续可回来捡。只有用户明说才删。
4. **杈上迭代**：同主题第二版开新杈（`-v2` 后缀），不覆盖旧杈，不 force-push。
5. **收账合流**：跑出显著结论（或明确负结果）后，笔记+代码一起 PR 回 main，
   用户点头才合并。

## 卫生纪律
- `.venv/`、`__pycache__/`、`results/` 永不进库（.gitignore 已锁）
- commit 前 `git status` 逐文件过目，禁止无脑 `git add -A`
- 一次 commit 一个主题，说明里带数据

## 历史锚点（BASELINE.md 是唯一权威，比大小先对口径）
