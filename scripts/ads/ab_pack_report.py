"""Readout for the PDP default-pack A/B test (cell a = 30-pack preselected, b = 60-pack).

Usage: python3 ab_pack_report.py [SINCE=2026-10-23]  (line-item tagging fix deployed 2026-10-23; earlier orders undercount cells)
Orders carry the cell as the hidden cart attribute `_ab_pack_default` (theme/snippets/ab-pack-default.liquid).
Users per cell come from GA4 events `ab_pack_default_a` / `_b` (totalUsers by eventName); pass them as
--users A,B to get profit per visitor, the metric that decides the test.
"""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pull_orders import pull

COST = {'30': 21.53, '60': 30.53, '90': 39.53}  # Shopify inventoryItem.unitCost, 2026-10-18
since = next((a for a in sys.argv[1:] if not a.startswith('--') and '-' in a and ',' not in a), '2026-10-23')
users = dict(zip('ab', map(int, sys.argv[sys.argv.index('--users') + 1].split(',')))) if '--users' in sys.argv else {}

cells = collections.defaultdict(lambda: {'orders': 0, 'rev': 0.0, 'profit': 0.0, 'mix': collections.Counter(), 'sub': 0})
for o in pull(since):
    if o['test'] or o['cancelledAt'] or (o['sourceName'] or '').startswith('subscription_contract'): continue
    cell = {a['key']: a['value'] for a in o.get('customAttributes') or []}.get('_ab_pack_default')
    # Buy-it-now orders carry the cell only as a line-item property (added 2026-10-23)
    cell = cell or next((a['value'] for li in o['lineItems']['nodes'] for a in li.get('customAttributes') or []
                         if a['key'] == '_ab_pack_default'), None)
    if cell not in ('a', 'b'): continue
    rev = float(o['currentTotalPriceSet']['shopMoney']['amount']); cogs = 0
    c = cells[cell]
    for li in o['lineItems']['nodes']:
        pack = (li.get('variantTitle') or '').split(' ')[0]
        cogs += COST.get(pack, 0) * li['quantity']; c['mix'][pack] += li['quantity']
        c['sub'] += bool(li.get('sellingPlan'))
    c['orders'] += 1; c['rev'] += rev; c['profit'] += rev - cogs - (rev * 0.029 + 0.30)

print(f'PDP default-pack test, orders since {since} (a = 30-pack default, b = 60-pack default)')
for k in 'ab':
    c = cells[k]; n = c['orders'] or 1
    line = (f"  {k}: {c['orders']} orders, revenue ${c['rev']:.0f}, AOV ${c['rev'] / n:.2f}, "
            f"profit ${c['profit']:.0f} (${c['profit'] / n:.2f}/order), packs {dict(c['mix'])}, subscriptions {c['sub']}")
    if k in users: line += f", users {users[k]}, conv {c['orders'] / users[k]:.2%}, profit/visitor ${c['profit'] / users[k]:.2f}"
    print(line)
if not users: print('  add --users A,B from GA4 (totalUsers for events ab_pack_default_a / ab_pack_default_b) for profit per visitor')
