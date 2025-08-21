.PHONY: build-prod
build-prod: generate-docs ## Build the container image but with the upstream tag
	podman build --tag ghcr.io/redhatinsights/insights-mcp:latest .

.PHONY: build
build: generate-docs ## Build the container image
	podman build --tag insights-mcp .

# please set from outside
TAG ?= UNKNOWN

.PHONY: build-claude-extension
build-claude-extension: ## Build the Claude extension
	sed -i "s/---VERSION---/$(TAG)/g" claude_desktop/manifest.json
	zip -j insights-mcp-$(TAG).dxt claude_desktop/*
	sed -i "s/$(TAG)/---VERSION---/g" claude_desktop/manifest.json

.PHONY: lint
lint: generate-docs ## Run linting with pre-commit
	pre-commit run --all-files --hook-stage manual

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
	@awk 'match($$0, /^([a-zA-Z_\/-]+):.*? ## (.*)$$/, m) {printf "  \033[36m%-30s\033[0m %s\n", m[1], m[2]}' $(MAKEFILE_LIST) | sort


# `INSIGHTS_CLIENT_ID` and `INSIGHTS_CLIENT_SECRET` are optional
# if you hand those over via http headers from the client.
.PHONY: run-sse
run-sse: build ## Run the MCP server with SSE transport
	# add firewall rules for fedora
	podman run --rm --network=host --env INSIGHTS_CLIENT_ID --env INSIGHTS_CLIENT_SECRET --name insights-mcp-sse localhost/insights-mcp:latest sse

.PHONY: run-http
run-http: build ## Run the MCP server with HTTP streaming transport
	# add firewall rules for fedora
	podman run --rm --network=host --env INSIGHTS_CLIENT_ID --env INSIGHTS_CLIENT_SECRET --name insights-mcp-http localhost/insights-mcp:latest http

# just an example command
# doesn't really make sense
# rather integrate this with an MCP client directly
.PHONY: run-stdio
run-stdio: build ## Run the MCP server with stdio transport
	podman run --interactive --tty --rm --env INSIGHTS_CLIENT_ID --env INSIGHTS_CLIENT_SECRET --name insights-mcp-stdio localhost/insights-mcp:latest

ALL_PYTHON_FILES := $(shell find src -name "*.py")

.PHONY: generate-docs
generate-docs: usage.md toolsets.md ## Generate documentation from the MCP server

usage.md: $(ALL_PYTHON_FILES) Makefile
	echo '```' > $@
	uv run python -m insights_mcp --help >> $@
	echo '```' >> $@

toolsets.md: $(ALL_PYTHON_FILES) Makefile
	uv run python -m insights_mcp --toolset-help > $@
