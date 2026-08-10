# newtown-bee-search — canonical entry point (run from the project root).
# See AGENTS.md for design/status.

.PHONY: help search

help:
	@echo "  make search TERMS='term1 term2 ...' [MATCH=regex] [AFTER=YYYY[-MM-DD]] \\"
	@echo "              [BEFORE=YYYY[-MM-DD]] [CONTEXT=N] [OUT=file.csv] [DELAY=N]"
	@echo ""
	@echo "  Example:"
	@echo "    make search TERMS='torpedoes \"swim results\" swimming swim' \\"
	@echo "                MATCH=Schmidt AFTER=2004 BEFORE=2015 OUT=schmidt_hits.csv"

search:
	@test -n "$(TERMS)" || { echo "usage: make search TERMS='term1 term2 ...' [MATCH=regex] [AFTER=...] [BEFORE=...] [CONTEXT=N] [OUT=file.csv] [DELAY=N]"; exit 2; }
	uv run python bee_search.py $(TERMS) \
		$(if $(MATCH),--match "$(MATCH)") \
		$(if $(AFTER),--after "$(AFTER)") \
		$(if $(BEFORE),--before "$(BEFORE)") \
		$(if $(CONTEXT),--context "$(CONTEXT)") \
		$(if $(OUT),--out "$(OUT)") \
		$(if $(DELAY),--delay "$(DELAY)")
