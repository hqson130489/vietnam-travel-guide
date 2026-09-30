#!/usr/bin/env python3
"""Browser tests against the local preview server (Playwright).

Checks every page for load errors, a single h1, loaded images, no horizontal
overflow on a phone viewport, plus the budget calculator's arithmetic.
"""
from __future__ import annotations

import asyncio
import sys

from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8099/vietnam-travel-guide"
PAGES = [
    "/", "/itineraries/", "/itineraries/5-days-north-vietnam/",
    "/itineraries/7-days-north-to-central/", "/itineraries/10-days-vietnam-north-to-south/",
    "/guides/", "/guides/best-time-to-visit-vietnam/", "/guides/getting-around-vietnam/",
    "/guides/vietnam-visa-for-tourists/", "/tools/budget-calculator/", "/about/", "/404.html",
]
failures: list[str] = []


def check(ok: bool, message: str) -> None:
    print(("OK   " if ok else "FAIL ") + message)
    if not ok:
        failures.append(message)


async def run() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        desktop = await browser.new_context(viewport={"width": 1280, "height": 900})
        phone = await browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)

        print("--- desktop pass ---")
        for path in PAGES:
            page = await desktop.new_page()
            errors: list[str] = []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            resp = await page.goto(BASE + path, wait_until="load")
            h1 = await page.locator("h1").count()
            imgs = await page.eval_on_selector_all(
                "img", "els => els.map(e => ({src: e.currentSrc, w: e.naturalWidth, alt: e.alt}))")
            broken = [i["src"] for i in imgs if i["w"] == 0]
            no_alt = [i["src"] for i in imgs if not i["alt"]]
            problems = []
            if resp is None or resp.status != 200:
                problems.append(f"status {resp.status if resp else 'none'}")
            if h1 != 1:
                problems.append(f"h1={h1}")
            if broken:
                problems.append(f"broken images {broken}")
            if no_alt:
                problems.append(f"missing alt {no_alt}")
            if errors:
                problems.append(f"console errors {errors[:2]}")
            check(not problems, f"{path:46} {'; '.join(problems) if problems else 'ok'}")
            await page.close()

        print("\n--- phone pass (390x844): no horizontal overflow ---")
        for path in PAGES:
            page = await phone.new_page()
            await page.goto(BASE + path, wait_until="load")
            overflow = await page.evaluate(
                "() => document.documentElement.scrollWidth - window.innerWidth")
            nav_visible = await page.locator(".site-nav a").first.is_visible()
            check(overflow <= 1 and nav_visible,
                  f"{path:46} overflow={overflow}px nav_visible={nav_visible}")
            await page.close()

        print("\n--- budget calculator ---")
        page = await desktop.new_page()
        await page.goto(BASE + "/tools/budget-calculator/", wait_until="load")
        await page.wait_for_selector(".calc-total .value")

        async def total() -> str:
            return (await page.locator(".calc-total .value").inner_text()).strip()

        got = await total()
        check(got == "$1,649–$3,233", f"defaults (10 nights, 2 people, mid-range, 3 cities): {got} "
                                      f"expected $1,649–$3,233")

        await page.fill("#days", "5")
        await page.fill("#travelers", "1")
        await page.check('input[name="style"][value="budget"]')
        for city in ["hoian", "hcmc"]:
            await page.uncheck(f'input[name="city"][value="{city}"]')
        got = await total()
        check(got == "$221–$440", f"5 nights, 1 person, budget, Hanoi only: {got} expected $221–$440")

        rows = await page.locator("#calc-output tbody tr").count()
        check(rows == 7, f"breakdown renders 6 categories + total row: {rows} rows")

        await page.click('button[type="reset"]')
        await page.wait_for_timeout(150)
        got = await total()
        check(got == "$1,649–$3,233", f"reset restores defaults: {got}")

        text = await page.locator("#calc-output").inner_text()
        check("September 2026" in text, "estimate is dated in the output")

        print("\n--- navigation ---")
        page2 = await desktop.new_page()
        await page2.goto(BASE + "/", wait_until="load")
        await page2.click('.site-nav a:has-text("Itineraries")')
        await page2.wait_for_load_state("load")
        check(page2.url.endswith("/itineraries/"), f"nav click lands on {page2.url}")
        await page2.click('.cards .card-link >> nth=0')
        await page2.wait_for_load_state("load")
        check("/itineraries/" in page2.url and page2.url.count("/") > 5,
              f"first itinerary card opens {page2.url}")
        crumbs = await page2.locator(".breadcrumb a, .breadcrumb span").count()
        check(crumbs >= 3, f"breadcrumb rendered with {crumbs} items")

        await browser.close()

    print(f"\n{'ALL BROWSER CHECKS PASSED' if not failures else str(len(failures)) + ' CHECK(S) FAILED'}")
    sys.exit(1 if failures else 0)


asyncio.run(run())
