#!/usr/bin/env python3
"""Publish any queued blog posts that have come due, in Melbourne time.

Run from the root of a site checkout, with the post-queue branch materialised
at ./_queue (queue.json + posts/<slug>/index.html).

  python3 _queue/scripts/drip_publish.py [--dry-run] [--force-slug SLUG]

Idempotent: a post already present in blog/ is skipped. Prints the URLs it
published to $GITHUB_OUTPUT as `urls` so the workflow can ping IndexNow.
"""
import argparse
import html
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

ORIGINS = {
    "au": "https://www.theestateorganiser.com.au",
    "usa": "https://theestateorganiser.com",
    "ca": "https://theestateorganiser.ca",
}


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#x27;"))


def post_meta(path):
    t = path.read_text(encoding="utf-8")
    title = html.unescape(re.search(r"<title>(.*?)</title>", t, re.S).group(1))
    desc = html.unescape(
        re.search(r'<meta name="description" content="([^"]*)"', t).group(1))
    return title, desc


def add_to_index(repo, site, slug, date, title, desc):
    idx = repo / "blog/index.html"
    t = idx.read_text(encoding="utf-8")
    href = f"/blog/{slug}/"
    if f'href="{href}"' in t:
        return False
    y, m, d = (int(x) for x in date.split("-"))
    if site == "au":
        entry = (f'<li style="margin-bottom:14px"><a href="{href}">{esc(title)}</a>'
                 f'<div class="date">{MONTHS[m - 1]} {d}, {y}</div></li>\n')
        anchor = "<ul style='list-style:none;padding:0'>"
        i = t.index(anchor) + len(anchor)
        t = t[:i] + entry + t[i:]
    else:
        card = (f'<a class="card" href="{href}" style="text-decoration:none;'
                f'display:block;margin-bottom:22px"><h4>{esc(title)}</h4>'
                f'<p>{esc(desc[:150])}</p>'
                f'<span class="micro" style="color:var(--gold-d)">'
                f'Read the article →</span></a>')
        cards = list(re.finditer(
            r'<a class="card" href="/blog/([^"/]+)/"[^>]*>.*?</a>', t, re.S))
        if not cards:
            raise SystemExit("no existing cards in blog index, refusing to guess")
        later = [c for c in cards if c.group(1) > slug]
        pos = later[0].start() if later else cards[-1].end()
        t = t[:pos] + card + t[pos:]
    idx.write_text(t, encoding="utf-8")
    return True


def add_to_sitemap(repo, site, slug, date):
    sm = repo / "sitemap.xml"
    t = sm.read_text(encoding="utf-8")
    loc = f"{ORIGINS[site]}/blog/{slug}/"
    if f"<loc>{loc}</loc>" in t:
        return False
    t = t.replace("</urlset>",
                  f"  <url><loc>{loc}</loc><lastmod>{date}</lastmod></url>\n</urlset>")
    sm.write_text(t, encoding="utf-8")
    return True


def due(entry, now, publish_hour, force_slug):
    if force_slug and entry["slug"] == force_slug:
        return True
    y, m, d = (int(x) for x in entry["date"].split("-"))
    today = (now.year, now.month, now.day)
    if (y, m, d) < today:
        return True          # a missed run catches up on the next pass
    if (y, m, d) == today:
        return now.hour >= publish_hour
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force-slug", default="")
    ap.add_argument("--queue", default="_queue",
                    help="where the post-queue branch is materialised; keep this "
                         "OUTSIDE the repo working tree in CI so it is never committed")
    args = ap.parse_args()

    repo = Path.cwd()
    qdir = Path(args.queue).resolve()
    cfg = json.loads((qdir / "queue.json").read_text(encoding="utf-8"))
    site = cfg["site"]
    tz = ZoneInfo(cfg.get("timezone", "Australia/Melbourne"))
    hour = int(cfg.get("publish_hour", 9))
    now = datetime.now(tz)

    print(f"site={site}  now={now:%Y-%m-%d %H:%M %Z}  publish_hour={hour}")
    if args.dry_run:
        print("DRY RUN: nothing will be written")

    published = []
    for e in cfg["entries"]:
        slug, date = e["slug"], e["date"]
        live = repo / "blog" / slug / "index.html"
        src = qdir / "posts" / slug / "index.html"
        if live.exists():
            print(f"  [live]    {date}  {slug}")
            continue
        if not due(e, now, hour, args.force_slug):
            print(f"  [waiting] {date}  {slug}")
            continue
        if not src.exists():
            print(f"  [ERROR]   {date}  {slug}: not in the queue at {src}")
            sys.exit(1)
        title, desc = post_meta(src)
        print(f"  [PUBLISH] {date}  {slug}  ({title})")
        if args.dry_run:
            published.append(f"{ORIGINS[site]}/blog/{slug}/")
            continue
        live.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, live)
        add_to_index(repo, site, slug, date, title, desc)
        add_to_sitemap(repo, site, slug, date)
        published.append(f"{ORIGINS[site]}/blog/{slug}/")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        host = ORIGINS[site].split("//", 1)[1]
        key = cfg.get("indexnow_key", "")
        payload = json.dumps({
            "host": host,
            "key": key,
            "keyLocation": f"{ORIGINS[site]}/{key}.txt",
            "urlList": published + [f"{ORIGINS[site]}/blog/",
                                    f"{ORIGINS[site]}/sitemap.xml"],
        })
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"count={len(published)}\n")
            fh.write("urls=" + " ".join(published) + "\n")
            fh.write(f"indexnow={payload}\n")
    print(f"published {len(published)}: {' '.join(published) or 'nothing'}")


if __name__ == "__main__":
    main()
