# Athena setup plan — get the tools + theme running

Ordered by dependency. **Owner** column: 🧑 = you (external accounts I can't create), 🤖 = I can do in-repo once prerequisites exist.

Scaffolding (wrappers, config, checklist) is already built and the build-on-use path is verified. What remains is (0) a reliable tool source, (1) provisioning Athena's credentials, (2) the Shopify theme workflow, (3) wiring the SEO/GA/image MCPs.

---

## Scope boundary — what is / isn't tied to Cyclone

Athena's **theme, store, and every credential are fully independent of Cyclone Pods.** The theme is pulled by logging the official Shopify CLI into the Athena store directly (Track 2) — zero Cyclone involvement.

The **only** Cyclone tie is that `shopify-admin` / `gmail-admin` compile from Cyclone's `tools/` source (your earlier "build from source, get updates from that repo" decision — shared code, not shared data). If you want even that severed later, say so and we vendor the tool source into Athena.

## Track 0 — Tool-source auto-update caveat 🧑 (optional)

`CYCLONE_DIR` points at `/Users/conrad/workspace/cyclone/cyclone`, your active dev clone (ahead 1 / behind 16, uncommitted work). `bin/refresh`'s `git pull --ff-only` **aborts** on a dirty/diverged tree, so auto-updates won't flow until that clone is manually updated. The wrappers still build fine from whatever source is on disk — only the *auto*-pull is affected.

To get true auto-update you'd point `CYCLONE_DIR` at a dedicated clean clone. You declined a second clone, so this stays best-effort: run `git -C "$CYCLONE_DIR" pull` yourself when you want the latest CLI code. No action required otherwise.

---

## Track 1 — Provision Athena credentials 🧑 (see `docs/CREDENTIALS.md` for the full table)

Do in this order (later steps depend on earlier ones):

1. **Shopify store** — confirmed live. Put its `*.myshopify.com` in `MYSHOPIFY_DOMAIN`.
2. **Shopify Admin API access** (for `shopify-admin`): create an OAuth app in the Partner dashboard on the Athena store → `SHOPIFY_CLIENT_ID` / `SHOPIFY_CLIENT_SECRET` → run `shopify-admin auth --client-id <id> --client-secret <secret>` (token caches under Athena's isolated `.home/`). *Or* a legacy custom-app `SHOPIFY_ACCESS_TOKEN`.
3. **Theme Access token** (for the official Shopify CLI theme work, Track 2): install the **Theme Access** app on the Athena store, generate a password → `SHOPIFY_CLI_THEME_TOKEN`. *(Optional — browser login also works; token is cleaner and keeps brands from crossing.)*
4. **GCP service account** → save key as `./gcs-service.json`. One SA serves GA4 + GSC + Gmail.
5. **GA4**: property id → `ATHENA_GA4_PROPERTY`; grant the SA **Viewer** on the property.
6. **Search Console**: verify `sc-domain:<athena-domain>`; set `ATHENA_DOMAIN`; grant the SA access.
7. **Gmail** (only if Athena does outreach): enable domain-wide delegation for the SA (scope `gmail.modify`); set `GMAIL_IMPERSONATE` to the Athena mailbox — **must not** be `conrad@cyclonepods.com`.
8. **Reuse account-scoped keys**: `OPENROUTER_API_KEY`, `GOOGLE_AI_API_KEY` (Gemini/image), DataForSEO (inherited from global MCP config).

→ `cp .env.example .env`, fill the above, drop `gcs-service.json` at repo root. Both are gitignored + auto-copied to new workspaces.

---

## Track 2 — Shopify theme code 🤖/🧑 (independent of Cyclone; needs the Athena store)

Theme lives in a **`theme/` subdir**. Official Shopify CLI 4.5.2 already installed. The `bin/shopify-theme` wrapper is **built** — it pins the Athena store + `theme/` path via env so you can never touch another brand's storefront.

Steps (once `MYSHOPIFY_DOMAIN` is in `.env`):
1. **Log in to the Athena store** — interactive, run once:
   `shopify-theme dev` → opens a browser to authenticate against `$MYSHOPIFY_DOMAIN`.
   *(Or non-interactive: set `SHOPIFY_CLI_THEME_TOKEN` from a Theme Access app.)*
   🧑 — browser OAuth can't be done in a headless agent session; you run this.
2. **Pull the live theme**: `shopify-theme pull` → downloads into `theme/`.
3. **Run locally**: `shopify-theme dev` → hot-reload preview at `http://127.0.0.1:9292` on the live store's data.
4. **Repo hygiene** (done): `theme/` is committed (not secret); `.shopify/`, `theme/.shopify/`, `theme/node_modules/` are gitignored; `SHOPIFY_CLI_THEME_TOKEN` is in `.env.example`.

**Safety**: `theme dev` is a local preview. Do **not** `shopify-theme push --allow-live` until intended — it clobbers theme-editor edits made in the Shopify admin.

### Two Shopify accounts on one machine (Cyclone + Athena)

Shopify CLI has **no built-in account switching** — one global session per `HOME` (token in `~/Library/Preferences/shopify-cli-kit-nodejs/config.json`). Choose one:

- **Theme Access tokens** — per-store `shptka_` password in each repo's `.env` (`SHOPIFY_CLI_THEME_TOKEN`). No login, no collision, works headless. Theme commands only.
- **HOME-isolated sessions** (wired here) — `shopify-theme` runs under `.home/`, so its login is a distinct account from Cyclone's plain `shopify` (real HOME). Log into each once; pick the account by which command you run. Full CLI, not just theme.

For Cyclone, keep using its own repo's `shopify` (real HOME). For Athena, always use `shopify-theme` (isolated HOME). They never cross.

---

## Track 3 — Wire SEO / GA / image MCPs 🧑 (needs Track 1 steps 4–8)

1. Load env: `direnv allow` (or `source scripts/env.sh`).
2. Start Claude Code from this workspace, `/mcp` → approve the project servers (`gsc`, `ga4`). Account-scoped servers (DataForSEO, nanobanana image gen, lighthouse) inherit from global config.
3. Confirm `${ATHENA_DIR}` / `${ATHENA_DOMAIN}` expand in `.mcp.json` (env must be loaded when Claude Code starts).

---

## Verification (run after each track)

| Check | Command / action | Proves |
|---|---|---|
| Tool source | `bin/refresh --force` | clean ff, auto-update works |
| Build on use | `shopify-admin --version` | builds + runs (already ✅) |
| Athena Shopify data | `shopify-admin products list` | returns **Athena** products, not Cyclone |
| Token isolation | after `shopify-admin auth`, Cyclone's `~/Library/Application Support/shopify-admin/token.json` unchanged | per-brand `HOME` works |
| Theme pull | `theme/` populates with liquid/sections/etc. | store + theme auth OK |
| Theme dev | local preview loads | end-to-end theme workflow |
| Gmail | `gmail-admin --dry-run ...` shows Athena mailbox | impersonation override |
| GA4 / GSC | `mcp__ga4__run_report` w/ Athena property; GSC query on Athena domain | brand-scoped analytics |
| SEO / image | DataForSEO query on Athena domain; nanobanana generate | account-scoped reuse |

---

## What I can execute now (no external accounts needed)

- **Track 0**: dedicated clean clone + repoint `CYCLONE_DIR`.
- **Track 2 step 3**: build the `bin/shopify-theme` wrapper + `.env.example`/gitignore updates.

Everything else waits on you provisioning the accounts in Track 1.
