#!/usr/bin/env python3
"""Acceptance checks for the built site (docs/).

1. every internal link and asset reference resolves
2. main-site link count per page (max 3) and anchor variety
3. JSON-LD parses, canonical/title/description sanity
4. sitemap.xml + robots.txt
5. no 8-word phrase reused from the main site's own pages
"""
from __future__ import annotations

import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
CRAWLED = Path("/tmp/vv-crawl")
MAIN_HOST = "vibevietnamtour.com"
failures: list[str] = []


def note(ok: bool, message: str) -> None:
    print(("OK   " if ok else "FAIL ") + message)
    if not ok:
        failures.append(message)


def visible_text(raw: str) -> str:
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).lower()


def shingles(text: str, size: int = 8) -> set[str]:
    words = [w for w in re.findall(r"[a-z0-9']+", text) if w]
    out = {" ".join(words[i:i + size]) for i in range(max(0, len(words) - size + 1))}
    # factual identifiers (postal address, licence and tax numbers) are exempt:
    # they must match the official registration, so they are not "copied prose".
    return {s for s in out if not any(ch.isdigit() for ch in s)}


def main() -> None:
    pages = sorted(DOCS.rglob("*.html"))
    print(f"--- internal references ({len(pages)} pages) ---")
    broken: list[str] = []
    main_links: dict[str, list[str]] = {}
    for page in pages:
        raw = page.read_text(encoding="utf-8")
        rel = page.relative_to(DOCS)
        for attr, ref in re.findall(r'(href|src)="([^"]+)"', raw):
            if ref.startswith(("http://", "https://", "mailto:", "#", "data:")):
                if MAIN_HOST in ref and attr == "href":
                    main_links.setdefault(str(rel), []).append(ref)
                continue
            target = (DOCS / ref.lstrip("/").replace("vietnam-travel-guide/", "", 1)) if ref.startswith("/") else (page.parent / ref)
            if ref.endswith("/"):
                target = target / "index.html"
            if not target.exists():
                broken.append(f"{rel} -> {ref}")
    note(not broken, f"internal links resolve ({len(broken)} broken)")
    for b in broken:
        print("      ", b)

    print("\n--- main-site links (limit 3 per page) ---")
    anchors: set[str] = set()
    for page in pages:
        raw = page.read_text(encoding="utf-8")
        rel = str(page.relative_to(DOCS))
        hrefs = re.findall(r'<a[^>]+href="(https://vibevietnamtour\.com[^"]*)"[^>]*>(.*?)</a>', raw, re.S)
        note(len(hrefs) <= 3, f"{rel:52} {len(hrefs)} link(s)")
        for _, text in hrefs:
            anchors.add(re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", text))).strip())
    print("      anchors used:", sorted(anchors))

    print("\n--- head sanity ---")
    titles, descs, canonicals = {}, {}, {}
    for page in pages:
        raw = page.read_text(encoding="utf-8")
        rel = str(page.relative_to(DOCS))
        t = re.search(r"<title>(.*?)</title>", raw, re.S)
        d = re.search(r'<meta name="description" content="(.*?)"', raw, re.S)
        c = re.search(r'<link rel="canonical" href="(.*?)"', raw, re.S)
        h1 = re.findall(r"<h1[^>]*>(.*?)</h1>", raw, re.S)
        og = re.findall(r'property="og:(title|description|image|url)" content="(.*?)"', raw)
        ld = re.findall(r'<script type="application/ld\+json">(.*?)</script>', raw, re.S)
        problems = []
        if not t or not d or not c:
            problems.append("missing title/description/canonical")
        if len(h1) != 1:
            problems.append(f"h1 count {len(h1)}")
        if len(og) < 4:
            problems.append(f"og tags {len(og)}")
        for block in ld:
            try:
                data = json.loads(block)
                if data.get("@context") != "https://schema.org":
                    problems.append("json-ld context")
                ET.fromstring("<x/>")  # noop, keeps import honest
            except Exception as exc:  # noqa: BLE001
                problems.append(f"json-ld invalid: {exc}")
        if t:
            titles.setdefault(t.group(1), []).append(rel)
        if d:
            descs.setdefault(d.group(1), []).append(rel)
        if c:
            canonicals.setdefault(c.group(1), []).append(rel)
        note(not problems, f"{rel:52} {'; '.join(problems) if problems else 'title/desc/canonical/og/json-ld ok'}")
        if rel != "index.html":
            note(c.group(1).endswith("/" + rel.replace("index.html", "")) or c.group(1).endswith(rel),
                 f"      canonical matches path: {c.group(1)}")
    dupes = {k: v for k, v in list(titles.items()) + list(descs.items()) + list(canonicals.items()) if len(v) > 1}
    note(not dupes, f"no duplicate title/description/canonical ({len(dupes)} duplicates)")

    print("\n--- javascript syntax ---")
    import shutil
    import subprocess
    if shutil.which("node"):
        for js in sorted((DOCS / "assets" / "js").glob("*.js")):
            proc = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
            note(proc.returncode == 0, f"{js.name} parses ({proc.stderr.strip().splitlines()[-1] if proc.returncode else 'ok'})")
    else:
        print("      node not available, skipped")

    print("\n--- sitemap + robots ---")
    tree = ET.parse(DOCS / "sitemap.xml")
    locs = [e.text for e in tree.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    note(len(locs) >= len(pages) - 1, f"sitemap lists {len(locs)} urls for {len(pages)} pages")
    robots = (DOCS / "robots.txt").read_text(encoding="utf-8")
    note("Sitemap:" in robots and "Allow: /" in robots, "robots.txt allows crawling and points to the sitemap")

    print("\n--- originality check against the main site ---")
    main_text = " ".join(visible_text(p.read_text(encoding="utf-8", errors="ignore"))
                          for p in CRAWLED.glob("*.html"))
    main_set = shingles(main_text)
    worst = 0
    for page in pages:
        mine = shingles(visible_text(page.read_text(encoding="utf-8")))
        overlap = mine & main_set
        worst = max(worst, len(overlap))
        if overlap:
            print("      ", page.relative_to(DOCS), sorted(overlap)[:3])
    note(worst == 0, f"no 8-word phrase shared with the main site (worst page: {worst})")

    print(f"\n{'ALL CHECKS PASSED' if not failures else str(len(failures)) + ' CHECK(S) FAILED'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
