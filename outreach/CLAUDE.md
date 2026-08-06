# Athena UraGuard — Outreach Tracker

Prospecting + outreach CRM for **Athena UraGuard**. Two motions: **awareness** (creators, communities, publications, podcasts) and **B2B supply** (care facilities, clinics, associations, distributors). Modeled on the Cyclone Pods outreach system.

## Product truth (what we're pitching)

| Product | What it is | Key points |
|---|---|---|
| **UraGuard™ Liner** (hero — `/products/athena-uraguard-liner`) | A thin **barrier liner worn *inside*** any adult incontinence product (brief/diaper/underwear) | Patent-pending **antibacterial layer**; lab-tested to reduce bacterial concentration **by up to 96%**; keeps skin drier. Positioned as **proactive UTI-risk reduction** for people managing leaks. NOT a pad, NOT the incontinence garment itself. |
| **Athena incontinence underwear** | Pull-on protective underwear with UraGuard™ tech | Tailored fits, breathable, dignity + comfort |
| **Athena adult diapers/briefs** | Protective briefs with UraGuard™ tech | Antibacterial protection built in |

Audience: **women managing incontinence + their caregivers**, skewing **older adults / post-menopausal**. Adjacent: UTI-prone, post-partum, diabetes, menopause, catheter users. Store: free US shipping $55+, 30-day US returns, 4★ (86 reviews). Medical content author: **Jacqueline Krieger, MD**.

Competitors: Poise / TENA / Attn:Grace / Because (incontinence); Uqora / LiveUTIFree / Utiva (UTI prevention). UraGuard's wedge = the **antibacterial barrier-liner** category (nobody else pairs incontinence protection with UTI-bacterial defense).

## Files

| File | Purpose |
|------|---------|
| `prospects.csv` | Master prospect DB (one row per prospect) |
| `touchpoints.csv` | Interaction history (one row per send/response) |
| `contacts.md` | Where each contact/email was found (provenance) |
| `templates/` | Outreach templates by motion + touchpoint |
| `drafts/` | Personalized, ready-to-send drafts for top prospects |
| `suppression.csv` | Do-not-contact list |
| `logs/outreach-changelog.md` | Append-only activity log |
| `reports/` | Discovery notes + weekly pipeline snapshots |

## CSV Schema: prospects.csv

`id, name, segment, platform, url, handle, audience_size, location, contact_name, role, contact_email, contact_method, outreach_type, pitch_angle, stage, priority, source, source_detail, notes, created_at, last_updated`

- **id** — unique slug (e.g., `menopause-nutritionist-jane-ig`)
- **segment** — `creator-blog | creator-youtube | creator-instagram | creator-tiktok | community-facebook | community-reddit | community-forum | publication-health | podcast | b2b-nursinghome | b2b-assistedliving | b2b-memorycare | b2b-hospice | b2b-homehealth | b2b-hospital | b2b-clinic | b2b-association | b2b-dme | b2b-seniorcenter | b2b-caremanager`
- **platform** — `website | youtube | instagram | tiktok | facebook | reddit | podcast | linkedin`
- **audience_size** — followers/subs, or facility bed-count / publication DA (leave blank if unknown)
- **contact_method** — `email | dm | contact-form | linkedin`
- **outreach_type** — `awareness` or `b2b`
- **stage** — `prospecting → contacted → responded → negotiating → placed/partner → rejected` (forward-only)
- **priority** — `P0` warm (existing mention/perfect fit) · `P1` high-fit + reachable · `P2` mid · `P3` cold
- **source** — `websearch-serp | youtube-search | ig-hashtag | tiktok-search | fb-group-search | reddit | directory | competitor-mention | manual`
- **source_detail** — the exact query / directory / page used to find it
- Dates always `YYYY-MM-DD`. Any comma inside a field → wrap the field in double quotes.

## CSV Schema: touchpoints.csv

`prospect_id, touchpoint_type, channel, outreach_type, sent_at, template_used, subject_line, response_status, response_date, placement_url, notes`

- **touchpoint_type** — `initial | followup-1 | followup-2 | response-received | placement-confirmed`
- **channel** — `email | dm | form`
- **response_status** — `pending | replied-positive | replied-negative | no-response | bounced`

## Template variables

