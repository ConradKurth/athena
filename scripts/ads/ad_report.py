"""Per-ad keep/kill report: Meta funnel (7d-click) joined to Shopify orders by utm_content.

Usage: python3 ad_report.py [SINCE] [UNTIL] [--campaign ID]   (dates YYYY-MM-DD, default last 7 days)
Writes .context/meta-dive/ad-report-<UNTIL>.md and prints it.

Ads map to orders through utm_content: either the ad id itself (url_tags with {{ad.id}}, the standard
for new ads) or a hand-written slug found in the ad's creative url_tags / link.
"""
import json, os, re, sys, datetime as dt, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from g import call, A, root
from pull_orders import pull

# Baselines: Category Launch, 60d to 2026-10-18, 7d-click: $464.89 spend, 22 ATC, 16 purchases.
COST_PER_ATC, CPA = 21.0, 29.0
# Gates. At ~3x the expected cost of one event, an average ad shows zero of them only ~5% of the time (Poisson).
KILL_NO_ATC = 3 * COST_PER_ATC      # ~$63 spent, 0 add-to-carts
KILL_NO_SALE = 3 * CPA              # ~$87 spent, 0 purchases (Meta) and 0 Shopify orders
TOO_EARLY = 2 * COST_PER_ATC        # under ~$42 nothing is readable
WIN_CPA, WIN_MIN_PURCH = 30.0, 3    # Directional tier: >=3 purchases at CPA <= $30
META_SOURCES = {'facebook', 'meta', 'fb', 'ig', 'instagram'}
EV = {'lpv': 'landing_page_view', 'atc': 'offsite_conversion.fb_pixel_add_to_cart',
      'ic': 'offsite_conversion.fb_pixel_initiate_checkout', 'pur': 'offsite_conversion.fb_pixel_purchase'}

args = [a for a in sys.argv[1:] if not a.startswith('--')]
camp = sys.argv[sys.argv.index('--campaign') + 1] if '--campaign' in sys.argv else None
if camp in args: args.remove(camp)
until = args[1] if len(args) > 1 else dt.date.today().isoformat()
since = args[0] if args else (dt.date.fromisoformat(until) - dt.timedelta(days=6)).isoformat()

def utm_content(s):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(s).query if '?' in s or '://' in s else s)
    return (q.get('utm_content') or [None])[0]

# 1. Map utm_content -> ad ids from every ad's creative.
ALL = ['ACTIVE','PAUSED','ARCHIVED','DELETED','CAMPAIGN_PAUSED','ADSET_PAUSED','DISAPPROVED','WITH_ISSUES','IN_PROCESS','PENDING_REVIEW']  # default edges hide archived/deleted ads, which still own past spend and orders
ads = call('GET', f'{A}/ads', paged=True, limit=200, effective_status=[x for x in ALL if x != 'DELETED'], fields='id,name,campaign_id,created_time,effective_status,'
           'creative{url_tags,object_story_spec,asset_feed_spec}')
if isinstance(ads, dict): raise SystemExit(json.dumps(ads)[:600])
slug2ads, ad_by_id = {}, {a['id']: a for a in ads}
for a in ads:
    c = a.get('creative') or {}
    links = [c.get('url_tags') or '', ((c.get('object_story_spec') or {}).get('link_data') or {}).get('link') or '']
    links += [l.get('website_url', '') for l in (c.get('asset_feed_spec') or {}).get('link_urls', [])]
    for l in links:
        v = utm_content(l)
        if v and '{{' not in v: slug2ads.setdefault(v, set()).add(a['id'])

def ads_for(content):
    if not content: return set()
    if content in ad_by_id or re.fullmatch(r'\d{15,}', content): return {content}  # {{ad.id}} tag
    return slug2ads.get(content, set())

# 2. Meta funnel per ad.
flt = [{'field': 'spend', 'operator': 'GREATER_THAN', 'value': 0}, {'field': 'ad.effective_status', 'operator': 'IN', 'value': ALL}]
if camp: flt.append({'field': 'campaign.id', 'operator': 'EQUAL', 'value': camp})
ins = call('GET', f'{A}/insights', paged=True, level='ad', limit=500, filtering=flt,
           time_range={'since': since, 'until': until}, action_attribution_windows=['7d_click'],
           fields='ad_id,ad_name,campaign_id,spend,impressions,inline_link_clicks,actions,action_values')
if isinstance(ins, dict): raise SystemExit(json.dumps(ins)[:600])
rows = {}
for r in ins:
    acts = {x['action_type']: float(x.get('7d_click', 0)) for x in r.get('actions', [])}
    vals = {x['action_type']: float(x.get('7d_click', 0)) for x in r.get('action_values', [])}
    rows[r['ad_id']] = {'name': r['ad_name'], 'spend': float(r['spend']), **{k: acts.get(v, 0) for k, v in EV.items()},
                        'pur_value': vals.get(EV['pur'], 0), 'sh_last': 0, 'sh_first': 0, 'sh_rev': 0.0, 'sh_new': 0, 'sh_sub': 0}

