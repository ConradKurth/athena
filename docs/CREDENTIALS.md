# Athena credentials checklist

Athena is a second Shopify brand running Cyclone's tooling against its **own**
data. The rule that decides everything:

- **Account-scoped** credentials (one key queries any domain) → **reuse Cyclone's**.
- **Brand-scoped** credentials (tied to a specific store/domain/property) → **create new for Athena**.

Fill the created values into `.env` (from `.env.example`) and drop Athena's
service-account key at repo root as `gcs-service.json`. Both are gitignored and
auto-copied into new Conductor workspaces via `.conductor/settings.local.toml`.

---

## A. CREATE new for Athena (brand-scoped)

| # | Credential | Where to get it | Goes in | Consumed by |
|---|---|---|---|---|
| 1 | **Shopify store** (`MYSHOPIFY_DOMAIN`) | The Athena Shopify store's `*.myshopify.com` domain | `.env` | `shopify-admin` |
| 2 | **Shopify OAuth app** (`SHOPIFY_CLIENT_ID`, `SHOPIFY_CLIENT_SECRET`) | Shopify Partner dashboard → create app on the Athena store → then run `shopify-admin auth --client-id <id> --client-secret <secret>` | `.env` | `shopify-admin` |
| 3 | **GCP service account** → `gcs-service.json` | GCP console (Athena project, or a new SA in an existing project). Create key, download JSON, save as `./gcs-service.json` | repo root | `gmail-admin`, GA4 MCP, GSC MCP |
| 4 | **GA4 property** (`ATHENA_GA4_PROPERTY`) | GA4 admin → Athena property → property id (numeric). Grant the service account (row 3) **Viewer** on the property | `.env` | GA4 MCP (`mcp__ga4__*`) |
| 5 | **Search Console property** (`ATHENA_DOMAIN`) | GSC → add & verify `sc-domain:<athena-domain>`. Grant the service account (row 3) access | `.env` (`ATHENA_DOMAIN`) | GSC MCP (`mcp__gsc__*`) |
| 6 | **Gmail impersonation** (`GMAIL_IMPERSONATE`) | The Athena Workspace mailbox to send as. Enable domain-wide delegation for the SA (row 3) in the Workspace admin, scope `gmail.modify`. **Must differ from `conrad@cyclonepods.com`** — that's the upstream default | `.env` | `gmail-admin` |

## B. REUSE Cyclone's (account-scoped — same key works for Athena)

| # | Credential | Notes | Goes in | Consumed by |
|---|---|---|---|---|
| 7 | **OpenRouter** (`OPENROUTER_API_KEY`) | Same key as Cyclone; account-level | `.env` | `shopify-admin` SEO/LLM commands |
| 8 | **Gemini image key** (`GOOGLE_AI_API_KEY`) | Same Google AI Studio key Cyclone uses for nanobanana image gen | `.env` | `seo-image-gen` skill / nanobanana MCP |
| 9 | **DataForSEO** (`DATAFORSEO_USERNAME/PASSWORD`) | Reuse Cyclone's account creds; set in `.env`, referenced by `.mcp.json` via `${VAR}` | `.env` | DataForSEO MCP (`mcp__dataforseo__*`) |
| 10 | **Moz / Bing / Common Crawl** | Optional SEO backlink sources; account-scoped/free. Configure only if used | per skill | `seo-backlinks` skill |

---

## Capability wiring (SEO / image / GA)

- **Google Analytics** — GA4 MCP (`analytics-mcp` via `pipx run`, defined in `.mcp.json`). Auth = Athena `gcs-service.json`; property id passed per query (`ATHENA_GA4_PROPERTY`). Confirm the exact pipx package matches how Cyclone invokes it.
- **SEO data** — DataForSEO/OpenRouter (account-scoped, reused) + Athena-scoped GSC (`.mcp.json`). The SEO skills query whatever `GSC_SITE_URL` / GA4 property are wired here, so they resolve to Athena automatically.
- **Image generation** — `seo-image-gen` skill via nanobanana (Gemini). Reuses `GOOGLE_AI_API_KEY`. This is a skill/MCP, not a CLI; nothing per-brand beyond the key.

## Not wired (need Athena content, not just credentials)

- **`generate_faqs.py`** — Cyclone article list hardcoded in the script. Needs Athena's own article data before use.
- **`wayback-submit.sh`** — Cyclone URL paths hardcoded. Needs an Athena URL list.
- **`walmart-admin`** — intentionally skipped.

## After filling credentials — verify

Run the live checks in `README.md` → Verification. The key isolation proof:
`shopify-admin products list` must return **Athena** products, and authenticating
Athena must not touch Cyclone's `~/Library/Application Support/shopify-admin/token.json`.
