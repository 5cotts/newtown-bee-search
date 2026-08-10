# Newtown Bee Swim Times Project

## Goal
Compile a complete CSV of Scott Schmidt's childhood swim times as published in
The Newtown Bee (newtownbee.com), covering 2004-2014. Scott swam for:
- **Newtown Torpedoes** — Parks & Rec junior team (roughly 2004-05 through
  2008-09 seasons; he was Boys 9-10 in Nov 2004 and Boys 13-14 in Nov 2008)
- **Newtown High School swim team** (after Torpedoes, roughly 2009-2013;
  NHS boys season runs ~Dec-Mar)

Deliverable: CSV with one row per swim. Required columns include the event,
place, time, date, and **a source URL column** pointing to the Bee article
where the time was found. Current working schema:
`Article Date, Age Group, Event, Place, Time, Meet Notes, Article Title, Article URL`

## Confirmed results so far (verified by fetching the articles)
1. **2004-11-19** — Boys 9-10, vs West Haven Wizzards (meet Nov 6, 2004):
   50 Yard Freestyle, 3rd, 58.42
   https://www.newtownbee.com/11192004/the-newtown-torpedoes-got-the-2004-05-season-off-to-a-fine-start-with-a-t/
2. **2008-11-28** — Boys 13-14, at Bristol (third meet of season):
   200 Free 2:42.76 (2nd); 200 IM 3:12.81 (2nd); 50 Free 31.67 (2nd)
   https://www.newtownbee.com/11282008/making-a-splash-torpedoes-swim-results/

Checked and confirmed NOT containing Schmidt: Nov 2009 Torpedoes-vs-Watertown
results (he had left the team), March 2010 Torpedoes All-Stars list, and all
search-engine-indexed NHS swim coverage.

Fun non-swim find: a Feb 2005 Bee article on the youth basketball rec league
mentions "Scott 'The Eraser' Schmidt" (Blue Devils). Not for the CSV.

## Key constraint discovered
- The Bee's month-archive filter (`/article-archive/?month=YYYYMM`) is
  **broken** — it ignores the param and returns current articles. No
  systematic month-by-month crawl is possible from outside.
- Search engines have indexed only a small fraction of the Bee's 2004-2014
  content; NHS boys swim coverage from 2010-2014 is almost entirely
  un-indexed. Extensive searching (name, teammates, opponents, coaches,
  "S. Schmidt" abbreviation) surfaced only the two articles above.
- Old imported articles contain mojibake (Â, â€" etc.); strip before matching.

## Strategy that should work: WordPress REST API
The site is WordPress. `bee_search.py` (in this zip) queries
`https://www.newtownbee.com/wp-json/wp/v2/posts?search=...` with pagination
and date filters — this searches the full article database, including
un-indexed pre-2015 content, IF the endpoint is enabled.

**Status: NOT YET TESTED against the live site.** The previous agent's
sandbox blocked newtownbee.com (network allowlist). Scott plans to run the
script locally, or an agent with network access to newtownbee.com can run it.

Usage:
```
pip install requests
python bee_search.py torpedoes "swim results" swimming swim \
    --match "Schmidt" --after 2004 --before 2015 --out schmidt_hits.csv
python bee_search.py "Scott Schmidt"   # broad name search, all years
```

## Next steps
1. Run `bee_search.py` (locally or with newtownbee.com network access).
   If `wp-json` returns 401/403/404 it may be disabled — fall back to the
   site's HTML search (`newtownbee.com/?s=Schmidt`, JS-driven, works in a
   real browser), or email sports editor Andy Hutchison (andyh@thebee.com),
   who wrote most of this coverage and has full archives.
2. For every hit, verify by reading the context/article; extract age group,
   event, place, time, meet details.
3. Watch for name variants: "Scott Schmidt", "S. Schmidt", possibly
   "Schmidt" alone in relay listings (relays list four surnames).
4. Merge new rows into the existing CSV (Scott has
   `scott_schmidt_newtown_bee_swim_times.csv` with the 4 confirmed rows),
   keep the source URL column, sort by date.
5. Also consider searching for NHS-era terms: "Nighthawks" swim, SWC
   championships, CIAC Class L/LL (2010-2013), coach names from that era.

## Files in this zip
- `bee_search.py` — generic Bee search CLI (WordPress API, pagination,
  `--match` regex filter, `--after/--before` dates, CSV output with context
  snippets). Swim-specific regex extraction was intentionally removed; a
  separate `bee_swim_scraper.py` variant with event/time auto-extraction
  exists in the chat history if needed.
