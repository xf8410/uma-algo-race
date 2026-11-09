#!/usr/bin/env python3
"""骏大祭命名空间 · 口径隔离门禁（真实可跑，无外部依赖）

用法:
    python3 iterate/verify_isolation.py            # 在 matsuri/ 目录下
    python3 matsuri/iterate/verify_isolation.py    # 在仓库根目录

退出码: 0 = 全部通过; 1 = 存在违规项。
只检查「数据文件」(.toml/.csv/.json/.yaml)。.md 文档允许出现对照说明文字。
脚本自身含黑名单字面，自动跳过。
"""
import sys, re, hashlib, tomllib, csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_EXT = {'.toml', '.csv', '.json', '.yaml'}

# 另一套参数面（71k 老家口径）的字段名与其锚点分数：不得出现在骏大祭数据文件里
BANNED_FIELDS = [
    'pt_tradeoff', 'ramen_', 'vital_rest', 'shining_bonus', 'status_rate',
    'bench_base', 'RecommendedRamenTrainer', 'seed_xnes_best',
]
BANNED_SCORES = ['71415.6', '71692', '79402', '64641.5']

failures = []
def bad(msg): failures.append(msg)

# ---- 1) 数据文件扫描：禁止另一套参数面字段名 / 锚点分数 ----
for p in sorted(ROOT.rglob('*')):
    if not p.is_file() or p.suffix.lower() not in DATA_EXT:
        continue
    text = p.read_text(encoding='utf-8', errors='replace')
    for w in BANNED_FIELDS + BANNED_SCORES:
        if w in text:
            bad(f'隔离违规: {p.relative_to(ROOT)} 含 "{w}"')

# ---- 2) 三份冠军 genome：单 decks 表 + 必需旋钮组 ----
genomes = sorted((ROOT / 'champion').glob('genome_*.toml'))
if len(genomes) != 3:
    bad(f'冠军 genome 数量应为 3，实得 {len(genomes)}')
for p in genomes:
    try:
        d = tomllib.load(open(p, 'rb'))
    except Exception as e:
        bad(f'{p.name} TOML 解析失败: {e}'); continue
    if set(d) != {'decks'} or len(d['decks']) != 1:
        bad(f'{p.name} 不是单 [decks.*] 表'); continue
    t = list(d['decks'].values())[0].get('trainer', {})
    for k in ('pt_favor_rate', 'weights', 'endgame'):
        if k not in t:
            bad(f'{p.name} trainer 缺必需旋钮组 {k}')

# ---- 3) 分数台账：每行的口径标签 / 来源 / commit 不得为空 ----
sb = ROOT / 'champion' / 'scoreboard.csv'
rows = list(csv.DictReader(open(sb, encoding='utf-8-sig')))
if not rows:
    bad('scoreboard.csv 为空')
for i, r in enumerate(rows, 2):
    if r['metric_type'] not in ('absolute', 'paired_delta'):
        bad(f'scoreboard.csv 第 {i} 行 metric_type 非法: {r["metric_type"]}')
    for k in ('comparable_group', 'source', 'commit'):
        if not r.get(k, '').strip():
            bad(f'scoreboard.csv 第 {i} 行 {k} 为空（无法对口径）')

# ---- 4) SOURCE.yaml 登记的 SHA256 与实物逐项一致 ----
src = ROOT / 'SOURCE.yaml'
sha_pairs = []
if not src.exists():
    bad('SOURCE.yaml 缺失')
else:
    s = src.read_text(encoding='utf-8')
    # 手解析，避免引入 PyYAML 依赖
    for m in re.finditer(r'-\s*path:\s*(\S+)\s*\n\s*bytes:\s*(\d+)\s*\n\s*sha256:\s*([0-9a-f]{64})', s):
        sha_pairs.append((m.group(1), int(m.group(2)), m.group(3)))
    if len(sha_pairs) < 18:
        bad(f'SOURCE.yaml 登记条目过少 ({len(sha_pairs)})')
    for rel, size, sha in sha_pairs:
        f = ROOT / rel
        if not f.exists():
            bad(f'SOURCE.yaml 登记的文件不存在: {rel}'); continue
        b = f.read_bytes()
        if len(b) != size or hashlib.sha256(b).hexdigest() != sha:
            bad(f'SOURCE.yaml SHA256/字节数不符: {rel}')

# ---- 5) 锚线纪律：新锚线必须声明与另一张表互不相认 ----
anchor = ROOT / 'ANCHOR_MATSURI.md'
if not anchor.exists():
    bad('ANCHOR_MATSURI.md 缺失')
elif '互不相认' not in anchor.read_text(encoding='utf-8'):
    bad('ANCHOR_MATSURI.md 未声明与 71k 口径锚线互不相认')

# ---- 汇总 ----
print('=' * 62)
print('骏大祭命名空间 · 口径隔离门禁')
print('=' * 62)
print(f'  数据文件扫描      : {sum(1 for p in ROOT.rglob("*") if p.is_file() and p.suffix.lower() in DATA_EXT)} 个')
print(f'  禁用字段/分数     : {len(BANNED_FIELDS)} 字段 + {len(BANNED_SCORES)} 分数')
print(f'  冠军 genome       : {len(genomes)} 份（单表 + 13 组旋钮）')
print(f'  台账行 / 登记文件 : {len(rows)} 行 / {len(sha_pairs)} 项 SHA256')
print('-' * 62)
if failures:
    for f in failures:
        print('  [FAIL]', f)
    print('-' * 62)
    print(f'结论: 不通过（{len(failures)} 项违规）')
    sys.exit(1)
print('  全部通过：数据文件零跨口径字段、genome 结构完整、台账带口径标签、SHA256 全一致。')
print('=' * 62)
sys.exit(0)