# 3. Shopify orders in the window, attributed by last-touch (and first-touch count).
orders = [o for o in pull(since) if not o['test'] and not o['cancelledAt'] and o['createdAt'][:10] <= until]
untagged, unmatched = [], []
for o in orders:
    j = o.get('customerJourneySummary') or {}
    touch = {}
    for k in ('firstVisit', 'lastVisit'):
        v = j.get(k) or {}; u = v.get('utmParameters') or {}
        if (u.get('source') or '').lower() in META_SOURCES: touch[k] = u.get('content')
        elif 'facebook' in (v.get('referrerUrl') or '') or 'instagram' in (v.get('referrerUrl') or ''): untagged.append(o['name'])
    for k, col in (('firstVisit', 'sh_first'), ('lastVisit', 'sh_last')):
        if k not in touch: continue
        ids = ads_for(touch[k])
        if not ids: unmatched.append(f"{o['name']}:{touch[k]}"); continue
        if camp: ids = {i for i in ids if i in rows or ad_by_id.get(i, {}).get('campaign_id') == camp}
        for i in ids:  # a slug reused by several ads credits each (flagged as shared below)
            r = rows.setdefault(i, {'name': ad_by_id.get(i, {}).get('name', i), 'spend': 0.0, **{x: 0 for x in EV},
                                    'pur_value': 0, 'sh_last': 0, 'sh_first': 0, 'sh_rev': 0.0, 'sh_new': 0, 'sh_sub': 0})
            r[col] += 1
            if col == 'sh_last':
                r['sh_rev'] += float(o['currentTotalPriceSet']['shopMoney']['amount'])
                first = ((o.get('customer') or {}).get('orders') or {}).get('nodes') or [{}]
                r['sh_new'] += first[0].get('name') == o['name']
                r['sh_sub'] += any(li.get('sellingPlan') for li in o['lineItems']['nodes'])

def verdict(r):
    s = r['spend']
    if not s: return 'no spend in window'
    if s < TOO_EARLY: return 'TOO EARLY'
    # Cart gates yield to real Shopify orders: the pixel misses Buy-it-now carts.
    if r['atc'] == 0 and r['sh_last'] == 0 and s >= KILL_NO_ATC: return 'KILL: no carts'
    if r['pur'] == 0 and r['sh_last'] == 0 and s >= KILL_NO_SALE: return 'KILL: no sales'
    if r['pur'] >= WIN_MIN_PURCH and s / r['pur'] <= WIN_CPA: return 'WINNING'
    if r['atc'] and r['sh_last'] == 0 and s / r['atc'] > 2 * COST_PER_ATC and s >= KILL_NO_ATC: return 'WEAK: carts 2x cost'
    if r['atc'] and s / r['atc'] <= COST_PER_ATC: return 'ON TRACK (carts)'
    return 'HOLD'

money = lambda x: f'${x:,.0f}' if x else '-'
per = lambda s, n: f'${s / n:,.0f}' if n else '-'
lines = [f'# Athena ad report {since} to {until}' + (f' (campaign {camp})' if camp else ''), '',
         f'Meta = 7d-click. Shopify = orders whose last visit carried this ad\'s utm_content. Baselines: ${COST_PER_ATC:.0f}/ATC, ${CPA:.0f}/purchase.',
         f'Gates: kill at ${KILL_NO_ATC:.0f} with 0 carts, or ${KILL_NO_SALE:.0f} with 0 sales; under ${TOO_EARLY:.0f} too early; winning = >={WIN_MIN_PURCH} purchases at <=${WIN_CPA:.0f}.', '',
         '| Ad | Spend | LPV | ATC | $/ATC | Purch | CPA | Shopify orders (last/first) | Shop rev | New | Sub | Verdict |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|']
shared = {i for v in slug2ads.values() if len(v) > 1 for i in v}
for i, r in sorted(rows.items(), key=lambda kv: -kv[1]['spend']):
    name = r['name'][:48] + (' *' if i in shared else '')
    lines.append(f"| {name} `{i}` | {money(r['spend'])} | {r['lpv']:.0f} | {r['atc']:.0f} | {per(r['spend'], r['atc'])} | {r['pur']:.0f} | "
                 f"{per(r['spend'], r['pur'])} | {r['sh_last']}/{r['sh_first']} | {money(r['sh_rev'])} | {r['sh_new']} | {r['sh_sub']} | {verdict(r)} |")
tot = {k: sum(r[k] for r in rows.values()) for k in ('spend', 'atc', 'pur', 'sh_last', 'sh_rev')}
lines += ['', f"Total: {money(tot['spend'])} spend, {tot['atc']:.0f} ATC, {tot['pur']:.0f} Meta purchases, "
          f"{tot['sh_last']} Shopify orders ({money(tot['sh_rev'])}).",
          f"Orders in window: {len(orders)}. Meta-referred but untagged: {len(set(untagged))} {sorted(set(untagged))}. "
          f"Tagged Meta but unmapped utm_content: {unmatched or 'none'}.",
          '`*` = utm_content slug shared by several ads; each gets the credit.']
md = '\n'.join(lines)
out = os.path.join(root, f'.context/meta-dive/ad-report-{until}.md'); os.makedirs(os.path.dirname(out), exist_ok=True); open(out, 'w').write(md + '\n')
print(md); print('\nwrote', out)
