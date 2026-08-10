# newtown-bee-search — canonical entry point (run from the project root).
# See AGENTS.md for design/status.

.PHONY: help search

help:
	@echo "  make search TERMS='term1 term2 ...' [MATCH=regex] [PROXIMITY=word1,word2] \\"
	@echo "              [WINDOW=N] [AFTER=YYYY[-MM-DD]] [BEFORE=YYYY[-MM-DD]] \\"
	@echo "              [CONTEXT=N] [FORMAT=csv|jsonl] [OUT=file] [DELAY=N]"
	@echo ""
	@echo "  PROXIMITY requires all words within WINDOW chars of each other, any order --"
	@echo "  use this instead of MATCH=Schmidt (a bare surname matches ANY person with it)."
	@echo ""
	@echo "  FORMAT selects csv (default) or jsonl (one JSON object per line) output."
	@echo ""
	@echo "  Example:"
	@echo "    make search TERMS='\"Scott Schmidt\"' \\"
	@echo "                PROXIMITY=Scott,Schmidt AFTER=2004 BEFORE=2015 OUT=schmidt_hits.csv"

search:
ifeq ($(strip $(TERMS)),)
	$(error usage: make search TERMS='term1 term2 ...' [MATCH=regex] [PROXIMITY=word1,word2] [WINDOW=N] [AFTER=...] [BEFORE=...] [CONTEXT=N] [FORMAT=csv|jsonl] [OUT=file] [DELAY=N])
endif
	uv run python -u bee_search.py $(TERMS) \
		$(if $(MATCH),--match "$(MATCH)") \
		$(if $(PROXIMITY),--proximity "$(PROXIMITY)") \
		$(if $(WINDOW),--window "$(WINDOW)") \
		$(if $(AFTER),--after "$(AFTER)") \
		$(if $(BEFORE),--before "$(BEFORE)") \
		$(if $(CONTEXT),--context "$(CONTEXT)") \
		$(if $(FORMAT),--format "$(FORMAT)") \
		$(if $(OUT),--out "$(OUT)") \
		$(if $(DELAY),--delay "$(DELAY)")
