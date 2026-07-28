# Athena tooling

Athena is a second Shopify brand that runs **Cyclone's CLI tools** against its
**own credentials**. This repo holds no CLI source code — only thin wrappers,
config, and a credential checklist. The tools are built from the Cyclone clone
on demand.

## How it works

- **Source of truth**: `$CYCLONE_DIR/tools/*` (default `/Users/conrad/workspace/cyclone/cyclone`). Nothing is forked.
- **Build on use**: each wrapper in `bin/` rebuilds its tool only when the Cyclone source is newer than the last build (fast no-op otherwise), into `bin/.build/`. The Cyclone worktree is never modified.
- **Auto-updates**: `bin/refresh` does a throttled (daily) `git pull` of the Cyclone clone before building, so upstream CLI changes flow in. Toggle with `ATHENA_AUTO_PULL` in `.env`; force with `bin/refresh --force`.
- **Credential isolation**: wrappers load Athena's `.env` and run the binary under an isolated `HOME` (`.home/`) so the Shopify OAuth token cache is Athena-only and never collides with Cyclone's. (macOS Go ignores `XDG_CONFIG_HOME`, so `HOME` is the lever.)

## Wrapped tools

| Command | Upstream | Status |
|---|---|---|
| `shopify-admin` | `tools/shopify-admin` (Go) | ✅ env-driven, reusable |
| `gmail-admin` | `tools/gmail-admin` (Go) | ✅ env-driven, reusable |
| `shopify-theme` | official Shopify CLI | ✅ pulls/runs the Athena theme (independent of Cyclone) |
| `refresh` | — | pulls the Cyclone source |

Deferred (Cyclone content baked in — see `docs/CREDENTIALS.md`): `generate_faqs.py`, `wayback-submit.sh`. Skipped: `walmart-admin`.

## First-time setup

1. `cp .env.example .env` and fill it in — see **`docs/CREDENTIALS.md`** for every value.
2. Save Athena's GCP service-account key as `./gcs-service.json`.
3. Load the environment:
   - direnv: `direnv allow`
   - otherwise: `source scripts/env.sh`
4. Verify the toolchain: `go version` (Go 1.26+) must be on PATH.
5. For the SEO/GA/image MCP servers, start Claude Code from this workspace (with the env loaded) and approve the project MCP servers via `/mcp`. Account-scoped servers (DataForSEO, nanobanana, lighthouse) are inherited from the global config.

## Verification (after credentials are filled)

1. **Build on use** — `shopify-admin --version` builds into `bin/.build/` and runs. Re-run → no rebuild. `touch $CYCLONE_DIR/tools/shopify-admin/main.go` → next run rebuilds.
2. **Athena data, not Cyclone** — `shopify-admin products list` returns Athena store products.
3. **Token isolation** — after `shopify-admin auth`, confirm `~/Library/Application Support/shopify-admin/token.json` (Cyclone's) is unchanged; Athena's token is under `.home/`.
4. **Gmail impersonation** — `gmail-admin --dry-run ...` shows the Athena mailbox, not `conrad@cyclonepods.com`.
5. **GA4** — `mcp__ga4__run_report` with `ATHENA_GA4_PROPERTY` returns Athena data.
6. **SEO** — a DataForSEO query for the Athena domain succeeds on the reused account.
7. **Image gen** — a nanobanana generate call produces an image with the reused `GOOGLE_AI_API_KEY`.

## Layout

```
bin/            wrappers (shopify-admin, gmail-admin, shopify-theme, refresh) + _common.sh
theme/          Athena Shopify theme code (pulled via shopify-theme; committed)
scripts/env.sh  PATH + env loader for non-direnv shells
.envrc          direnv equivalent
.env.example    credential schema (copy to .env)
.mcp.json       Athena-scoped MCP servers (GSC, GA4)
docs/CREDENTIALS.md   the credential checklist
docs/SETUP-PLAN.md    ordered rollout plan
```
