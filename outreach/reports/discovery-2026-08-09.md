# Discovery report — 2026-08-09 (Round-2 awareness expansion)

**Total net-new added:** 248
**With a direct email:** 75 / 248
**Wedge tag (in notes):** compliant=233 · uti=15
**By priority:** P0=44 · P1=83 · P2=102 · P3=19

## By segment

- creator-instagram: 59
- creator-blog: 48
- podcast: 27
- community-facebook: 25
- creator-youtube: 25
- publication-health: 20
- community-forum: 18
- community-reddit: 16
- creator-tiktok: 10

## Method

11-agent web-discovery fan-out (feature-dev:code-explorer, WebSearch+WebFetch), one per segment/niche.
Appended via tools/append_prospects.py (dedup on normalized url/handle/name vs existing + within-batch).
Raw: raw/round2-2026-08-09.json. Per-agent JSON: .context/round2/*.json.
Anti-hallucination: 14/14 sampled URLs resolved (HTTP 200).
