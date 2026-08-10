#!/usr/bin/env python3
"""
Generic Newtown Bee article search via the WordPress REST API.

Searches newtownbee.com for any term(s), optionally filters article text
with a regex, and writes matches + surrounding context to CSV.

Usage:
    pip install requests

    python bee_search.py "Scott Schmidt"
    python bee_search.py torpedoes "swim results" --match "Schmidt"
    python bee_search.py torpedoes --after 2004 --before 2015 \
        --match "Schmidt" --out schmidt_articles.csv

Options:
    terms            One or more search terms sent to the Bee's search API.
    --match REGEX    Only keep articles whose text matches this regex, and
                     emit one row per regex hit with context. Default: each
                     search term itself.
    --after YYYY[-MM-DD]   Only posts on/after this date.
    --before YYYY[-MM-DD]  Only posts before this date.
    --context N      Characters of context around each match (default 160).
    --out FILE       Output CSV (default bee_search_results.csv).
    --delay SECONDS  Sleep between requests (default 1.5).
"""

import argparse
import csv
import html
import re
import sys
import time

import requests

BASE = "https://www.newtownbee.com"
API = f"{BASE}/wp-json/wp/v2/posts"
HEADERS = {"User-Agent": "personal-archive-research/1.0"}


def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    # Fix mojibake common in the Bee's imported pre-2015 articles
    s = s.replace("\u00e2\u0080\u0094", " - ").replace("\u00e2", " ").replace("\u00c2", " ")
    return re.sub(r"\s+", " ", s).strip()


def norm_date(d: str | None, end: bool = False) -> str | None:
    if not d:
        return None
    if re.fullmatch(r"\d{4}", d):
        d = f"{d}-01-01"
    return f"{d}T{'23:59:59' if end else '00:00:00'}"


def fetch_all_posts(term: str, after: str | None, before: str | None, delay: float):
    """Yield every post matching a search term, walking WP pagination."""
    page = 1
    while True:
        params = {
            "search": term,
            "per_page": 100,
            "page": page,
            "_fields": "id,date,link,title,content",
        }
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        r = requests.get(API, params=params, headers=HEADERS, timeout=30)
        if r.status_code == 400:  # past last page
            return
        r.raise_for_status()
        posts = r.json()
        if not posts:
            return
        yield from posts
        total_pages = int(r.headers.get("X-WP-TotalPages", page))
        print(f"  [{term}] page {page}/{total_pages}: {len(posts)} posts")
        if page >= total_pages:
            return
        page += 1
        time.sleep(delay)


def extract_matches(text: str, pattern: re.Pattern, ctx_chars: int):
    for m in pattern.finditer(text):
        start = max(0, m.start() - ctx_chars)
        end = min(len(text), m.end() + ctx_chars)
        yield m.group(0), text[start:end].strip()


def main():
    ap = argparse.ArgumentParser(description="Search newtownbee.com via its WordPress API")
    ap.add_argument("terms", nargs="+", help="search term(s) for the Bee's API")
    ap.add_argument("--match", help="regex to filter/highlight within article text")
    ap.add_argument("--after", help="only posts on/after this date (YYYY or YYYY-MM-DD)")
    ap.add_argument("--before", help="only posts before this date (YYYY or YYYY-MM-DD)")
    ap.add_argument("--context", type=int, default=160, help="context chars around each match")
    ap.add_argument("--out", default="bee_search_results.csv")
    ap.add_argument("--delay", type=float, default=1.5)
    args = ap.parse_args()

    match_re = re.compile(
        args.match if args.match else "|".join(re.escape(t) for t in args.terms), re.I
    )
    after, before = norm_date(args.after), norm_date(args.before, end=True)

    seen_ids, rows = set(), []
    for term in args.terms:
        print(f"Searching API for: {term!r}")
        try:
            for post in fetch_all_posts(term, after, before, args.delay):
                if post["id"] in seen_ids:
                    continue
                seen_ids.add(post["id"])
                text = strip_html(post.get("content", {}).get("rendered", ""))
                if not match_re.search(text):
                    continue
                title = strip_html(post.get("title", {}).get("rendered", ""))
                date = post.get("date", "")[:10]
                link = post.get("link", "")
                for matched, ctx in extract_matches(text, match_re, args.context):
                    rows.append([date, title, link, matched, ctx])
                print(f"  MATCH: {date}  {title}")
        except requests.HTTPError as e:
            print(f"  API error for {term!r}: {e}", file=sys.stderr)
            if e.response is not None and e.response.status_code in (401, 403, 404):
                print(
                    "  The REST API may be disabled. Fallback: use the site's search\n"
                    f"  {BASE}/?s=YOUR+TERM in a browser.",
                    file=sys.stderr,
                )
        time.sleep(args.delay)

    rows.sort(key=lambda r: r[0])
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["article_date", "article_title", "article_url", "match", "context"])
        w.writerows(rows)
    print(f"\nWrote {len(rows)} rows across {len({r[2] for r in rows})} articles -> {args.out}")


if __name__ == "__main__":
    main()
