# newtown-bee-search

Searches The Newtown Bee (newtownbee.com) for articles mentioning Scott
Schmidt, using the site's own `/search/?q=...` page (not the WordPress
REST API — that's enabled but returns zero results for everything; see
`AGENTS.md`). Reaches the full archive, including pre-2015 content search
engines never indexed. Saves each matching article's full text to CSV.

## Setup

```bash
cd newtown-bee-search
uv sync
```

## Usage

Always run through `make`, not `uv run python bee_search.py ...` directly
— see the root workspace `AGENTS.md` convention (make targets are the
canonical entry point for every project here).

```bash
make search TERMS='Scott Schmidt' MATCH=Schmidt AFTER=2004 BEFORE=2015 OUT=schmidt_mentions.csv
make help    # full flag reference
```

- `TERMS` — one or more search terms/phrases (space-separated; quote
  multi-word phrases individually within the string).
- `MATCH` — regex a hit's full article text must contain to survive;
  defaults to an OR of the terms if omitted.
- `AFTER` / `BEFORE` — date bounds (`YYYY` or `YYYY-MM-DD`) on the
  article's published date.
- `OUT` — output CSV path (git-ignored; treat as a local data product,
  not something to commit).

Output columns: `article_date, article_title, article_url, search_term,
match_count, context, full_text`.

See `AGENTS.md` for the project's goal, confirmed swim results so far, and
the reverse-engineering notes on how the site search actually works.
