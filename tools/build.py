#!/usr/bin/env python3
"""Build the Vietnam Travel Guide static site into ./docs (GitHub Pages root).

Usage:
    python3 tools/build.py            # build
    python3 tools/build.py --check    # build + print the SEO/QA report

Every page lives in src/pages/<name>.html with a small front-matter block.
Phase 2 (ko/ja/zh) only needs LOCALES extended below: hreflang output and the
language switcher are generated from that list.
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
PAGES_DIR = SRC / "pages"
OUT = ROOT / "docs"

SITE_URL = "https://hqson130489.github.io/vietnam-travel-guide"
BASE = "/vietnam-travel-guide/"
BRAND = "Vietnam Travel Guide"
MAIN_SITE = "https://vibevietnamtour.com/"
UPDATED_HUMAN = "September 2026"
UPDATED_ISO = "2026-09-30"
LOCALES = ["en"]  # phase 2: ["en", "ko", "ja", "zh"]

NAV_KEYS = {"home": "NAV_HOME", "itineraries": "NAV_ITIN", "guides": "NAV_GUIDES",
            "tools": "NAV_TOOLS", "about": "NAV_ABOUT"}


# --------------------------------------------------------------------------- #
# front matter + helpers
# --------------------------------------------------------------------------- #
def parse_page(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"^<!--\s*\n(.*?)\n\s*-->\s*\n(.*)$", raw, re.S)
    if not m:
        raise SystemExit(f"{path.name}: missing <!-- front matter --> block")
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    meta["body"] = m.group(2).strip()
    meta["source"] = path.name
    for required in ("title", "description", "h1", "slug", "kind"):
        if not meta.get(required):
            raise SystemExit(f"{path.name}: front matter is missing '{required}'")
    return meta


def slug_to_out(slug: str) -> Path:
    if slug in ("/", ""):
        return OUT / "index.html"
    if slug.endswith(".html"):
        return OUT / slug.lstrip("/")
    return OUT / slug.strip("/") / "index.html"


def abs_url(slug: str) -> str:
    if slug in ("/", ""):
        return SITE_URL + "/"
    return SITE_URL + "/" + slug.strip("/") + ("/" if not slug.endswith(".html") else "")


def text_of(fragment: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", fragment, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def word_count(fragment: str) -> int:
    return len([w for w in text_of(fragment).split(" ") if w])


def image_size(path: Path) -> tuple[int, int] | None:
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        return None
    if not path.exists():
        return None
    with Image.open(path) as im:
        return im.size


def strip_accents(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))


# --------------------------------------------------------------------------- #
# structured data
# --------------------------------------------------------------------------- #
def organization_node() -> dict:
    return {
        "@type": "Organization",
        "@id": MAIN_SITE + "#organization",
        "name": "Vibe Vietnam Tour",
        "url": MAIN_SITE,
        "logo": {
            "@type": "ImageObject",
            "url": SITE_URL + "/assets/img/logo.png",
            "width": 612,
            "height": 148,
        },
        "description": "Vietnam tour operator offering tailor-made private tours, day tours and multi-day packages.",
    }


def breadcrumb_node(items: list[tuple[str, str]]) -> dict:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": url}
            for i, (name, url) in enumerate(items)
        ],
    }


def faq_node(pairs: list[tuple[str, str]]) -> dict:
    return {
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in pairs
        ],
    }


def extract_faq(body: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for block in re.findall(r"<details[^>]*>(.*?)</details>", body, re.S | re.I):
        m = re.search(r"<summary[^>]*>(.*?)</summary>(.*)", block, re.S | re.I)
        if not m:
            continue
        question = text_of(m.group(1))
        answer = text_of(m.group(2))
        if question and answer:
            pairs.append((question, answer))
    return pairs


def jsonld_for(meta: dict, crumbs: list[tuple[str, str]], faqs: list[tuple[str, str]]) -> str:
    kind = meta.get("kind", "page")
    graph: list[dict] = [organization_node(), breadcrumb_node(crumbs)]
    canonical = abs_url(meta["slug"])
    common = {"url": canonical, "name": meta["title"], "description": meta["description"],
              "inLanguage": "en", "dateModified": UPDATED_ISO,
              "isPartOf": {"@id": SITE_URL + "/#website"}}

    if kind == "home":
        graph.append({
            "@type": "WebSite",
            "@id": SITE_URL + "/#website",
            "url": SITE_URL + "/",
            "name": BRAND,
            "description": meta["description"],
            "inLanguage": "en",
            "publisher": {"@id": MAIN_SITE + "#organization"},
        })
        graph.append({"@type": "WebPage", **common})
    elif kind in ("itinerary", "guide"):
        graph.append({
            "@type": "Article",
            **common,
            "headline": meta["h1"][:110],
            "author": {"@id": MAIN_SITE + "#organization"},
            "publisher": {"@id": MAIN_SITE + "#organization"},
            "datePublished": UPDATED_ISO,
            "image": SITE_URL + "/assets/" + meta["og"] if meta.get("og") else None,
        })
    elif kind == "tool":
        graph.append({
            "@type": "WebApplication",
            **common,
            "applicationCategory": "TravelApplication",
            "operatingSystem": "Any modern browser",
            "browserRequirements": "Requires JavaScript",
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            "publisher": {"@id": MAIN_SITE + "#organization"},
        })
    elif kind == "about":
        graph.append({"@type": "AboutPage", **common, "about": {"@id": MAIN_SITE + "#organization"}})
    elif kind == "collection":
        graph.append({"@type": "CollectionPage", **common})
    else:
        graph.append({"@type": "WebPage", **common})

    if faqs:
        graph.append(faq_node(faqs))

    payload = {"@context": "https://schema.org", "@graph": [{k: v for k, v in g.items() if v is not None} for g in graph if g]}
    return '<script type="application/ld+json">\n' + json.dumps(payload, ensure_ascii=False, indent=2) + "\n</script>"


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #
def breadcrumb_html(crumbs: list[tuple[str, str | None]]) -> str:
    if len(crumbs) < 2:
        return ""
    parts = []
    for i, (name, url) in enumerate(crumbs):
        last = i == len(crumbs) - 1
        label = html.escape(name)
        if last or not url:
            parts.append(f'<span class="crumb-current">{label}</span>' if last else f'<span>{label}</span>')
        else:
            parts.append(f'<a href="{url}">{label}</a>')
    return ('    <nav class="breadcrumb" aria-label="Breadcrumb">\n      '
            + '\n      <span class="crumb-sep" aria-hidden="true">/</span>\n      '.join(parts)
            + "\n    </nav>")


def hero_html(meta: dict) -> str:
    if not meta.get("hero"):
        return ""
    size = image_size(SRC / "assets" / meta["hero"])
    dims = f' width="{size[0]}" height="{size[1]}"' if size else ""
    caption = (f'\n        <figcaption>{html.escape(meta["hero_caption"])}</figcaption>'
               if meta.get("hero_caption") else "")
    return (f'      <figure class="hero">\n'
            f'        <img src="{BASE}assets/{meta["hero"]}" alt="{html.escape(meta.get("hero_alt", ""))}"'
            f'{dims} fetchpriority="high" decoding="async">{caption}\n'
            f'      </figure>')


def card_html(page: dict) -> str:
    href = BASE + page["slug"].strip("/") + "/"
    img = ""
    if page.get("card_image"):
        size = image_size(SRC / "assets" / page["card_image"])
        dims = f' width="{size[0]}" height="{size[1]}"' if size else ""
        img = (f'\n          <img src="{BASE}assets/{page["card_image"]}" alt="{html.escape(page.get("card_alt", ""))}"'
               f'{dims} loading="lazy" decoding="async">')
    return (f'        <li class="card">\n'
            f'          <a class="card-link" href="{href}">{img}\n'
            f'            <span class="card-body">\n'
            f'              <span class="card-title">{html.escape(page["card_title"] or page["h1"])}</span>\n'
            f'              <span class="card-text">{html.escape(page.get("card", ""))}</span>\n'
            f'              <span class="card-meta">{html.escape(page.get("card_meta", ""))}</span>\n'
            f'            </span>\n'
            f'          </a>\n'
            f'        </li>')


def meta_line(meta: dict, words: int) -> str:
    bits = [f'Updated {UPDATED_HUMAN}', f'{words} words']
    if meta.get("kind") == "itinerary" and meta.get("days"):
        bits.insert(0, f'{meta["days"]} days')
    return '        <p class="page-meta">' + " · ".join(bits) + "</p>"


def render(page: dict, page_index: dict[str, dict], template: str) -> str:
    meta = page
    slug = meta["slug"]
    kwargs = {k: "" for k in NAV_KEYS.values()}
    nav = meta.get("nav", "")
    if nav in NAV_KEYS:
        kwargs[NAV_KEYS[nav]] = ' aria-current="page"'

    crumbs: list[tuple[str, str | None]] = [("Home", BASE)]
    if slug not in ("/", ""):
        segments = [s for s in slug.strip("/").split("/") if s]
        for i in range(len(segments) - 1):
            parent = "/" + "/".join(segments[: i + 1]) + "/"
            parent_page = page_index.get(parent)
            label = parent_page["crumb"] if parent_page and parent_page.get("crumb") else segments[i].replace("-", " ").title()
            # only link intermediate crumbs that are real pages
            crumbs.append((label, BASE + parent.strip("/") + "/" if parent_page else None))
        crumbs.append((meta.get("crumb") or meta["h1"], abs_url(slug)))

    faqs = extract_faq(meta["body"])
    body = meta["body"]
    body = re.sub(r"\{\{CARDS:([a-z]+)\}\}", lambda m: cards_block(m.group(1), page_index), body)
    body = wrap_tables(body)

    words = word_count(body)
    og_image = SITE_URL + "/assets/" + meta["og"] if meta.get("og") else SITE_URL + "/assets/og/default.jpg"
    og_alt = meta.get("og_alt", meta["title"])

    values = {
        "TITLE": html.escape(meta["title"]),
        "DESCRIPTION": html.escape(meta["description"]),
        "CANONICAL": abs_url(slug),
        "ROBOTS": meta.get("robots", "index, follow, max-image-preview:large"),
        "HREFLANG": hreflang_block(slug),
        "OG_TYPE": "article" if meta["kind"] in ("itinerary", "guide") else "website",
        "OG_TITLE": html.escape(meta.get("og_title", meta["title"])),
        "OG_IMAGE": og_image,
        "OG_IMAGE_ALT": html.escape(og_alt),
        "BASE": BASE,
        "H1": html.escape(meta["h1"]),
        "PAGE_META": "" if meta["kind"] == "home" else meta_line(meta, words),
        "BREADCRUMB": breadcrumb_html(crumbs),
        "HERO": hero_html(meta),
        "BODY": body,
        "JSONLD": jsonld_for(meta, crumbs, faqs),
        "SCRIPTS": scripts_html(meta),
        **kwargs,
    }
    out = template
    # two passes: page bodies may themselves contain placeholders such as {{BASE}}
    for _ in range(2):
        for key, value in values.items():
            out = out.replace("{{" + key + "}}", value)
    leftover = re.findall(r"\{\{[A-Z_]+", out)
    if leftover:
        raise SystemExit(f"{meta['source']}: unfilled placeholders {leftover}")
    meta["_words"] = words
    meta["_faqs"] = len(faqs)
    meta["_out"] = slug_to_out(slug)
    return out


def scripts_html(meta: dict) -> str:
    """Page scripts. The calculator ships its data inline so it works offline."""
    if meta.get("scripts") != "calculator":
        return ""
    data = (SRC / "data" / "costs.json").read_text(encoding="utf-8")
    return ('<script>window.VNT_COSTS = ' + data.strip() + ";</script>\n"
            '<script src="' + BASE + 'assets/js/calculator.js" defer></script>')


def wrap_tables(body: str) -> str:
    """Horizontal scroll container so wide tables stay usable on phones."""
    return re.sub(r"<table([^>]*)>(.*?)</table>",
                  r'<div class="table-wrap"><table\1>\2</table></div>',
                  body, flags=re.S | re.I)


def hreflang_block(slug: str) -> str:
    """Single-language today; phase 2 adds /ko/ /ja/ /zh/ siblings here."""
    if len(LOCALES) == 1:
        return f'<link rel="alternate" hreflang="en" href="{abs_url(slug)}">\n<link rel="alternate" hreflang="x-default" href="{abs_url(slug)}">'
    lines = [f'<link rel="alternate" hreflang="{loc}" href="{abs_url(slug)}">' for loc in LOCALES]
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{abs_url(slug)}">')
    return "\n".join(lines)


def cards_block(kind: str, page_index: dict[str, dict]) -> str:
    items = [p for p in page_index.values() if p.get("kind") == kind and p.get("card")]
    items.sort(key=lambda p: int(p.get("order", 50)))
    if not items:
        return ""
    return '        <ul class="cards">\n' + "\n".join(card_html(p) for p in items) + "\n        </ul>"


# --------------------------------------------------------------------------- #
# sitemap / robots
# --------------------------------------------------------------------------- #
def write_sitemap(pages: list[dict]) -> None:
    urls = [p for p in pages if p["slug"] != "/404.html" and "noindex" not in p.get("robots", "")]
    urls.sort(key=lambda p: (p["slug"] != "/", p["slug"]))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in urls:
        priority = "1.0" if p["slug"] in ("/", "") else ("0.8" if p["kind"] in ("itinerary", "guide", "tool") else "0.6")
        lines += ["  <url>",
                  f"    <loc>{abs_url(p['slug'])}</loc>",
                  f"    <lastmod>{UPDATED_ISO}</lastmod>",
                  "    <changefreq>monthly</changefreq>",
                  f"    <priority>{priority}</priority>",
                  "  </url>"]
    lines.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_robots() -> None:
    (OUT / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n\nSitemap: " + SITE_URL + "/sitemap.xml\n", encoding="utf-8")


def copy_assets() -> None:
    target = OUT / "assets"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(SRC / "assets", target)
    (OUT / "data").mkdir(exist_ok=True)
    shutil.copy(SRC / "data" / "costs.json", OUT / "data" / "costs.json")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> None:
    pages = [parse_page(p) for p in sorted(PAGES_DIR.glob("*.html"))]
    page_index = {p["slug"]: p for p in pages}
    template = (SRC / "templates" / "layout.html").read_text(encoding="utf-8")
    OUT.mkdir(exist_ok=True)

    rendered: list[tuple[dict, str]] = [(p, render(p, page_index, template)) for p in pages]
    for meta, out_html in rendered:
        meta["_out"].parent.mkdir(parents=True, exist_ok=True)
        meta["_out"].write_text(out_html, encoding="utf-8")

    write_sitemap(pages)
    write_robots()
    copy_assets()

    print(f"Built {len(pages)} pages into {OUT}")
    if "--check" in sys.argv:
        report(pages, rendered)


def report(pages: list[dict], rendered: list[tuple[dict, str]]) -> None:
    print("\n=== QA report ===")
    problems = 0
    for meta, out_html in sorted(rendered, key=lambda r: r[0]["slug"]):
        slug = meta["slug"]
        issues = []
        if len(meta["title"]) > 60:
            issues.append(f"title {len(meta['title'])} chars")
        if len(meta["description"]) > 155:
            issues.append(f"description {len(meta['description'])} chars")
        if len(re.findall(r"<h1", out_html)) != 1:
            issues.append("h1 count != 1")
        links = len(re.findall(r'href="https://vibevietnamtour\.com', out_html))
        if links > 3:
            issues.append(f"{links} main-site links")
        if meta.get("hero") and not meta.get("hero_alt"):
            issues.append("hero without alt")
        for img in re.findall(r"<img[^>]+>", out_html):
            if 'alt="' not in img:
                issues.append("img without alt")
            if 'width=' not in img and 'loading="lazy"' not in img:
                issues.append("img without dimensions")
        problems += len(issues)
        status = "OK " if not issues else "!! "
        print(f"{status}{slug:<52} words={meta['_words']:<5} faq={meta['_faqs']} main-links={links}"
              + ("  -> " + ", ".join(issues) if issues else ""))
    print(f"\n{problems} issue(s) found")


if __name__ == "__main__":
    main()
