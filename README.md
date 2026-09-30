# Vietnam Travel Guide

Practical, original planning content for a first trip to Vietnam: three day-by-day
itineraries, a browser-based trip budget calculator, and guides to timing, transport
and paperwork. Written by the team at [Vibe Vietnam Tour](https://vibevietnamtour.com/)
in Hanoi, and written separately from that site — nothing here is copied from it.

**Read it online: <https://hqson130489.github.io/vietnam-travel-guide/>**

## What is in it

| Section | What it covers |
|---|---|
| [Itineraries](https://hqson130489.github.io/vietnam-travel-guide/itineraries/) | 5, 7 and 10-day routes through the north, centre and south, each with travel times, where to stay by price band and a three-tier budget table |
| [Budget calculator](https://hqson130489.github.io/vietnam-travel-guide/tools/budget-calculator/) | Pick your nights, group size, comfort level and stops to get a cost breakdown — runs entirely in your browser |
| [Guides](https://hqson130489.github.io/vietnam-travel-guide/guides/) | Best time to visit (region by region), getting around (planes, trains, buses, ride-hailing) and how the tourist visa process works |
| [About](https://hqson130489.github.io/vietnam-travel-guide/about/) | Who writes the guide, how the prices are checked and how to send a correction |

## How the site is built

Plain static HTML, CSS and vanilla JavaScript — no framework, no build step required to
edit a page, no tracking scripts and no cookies.

```
src/                 source of truth
  pages/*.html       one file per page: front matter + body HTML
  templates/         shared layout (head, header, footer)
  assets/            css, js, images (WebP, plus 1200x630 OG JPEGs)
  data/costs.json    budget-calculator cost ranges
tools/
  build.py           renders src/pages -> docs/ and writes sitemap.xml + robots.txt
  make_images.py     regenerates the WebP/OG image set from the main site's photo library
  qa.py              link, metadata, JSON-LD, sitemap and originality checks
  e2e.py             Playwright checks (images, mobile overflow, calculator maths)
docs/                generated output, served by GitHub Pages
```

Rebuild after editing anything in `src/`:

```bash
python3 tools/build.py          # write docs/
python3 tools/build.py --check  # + SEO/QA report
python3 tools/qa.py             # acceptance checks
```

`docs/` is generated output and is committed because GitHub Pages serves it directly
(branch `main`, folder `/docs`).

## Prices and accuracy

Every money figure is a planning **estimate** in US dollars, reviewed in **September 2026**,
shown as a range rather than a single number. Nothing on the site is a quote, and nothing
is sponsored: no hotel, cruise or booking platform pays to be mentioned.

## License

- Written content (guide text, itineraries, page copy, `src/data/`): **CC BY 4.0** — see [`LICENSE`](LICENSE)
- Code (`tools/`, CSS, JavaScript): **MIT** — see [`LICENSE-CODE`](LICENSE-CODE)

The Vibe Vietnam Tour name, logo and photographs remain all rights reserved.

## Contact

Corrections and questions about the content: use the
[Vibe Vietnam Tour contact page](https://vibevietnamtour.com/pages/contact) and mention
"travel guide" so the message reaches the people who write these pages.
