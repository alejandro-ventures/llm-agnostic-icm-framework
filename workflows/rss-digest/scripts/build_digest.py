#!/usr/bin/env python3
"""Build a dated markdown digest from public RSS/Atom feeds.
Usage: python build_digest.py <feeds.md> <output_dir>"""
from __future__ import annotations
import csv, re, sys, datetime
from pathlib import Path

def read_feeds(md: Path) -> list[str]:
    return re.findall(r"https?://\S+", md.read_text(encoding="utf-8")) if md.exists() else []

def main(feeds_md: str, out_dir: str) -> int:
    try:
        import feedparser
    except ImportError:
        print("Install deps first: pip install -r requirements.txt"); return 1
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    urls = read_feeds(Path(feeds_md))
    today = datetime.date.today().isoformat()
    lines = [f"# Digest — {today}", ""]
    total = 0
    for url in urls:
        f = feedparser.parse(url)
        title = f.feed.get("title", url)
        lines.append(f"## {title}")
        for e in f.entries[:10]:
            lines.append(f"- [{e.get('title','(untitled)')}]({e.get('link','')})")
            total += 1
        lines.append("")
    digest = out / f"digest-{today}.md"
    digest.write_text("\n".join(lines), encoding="utf-8")
    (out / ".last_run").write_text(datetime.datetime.now().isoformat())
    with (out / "run-log.csv").open("a", newline="") as fh:
        csv.writer(fh).writerow([datetime.datetime.now().isoformat(timespec="seconds"),
                                 "rss-digest", "digest", total])
    print(f"Wrote {digest} ({total} item(s) from {len(urls)} feed(s)).")
    return 0

if __name__ == "__main__":
    a = sys.argv[1:]
    raise SystemExit(main(a[0] if a else "references/feeds.example.md",
                          a[1] if len(a) > 1 else "output"))
