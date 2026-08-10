#!/usr/bin/env python3
"""
Search The Newtown Bee (newtownbee.com) via its live site search.

The WordPress REST API (/wp-json/wp/v2/posts) is enabled but returns zero
results for every query, including no query at all -- articles simply
aren't exposed through it (confirmed by inspecting /wp-json/wp/v2/types:
the "post" type is registered but empty; /wp/v2/pages returns real data).

The site's OWN search page works instead: /search/?q=... is plain
server-rendered HTML (no JS, no auth) and searches the full archive,
including pre-2015 content that search engines never indexed. Confirmed
by finding NHS-era swim articles (2010-2012) that were previously
unreachable by any indexed search.

Quirk: the site's "sort" param is backwards from its own UI labels.
Empirically: sort=desc -> oldest first, sort=asc (or omitted) -> newest
first. This script's --order flag hides that behind sane names.

Every surviving hit's full article text is fetched (one extra request per
hit, after the search-result list itself) and saved into the CSV so the
whole corpus can be reviewed/grepped offline without re-fetching.

Usage:
    pip install requests

    python bee_search.py "Scott Schmidt"
    python bee_search.py torpedoes "swim results" swimming swim \
        --after 2004 --before 2015 --out hits.csv
    python bee_search.py "Scott Schmidt" --match "Schmidt" --after 2004 --before 2015 \
        --out schmidt_hits.csv

Options:
    terms              One or more search terms/phrases sent to the Bee's
                        search page (each run as a separate query, results
                        merged and deduped by URL).
    --after YYYY[-MM-DD]    Only articles on/after this date (article date
                        is embedded in the URL, e.g. /11282008/... ).
    --before YYYY[-MM-DD]   Only articles strictly before this date.
    --order {oldest,newest}  Page order (default: oldest). With --after
                        and/or --before set, pagination stops as soon as a
                        page crosses out of range, instead of walking every
                        page of the (possibly large) result set.
    --match REGEX       Regex tested against each hit's full article text
                        (fetched from the page). Default: OR of the search
                        terms. Hits with no match are dropped.
    --context N         Characters of context around the first match, shown
                        in the CSV's `context` preview column (default 160).
    --out FILE          Output CSV (default bee_search_results.csv).
    --delay SECONDS     Sleep between requests (default 1.5).
"""

import argparse
import csv
import html
import re
import sys
import time
from datetime import date

import requests
from bs4 import BeautifulSoup

BASE = "https://www.newtownbee.com"
SEARCH_URL = f"{BASE}/search/"
HEADERS = {"User-Agent": "personal-archive-research/1.0"}
PER_PAGE = 10

RESULT_PATTERN = re.compile(
    r'href="(?P<url>https://www\.newtownbee\.com/(?P<date>\d{8})/[^"?]+/)\?q=[^"]*">\s*'
    r'<h2 class="teaser__headline">\s*<span class="teaser__headline-marker">\s*'
    r'(?P<title>.*?)\s*</span>',
    re.S,
)
TOTAL_PATTERN = re.compile(r'search_results_query">(\d+) results returned')


def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    # Fix mojibake common in the Bee's imported pre-2015 articles
    s = s.replace("â", " - ").replace("â", " ").replace("Â", " ")
    return re.sub(r"\s+", " ", s).strip()


def url_date_to_iso(d: str) -> str:
    """Bee article URLs embed the publish date as MMDDYYYY."""
    return f"{d[4:8]}-{d[0:2]}-{d[2:4]}"


def parse_bound(d: str | None) -> date | None:
    if not d:
        return None
    if re.fullmatch(r"\d{4}", d):
        d = f"{d}-01-01"
    return date.fromisoformat(d)


