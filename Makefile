# In some parts this is hardcoded
# see pyproject.toml for the available script names
# see src/insights_mcp/server.py for accepted environment variables
VALID_CONTAINER_BRANDS := insights red-hat-lightspeed
CONTAINER_BRAND ?= insights

ifeq ($(filter $(CONTAINER_BRAND),$(VALID_CONTAINER_BRANDS)),)
  $(error invalid CONTAINER_BRAND: $(CONTAINER_BRAND). \
Valid options are: $(VALID_CONTAINER_BRANDS))
endif

IMAGE_NAME := $(CONTAINER_BRAND)-mcp

ifeq ($(CONTAINER_BRAND),insights)
  CONTAINER_BRAND_TITLE_CASE := Red Hat Insights
  CONTAINER_BRAND_UPPERCASE := INSIGHTS
else ifeq ($(CONTAINER_BRAND),red-hat-lightspeed)
  CONTAINER_BRAND_TITLE_CASE := Red Hat Lightspeed
  CONTAINER_BRAND_UPPERCASE := LIGHTSPEED
else
	$(error invalid CONTAINER_BRAND for image name: $(CONTAINER_BRAND))
endif
SCRIPT_NAME ?= $(IMAGE_NAME)

.PHONY: build
build: generate-docs ## Build the container image
	podman build \
	  --build-arg INSIGHTS_MCP_VERSION=$(VERSION) \
	  --build-arg CONTAINER_BRAND=$(CONTAINER_BRAND) \
	  --tag $(IMAGE_NAME) .

.PHONY: build-prod
build-prod: generate-docs ## Build the container image but with the upstream tag
	podman build \
	  --build-arg INSIGHTS_MCP_VERSION=$(VERSION) \
	  --build-arg CONTAINER_BRAND=$(CONTAINER_BRAND) \
	  --tag ghcr.io/redhatinsights/$(IMAGE_NAME) .

# please set from outside
CONTAINER_IMAGE ?= ghcr.io/redhatinsights/$(IMAGE_NAME):latest
TAG ?= v0.0.0-dev
VERSION ?= $(TAG)

.PHONY: build-claude-extension
build-claude-extension: ## Build the Claude extension
	sed \
	  -e "s/{{VERSION}}/$(TAG)/g" \
	  -e "s/{{IMAGE_NAME}}/$(IMAGE_NAME)/g" \
	  -e "s|{{CONTAINER_IMAGE}}|$(CONTAINER_IMAGE)|g" \
	  -e "s|{{CONTAINER_BRAND_TITLE_CASE}}|$(CONTAINER_BRAND_TITLE_CASE)|g" \
	  -e "s|{{CONTAINER_BRAND}}|$(CONTAINER_BRAND)|g" \
	  -e "s|{{CONTAINER_BRAND_UPPERCASE}}|$(CONTAINER_BRAND_UPPERCASE)|g" \
	  claude_desktop/manifest.json.template > claude_desktop/manifest.json
	zip -j $(IMAGE_NAME)-$(TAG).dxt claude_desktop/manifest.json claude_desktop/icon.png
	rm claude_desktop/manifest.json

build-claude-extension-dev: build ## Build Claude extension for local development
	$(MAKE) build-claude-extension TAG=local-dev CONTAINER_BRAND=$(CONTAINER_BRAND) CONTAINER_IMAGE=localhost/$(IMAGE_NAME):latest

.PHONY: lint
lint: generate-docs ## Run linting with pre-commit
	uv run pre-commit run --all-files --hook-stage manual

.PHONY: test
test: ## Run tests with pytest (hides logging output)
	@echo "Running pytest tests..."
	env DEEPEVAL_TELEMETRY_OPT_OUT=YES uv run pytest -v

.PHONY: test-verbose
test-verbose: ## Run tests with pytest with verbose output (shows logging output)
	@echo "Running pytest tests with verbose output..."
	env DEEPEVAL_TELEMETRY_OPT_OUT=YES uv run pytest -vv -o log_cli=true

.PHONY: test-very-verbose
test-very-verbose: ## Run tests with pytest showing all intermediate agent steps (shows logging output)
	@echo "Running pytest tests with debug output..."
	env DEEPEVAL_TELEMETRY_OPT_OUT=YES uv run pytest -vvv -o log_cli=true

.PHONY: test-coverage
test-coverage: ## Run tests with coverage reporting
	@echo "Running pytest tests with coverage..."
	env DEEPEVAL_TELEMETRY_OPT_OUT=YES uv run pytest -v --cov=. --cov-report=html --cov-report=term-missing

# Define a reusable check function for container sanity tests
# $(1) = image URL, $(2) = expected CONTAINER_BRAND value
define check_container
	@echo -e "\n----- Checking $(1)"
	podman run --rm -ti \
	  --entrypoint /bin/bash \
	  --pull always \
	  $(1) -c "env; (echo 'Checking container brand…' ; env | grep 'CONTAINER_BRAND=$(2)') \
	     && (echo 'Checking insights mcp version…' ; env | grep 'INSIGHTS_MCP_VERSION')" || \
	  ( echo 'FAILED $(1) seems broken'; exit 1 )
	@echo -e "\nCheck usage output to at least contain the container brand"
	podman run --rm -ti \
	  $(1) --help | grep $(2)
