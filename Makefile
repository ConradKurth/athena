# Athena CLI — thin targets over bin/ so the tools work without direnv/PATH setup.
# Run `make` or `make help` for the list.
#
# Shopify sessions are isolated under .home/, so the Athena login is a SEPARATE
# account from Cyclone Pods. `make login` authenticates the Athena account only.

ATHENA_DIR := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
BIN        := $(ATHENA_DIR)/bin
HOME_DIR   := $(ATHENA_DIR)/.home
STORE      := $(shell grep -s '^MYSHOPIFY_DOMAIN=' $(ATHENA_DIR)/.env | cut -d= -f2)
ARGS ?=

.DEFAULT_GOAL := help
.PHONY: help login logout auth theme-list theme-pull theme-dev theme-push shopify gmail refresh

help: ## Show this help
	@echo "Athena CLI  (store: $(STORE))"
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

login: ## Log in the Athena Shopify account (browser; isolated session)
	@echo "Logging in to $(STORE) — pick the account with access to the Athena store."
	$(BIN)/shopify-theme list

logout: ## Log out the Athena Shopify session only (leaves Cyclone alone)
	HOME="$(HOME_DIR)" shopify auth logout

theme-list: ## List themes on the Athena store
	$(BIN)/shopify-theme list

theme-pull: ## Download the live theme into ./theme
	$(BIN)/shopify-theme pull

theme-dev: ## Local theme preview at http://127.0.0.1:9292
	$(BIN)/shopify-theme dev

theme-push: ## Push ./theme to a NEW unpublished theme (never touches live)
	$(BIN)/shopify-theme push --unpublished

auth: ## OAuth the shopify-admin CLI to the Athena store (browser, one-time)
	$(BIN)/shopify-admin auth

shopify: ## shopify-admin passthrough:  make shopify ARGS="products list"
	$(BIN)/shopify-admin $(ARGS)

gmail: ## gmail-admin passthrough:  make gmail ARGS="--dry-run inbox"
	$(BIN)/gmail-admin $(ARGS)

refresh: ## Pull latest Cyclone tool source, then rebuild on next run
	$(BIN)/refresh --force
