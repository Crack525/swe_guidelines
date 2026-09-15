# Software Design and Architecture Guidelines: checks and generators
SHELL := /bin/bash
PYTHON := python3
NPX := npx --yes
MARKDOWNLINT := $(NPX) markdownlint-cli2@0.18.1

.PHONY: help check lint lenses leaks links skills plugin gen-skills gen-skills-check clean

help:              ## show targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

check: lint lenses leaks links gen-skills-check skills plugin ## run every check (what CI runs)

lint:              ## markdownlint over every Markdown file
	$(MARKDOWNLINT) "**/*.md" "#node_modules"

lenses:            ## every lens follows the format and cites a real section
	$(PYTHON) scripts/check_lenses.py

leaks:             ## no product, hardware, or assistant-tooling vocabulary in the published files
	$(PYTHON) scripts/check_leaks.py

links:             ## every relative link and anchor resolves
	$(PYTHON) scripts/check_links.py

skills:            ## every skill has valid frontmatter and references files that exist
	$(PYTHON) scripts/check_skills.py

plugin:            ## validate the plugin, marketplace, skills, and agents with Claude Code (skipped when claude is not installed)
	@if command -v claude >/dev/null 2>&1; then \
	  claude plugin validate . --strict && claude plugin validate skills --strict && claude plugin validate agents --strict; \
	else echo "plugin: claude not installed, skipped"; fi

gen-skills:        ## regenerate the review skills from the template and the lens files
	$(PYTHON) scripts/gen_skills.py

gen-skills-check:  ## fail when a generated skill is out of date
	$(PYTHON) scripts/gen_skills.py --check

clean:             ## remove tool caches
	rm -rf .markdownlint-cli2-cache node_modules