endef

.PHONY: test-upstream-containers
test-upstream-containers: ## Pull the upstream container images and check if they are sane
	$(call check_container,ghcr.io/redhatinsights/red-hat-lightspeed-mcp:latest,red-hat-lightspeed)
	$(call check_container,quay.io/redhat-services-prod/insights-management-tenant/insights-mcp/red-hat-lightspeed-mcp:latest,red-hat-lightspeed)
	$(call check_container,ghcr.io/redhatinsights/insights-mcp:latest,insights)
	$(call check_container,quay.io/redhat-services-prod/insights-management-tenant/insights-mcp/insights-mcp:latest,insights)

.PHONY: install-test-deps
install-test-deps: ## Install test dependencies
	uv sync --locked --all-extras --dev

.PHONY: clean-test
clean-test: ## Clean test artifacts and cache
	@echo "Cleaning test artifacts..."
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

.PHONY: help
help: ## Show this help message
	@echo "make [TARGETS...]"
	@echo
	@echo 'Targets:'
	@awk '/^[a-zA-Z_\/-]+:.*? ## .*$$/ { split($$0, parts, " ## "); split(parts[1], target_parts, ":"); printf "  \033[36m%-30s\033[0m %s\n", target_parts[1], parts[2] }' $(MAKEFILE_LIST) | sort


# `INSIGHTS_CLIENT_ID` and `INSIGHTS_CLIENT_SECRET` are optional
# if you hand those over via http headers from the client.
.PHONY: run-sse
run-sse: build ## Run the MCP server with SSE transport
	# add firewall rules for fedora
	# !! ONLY set INSIGHTS_* environment variables in case you need to
	# contact another server than production
	podman run --rm --network=host \
	  --env INSIGHTS_PROXY_URL \
	  --env INSIGHTS_BASE_URL \
	  --env INSIGHTS_SSO_BASE_URL \
	  --name $(CONTAINER_BRAND)-mcp-sse localhost/$(CONTAINER_BRAND)-mcp:latest sse

.PHONY: run-http
run-http: build ## Run the MCP server with HTTP streaming transport
	# add firewall rules for fedora
	# !! ONLY set INSIGHTS_PROXY_URL, INSIGHTS_BASE_URL and INSIGHTS_SSO_BASE_URL
	# environment variables in case you really need to
	# contact another server than production
	podman run --rm --network=host \
	  --env INSIGHTS_PROXY_URL \
	  --env INSIGHTS_BASE_URL \
	  --env INSIGHTS_SSO_BASE_URL \
	  --name $(CONTAINER_BRAND)-mcp-http \
	   localhost/$(CONTAINER_BRAND)-mcp:latest http

# just an example command
# doesn't really make sense
# rather integrate this with an MCP client directly
.PHONY: run-stdio
run-stdio: build ## Run the MCP server with stdio transport
	# !! ONLY set INSIGHTS_PROXY_URL, INSIGHTS_BASE_URL and INSIGHTS_SSO_BASE_URL
	# environment variables in case you really need to
	# contact another server than production
	podman run --interactive --tty --rm \
	  --env INSIGHTS_CLIENT_ID \
	  --env INSIGHTS_CLIENT_SECRET \
	  --env INSIGHTS_PROXY_URL \
	  --env INSIGHTS_BASE_URL \
	  --env INSIGHTS_SSO_BASE_URL \
	  --name $(CONTAINER_BRAND)-mcp-stdio localhost/$(CONTAINER_BRAND)-mcp:latest

run-oauth: build ## Run the MCP server with OAuth transport
	podman run --rm --network=host \
	--env SSO_CLIENT_ID --env SSO_CLIENT_SECRET --env OAUTH_ENABLED=True \
	--name insights-mcp-oauth localhost/insights-mcp:latest http \
	--host localhost

ALL_PYTHON_FILES := $(shell find src -name "*.py")

.PHONY: generate-docs
generate-docs: usage.md toolsets.md docs/architecture-structure.svg docs/architecture-deployment.svg ## Generate documentation from the MCP server

usage.md: $(ALL_PYTHON_FILES) Makefile
	uv tool install -e .
	echo '```' > $@
	$(SCRIPT_NAME) --help >> $@
	echo '```' >> $@

toolsets.md: $(ALL_PYTHON_FILES) Makefile
	uv run python -m insights_mcp --toolset-help > $@

docs/architecture-structure.svg docs/architecture-deployment.svg docs/architecture-structure.png docs/architecture-deployment.png: HACKING.md scripts/generate_diagrams.py
	uv run python scripts/generate_diagrams.py --format svg,png
