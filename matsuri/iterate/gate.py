#!/usr/bin/env python3
"""骏大祭迭代门禁判定（机械执行，避免人眼放松标准）。

口径与阈值照抄上游 docs/plan/deck_param_scan.md §10.1：
  1. 复核分最高者才进门禁（外部保证，本脚本只判数值）
  2. 对现值、对起点都 z > 2.58
  3. 走满率 >= max(现值走满率, 起点走满率) - 0.002
  4. 影子卡组配对 Δ > 0
  5. 搜索档 search_check: t >= 1.96 落库; 0<t<1.96 补局; t<=0 不落

用法（分数与走满率分开给，不混算）：
  python3 gate.py --candidate 88300 --current 87557.1 --start 83793.9 \
      --se 260 --n 39 --shadow-delta 120 \
      --friend-full 0.9990 --current-friend-full 0.9988 --start-friend-full 0.9980 \
      --search-t 3.2

零依赖，只用标准库。退出码 0=通过 / 1=不通过 / 2=参数错误。
"""
from __future__ import annotations
import argparse
import sys

Z_GATE = 2.58
FRIEND_TOL = 0.002
T_GATE = 1.96


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--candidate', type=float, required=True, help='候选复核分')
    ap.add_argument('--current', type=float, required=True, help='现值（同可比组分数）')
    ap.add_argument('--start', type=float, required=True, help='暖启起点分数')
    ap.add_argument('--se', type=float, required=True, help='配对差的标准误')
    ap.add_argument('--n', type=int, required=True, help='配对对数')
    ap.add_argument('--shadow-delta', type=float, required=True,
                    help='影子卡组配对差（须 > 0）')
    ap.add_argument('--friend-full', type=float, required=True, help='候选友人走满率')
    ap.add_argument('--current-friend-full', type=float, default=None,
                    help='现值走满率（不给则该项 SKIP）')
    ap.add_argument('--start-friend-full', type=float, default=None,
                    help='起点走满率（不给则该项 SKIP）')
    ap.add_argument('--search-t', type=float, default=None,
                    help='搜索档配对 t（不给则该项 SKIP）')
    a = ap.parse_args()

    if a.se <= 0 or a.n < 2:
        print('[参数错误] --se 必须 > 0 且 --n >= 2', file=sys.stderr)
        return 2

    checks = []

    z_cur = (a.candidate - a.current) / a.se
    checks.append(('对现值 z > 2.58', z_cur > Z_GATE, f'z={z_cur:.3f}'))
    z_sta = (a.candidate - a.start) / a.se
    checks.append(('对起点 z > 2.58', z_sta > Z_GATE, f'z={z_sta:.3f}'))

    if a.current_friend_full is None or a.start_friend_full is None:
        checks.append(('走满率', None, 'SKIP: 需 --current-friend-full 与 --start-friend-full'))
    else:
        need = max(a.current_friend_full, a.start_friend_full) - FRIEND_TOL
        checks.append(('走满率', a.friend_full >= need,
                       f'{a.friend_full:.4f} vs 下限 {need:.4f}'))

    checks.append(('影子卡组 Δ > 0', a.shadow_delta > 0, f'Δ={a.shadow_delta:+.1f}'))

    if a.search_t is None:
        checks.append(('搜索档 t >= 1.96', None, 'SKIP: 需 --search-t'))
    else:
        label = '落库' if a.search_t >= T_GATE else ('补局一次' if a.search_t > 0 else '不落')
        checks.append(('搜索档 t >= 1.96', a.search_t >= T_GATE,
                       f't={a.search_t:.2f} → {label}'))

    print('=' * 60)
    print('骏大祭迭代门禁判定（阈值固定，不可事后放宽）')
    print('=' * 60)
    for name, ok, detail in checks:
        mark = 'PASS' if ok is True else ('FAIL' if ok is False else 'SKIP')
        print(f'  [{mark:4}] {name:<20} {detail}')
    print('-' * 60)

    failed = [n for n, ok, _ in checks if ok is False]
    skipped = [n for n, ok, _ in checks if ok is None]
    if failed:
        print(f'结论: 不通过（{len(failed)} 项 FAIL: {", ".join(failed)}）')
        return 1
    if skipped:
        print(f'结论: 条件通过，但 {len(skipped)} 项 SKIP（{", ".join(skipped)}）——'
              f'补齐实测值前不得登记进锚线表。')
        return 1
    print(f'结论: 通过（{len(checks)}/{len(checks)} 项）。可登记进 ANCHOR_MATSURI.md。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
