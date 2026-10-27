# Athena ads ops scripts

Read-mostly Python (stdlib only) for judging Meta ads against real Shopify orders. Outputs go to `.context/` (gitignored).

Credentials, all from the repo-root `.env` (Conductor copies it into every workspace):

- Meta: `ATHENA_META_ACCESS_TOKEN` (system user "Conrad CLI", ads_read + ads_management, non-expiring) and `ATHENA_META_AD_ACCOUNT_ID=act_1648079109440158`.
- Shopify: `MYSHOPIFY_DOMAIN`, `SHOPIFY_CLIENT_ID`, `SHOPIFY_CLIENT_SECRET`. `shop.py` mints a 24h Admin token with the client-credentials grant, so no `make auth` login is needed. It falls back to the `.home/` shopify-admin session if those are missing.

| Script | What it does |
|---|---|
| `g.py GET\|POST <path> [k=v ...]` | Raw Graph v21 call. Use it to verify `effective_status`; the meta-ads CLI `audit`/`urlcheck` see 0 ads on Athena. |
| `ad_report.py [SINCE] [UNTIL] [--campaign ID]` | Per-ad keep/kill table: Meta 7d-click funnel joined to Shopify orders by `utm_content`. Writes `.context/meta-dive/ad-report-<UNTIL>.md`. |
| `ab_pack_report.py [SINCE] [--users A,B]` | PDP default-pack A/B readout (cell from `_ab_pack_default`). Users per cell come from GA4 events `ab_pack_default_a/_b`. |
| `pull_orders.py [SINCE]` | Shopify orders with customer journey and UTMs, to `.context/data/orders.json`. |
| `first20_scope.py show\|apply\|rollback` | FIRST20 discount scope. Writes to Shopify; `show` is safe. |

Tag every new ad with url_tags `utm_source=facebook&utm_medium=paid&utm_campaign={{campaign.id}}&utm_content={{ad.id}}`, or its orders won't map.

The `meta-ads` CLI (creates, budgets, pacing) is not in this repo. Build it from `~/workspace/cyclone/meta-ads` with `go build ./cmd/meta-ads`, then export `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`, `META_PAGE_ID=530366183488020` and `META_PIXEL_ID=1344187570344321` from the values above.