def fetch_all_hits(term: str, order: str, after: date | None, before: date | None, delay: float):
    """Yield (iso_date, title, url) for every search hit, walking pagination.

    Stops early once a page crosses out of the after/before range, since
    results are strictly ordered by --order.
    """
    start = 0
    total = None
    while True:
        params = {"q": term}
        if order == "oldest":
            params["sort"] = "desc"  # backwards vs. the site's own UI labels
        if start:
            params["start"] = start
        r = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        body = r.text

        if total is None:
            m = TOTAL_PATTERN.search(body)
            total = int(m.group(1)) if m else 0
            print(f"  [{term}] {total} results returned by the site search")
            if total == 0:
                return

        hits, seen_on_page = [], set()
        for m in RESULT_PATTERN.finditer(body):
            if m.group("url") in seen_on_page:
                continue
            seen_on_page.add(m.group("url"))
            hits.append((url_date_to_iso(m.group("date")), strip_html(m.group("title")), m.group("url")))

        if not hits:
            return

        stop = False
        for iso, title, url in hits:
            d = date.fromisoformat(iso)
            if order == "oldest":
                if before and d >= before:
                    stop = True
                    continue
                if after and d < after:
                    continue
            else:
                if after and d < after:
                    stop = True
                    continue
                if before and d >= before:
                    continue
            yield iso, title, url

        print(f"  [{term}] start={start}: {len(hits)} hits ({hits[0][0]} .. {hits[-1][0]})")

        if stop:
            return
        start += PER_PAGE
        if start >= total:
            return
        time.sleep(delay)


def extract_matches(text: str, pattern: re.Pattern, ctx_chars: int):
    for m in pattern.finditer(text):
        s = max(0, m.start() - ctx_chars)
        e = min(len(text), m.end() + ctx_chars)
        yield m.group(0), text[s:e].strip()


def fetch_article_text(url: str) -> str:
    """Fetch an article page and return just its body text.

    Article body copy lives in scattered <p class="article__body"> (and
    occasionally a span.article__leadin) elements, not one wrapping
    container, interleaved with nav/sidebar/related-article markup. A
    plain HTML-tag strip over the whole page would pull in that boilerplate
    and dilute --match context, so this targets the body-class elements
    specifically via a real parser.
    """
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    parts = [
        el.get_text(" ", strip=True)
        for el in soup.find_all(class_=lambda c: c and "article__body" in c.split())
    ]
    text = " ".join(p for p in parts if p)
    return strip_html(text)


def main():
    ap = argparse.ArgumentParser(description="Search newtownbee.com via its own site search")
    ap.add_argument("terms", nargs="+", help="search term(s)/phrase(s)")
    ap.add_argument("--match", help="regex to filter/extract; default: OR of terms")
    ap.add_argument("--after", help="only articles on/after this date (YYYY or YYYY-MM-DD)")
    ap.add_argument("--before", help="only articles strictly before this date")
    ap.add_argument("--order", choices=["oldest", "newest"], default="oldest")
    ap.add_argument("--context", type=int, default=160,
                     help="chars of context around the first match, for the CSV preview column")
    ap.add_argument("--out", default="bee_search_results.csv")
    ap.add_argument("--delay", type=float, default=1.5)
    args = ap.parse_args()

    match_re = re.compile(
        args.match if args.match else "|".join(re.escape(t) for t in args.terms), re.I
    )
    after, before = parse_bound(args.after), parse_bound(args.before)

    seen_urls, rows = set(), []
    for term in args.terms:
        print(f"Searching site search for: {term!r}")
        try:
            for iso, title, url in fetch_all_hits(term, args.order, after, before, args.delay):
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                time.sleep(args.delay)
                try:
                    text = fetch_article_text(url)
                except requests.HTTPError as e:
                    print(f"  article fetch error for {url}: {e}", file=sys.stderr)
                    continue

                found = list(extract_matches(text, match_re, args.context))
                if not found:
                    continue
                _, first_context = found[0]
                rows.append([iso, title, url, term, len(found), first_context, text])
                print(f"  MATCH ({len(found)}x): {iso}  {title}")
        except requests.HTTPError as e:
            print(f"  search error for {term!r}: {e}", file=sys.stderr)
        time.sleep(args.delay)

    rows.sort(key=lambda r: r[0])
    header = ["article_date", "article_title", "article_url", "search_term",
              "match_count", "context", "full_text"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"\nWrote {len(rows)} rows across {len({r[2] for r in rows})} articles -> {args.out}")


if __name__ == "__main__":
    main()