`{{contact_name}}`, `{{personalized_opener}}` (1-2 sentences on their real work — written fresh per prospect, never reused), `{{relevance_hook}}` (why UraGuard fits their audience), `{{ask}}` (the specific request), `{{new_hook}}` (follow-up reason). A missing `{{var}}` in subject or body is a hard abort at send time.

## Claim guardrails (FTC / FDA) — READ BEFORE WRITING ANY COPY (outreach OR website)

**2026-08-05 — claims reset.** FDA consultant (via Dr. Kurth): do **NOT** use the 96% bacterial-reduction stat — it triggers a **medical-device designation**. Broader rule: any antibacterial-efficacy or UTI/infection claim makes UraGuard a regulated device. Removing the number isn't enough — the whole antibacterial/UTI wedge is out until a regulatory path is chosen. **Master doc: `positioning-compliant-2026-08-05.md`.**

**BANLIST — never (stated OR implied, brand OR curated):**
- "antibacterial / antimicrobial" as a benefit; "reduces bacteria / bacterial concentration"; the **96%** or the lab study in consumer copy
- "reduces / prevents UTIs", "UTI protection", "urinary health", "recurrent UTIs", "reduces infection risk"
- structure/function dodges ("supports urinary health"); implied claims (UTI stats beside the product, "Worried about UTIs?" framing, reviews curated for infection mentions); any MD/expert asserting an efficacy outcome

**ALLOWLIST — safe (high confidence):** dryness / stays-dry / extra-dry layer; the thin liner worn **inside** any brief for overnight + leak security (form-factor/performance); thin / discreet / breathable / tailored fits; **dignity, comfort, confidence**; **physician-founded** (trust, not efficacy).

**CONSULTANT-GATED — HOLD:** odor/freshness claims (need EPA treated-article + biocide check); handing the AATCC-100 study to B2B/clinical buyers (may set FDA "intended use").

- Never market to minors (N/A — adults/caregivers).

## Workflow

### Discovery
WebSearch (US) + WebFetch (contact/about pages) + chrome-devtools browser (IG/TikTok/YouTube/FB). Capture the decision-maker where findable (editor/creator handle; DON/administrator/clinic manager). Record provenance in `contacts.md`. Dedup on `url` + `contact_email`.

### Sending — via the `gmail-admin` CLI (auth already works)
Tool: `/Users/conrad/workspace/cyclone/cyclone/tools/gmail-admin/gmail-admin` (Gmail API, service account + domain-wide delegation — no browser/login). Env:
```
export GMAIL_SA_KEY=/Users/conrad/workspace/cyclone/athena/gcs-service.json
export GMAIL_IMPERSONATE=conrad@athenauraguard.com   # verified sender; `gmail-admin auth check` passes
DIR=/Users/conrad/conductor/workspaces/athena/managua/outreach
```
- **Draft-first (default):** `gmail-admin drafts create --to <email> --subject <s> --body-file <f>` stages a Gmail draft in the Athena mailbox to review + send by hand. Raw primitive — does **not** write `touchpoints.csv`/`stage`/labels. `--dry-run` prints the MIME first.
- **Tracked send:** `gmail-admin outreach send --template <name> --prospect-id <id> --dir "$DIR"` renders + sends + advances `stage`→`contacted`, appends a `touchpoints.csv` row, applies the `Outreach/Sent` label, enforces `suppression.csv`. Requires the `templates/` files reformatted into YAML front-matter (`---` / `subject:` / `touchpoint:` / `{{var}}`), which the current `**Subject:**` format is not yet in.
- Only `contact_method == email` prospects go through the CLI; DM/contact-form stay manual. Max ~5 initial emails/session; wait 5-7 days before a follow-up; max 2 follow-ups. Daily inbox ops: `outreach scan-replies --since 2d --update-csv`, `scan-bounces`, `followups`, `report`.

### Gmail labels (mirror `stage`)
`Outreach/Sent`, `Outreach/Follow-up`, `Outreach/Replied`, `Outreach/Negotiating`, `Outreach/Placed`, `Outreach/Dead`.

## Conventions
- Stage transitions forward-only. Second product pitch to a placed prospect → new `id`.
- Personalize every opener; never reuse. Log every batch send + response in `logs/outreach-changelog.md`.
- Weekly pipeline summary → `reports/pipeline-summary-YYYY-MM-DD.md`.
