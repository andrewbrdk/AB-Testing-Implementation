import random
import asyncio
import argparse
from collections import Counter
from math import sqrt
from playwright.async_api import async_playwright
import aiohttp

BASE_URL = "http://127.0.0.1:5000"
CLICK_PROBS = {
    'A': 0.1,
    'B': 0.2
}

MAX_CONCURRENT = 50
SEM = asyncio.Semaphore(MAX_CONCURRENT)

async def simulate_visit(browser):
    async with SEM:
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(BASE_URL)
        button_group = None
        button_exp_h3 = await page.query_selector("h3")
        if button_exp_h3:
            h = await button_exp_h3.text_content()
            if "Variant A" in h:
                button_group = "A"
            elif "Variant B" in h:
                button_group = "B"
        headline_group = None
        headline_exp_h2 = await page.query_selector("#headline-container h2")
        if headline_exp_h2:
            h = await headline_exp_h2.text_content()
            if "Future" in h:
                headline_group = "Future"
            elif "Journey" in h:
                headline_group = "Journey"
        if random.random() < CLICK_PROBS.get(button_group):
            await page.click("button")
            await page.wait_for_load_state('load')
        await page.close()
        await context.close()
        return button_group, headline_group

async def fetch_events():
    url = f"{BASE_URL}/events"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                resp.raise_for_status()
                return await resp.json()
    except Exception as e:
        return None

async def fetch_experiments():
    url = f"{BASE_URL}/api/experiments"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                resp.raise_for_status()
                return await resp.json()
    except Exception as e:
        return None

async def count_exp_visits_clicks(exp_name):
    visits, clicks = Counter(), Counter()
    events = await fetch_events()
    if events is not None:
        device_groups = {}
        for e in events:
            if e.get("event") == "exp_groups":
                device_groups[e.get("deviceId")] = e["params"].get(exp_name).get('group')
        for e in events:
            group = device_groups.get(e.get('deviceId')) or e.get("exp_group")
            if e.get("event") == "pageview":
                visits[group] += 1
            elif e.get("event") == "button_click":
                clicks[group] += 1
    return visits, clicks

def ctr_ci(v, c):
    ctr = (c / v) if v > 0 else None
    ci = 2 * sqrt(ctr * (1 - ctr) / v) if v > 0 else None
    return ctr, ci

async def main():
    parser = argparse.ArgumentParser(description="Simulate A/B test visits")
    parser.add_argument(
        "-n", "--num-visits", type=int, default=1000,
        help="Number of visits to simulate (default: 1000)"
    )
    args = parser.parse_args()
    N = args.num_visits

    button_counts = Counter()
    headline_counts = Counter()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        t = [simulate_visit(browser) for i in range(N)]
        results = await asyncio.gather(*t)
        for button_group, headline_group in results:
            button_counts[button_group] += 1
            if headline_group is not None:
                headline_counts[headline_group] += 1
        await browser.close()

    if button_counts:
        print("Button Exp Split:")
        for group in sorted(button_counts):
            part = (button_counts[group] / N) * 100
            print(f"Group {group}: {button_counts[group]} visits ({part:.2f}%)")
    if headline_counts:
        print("Headline Exp Split:")
        for group in sorted(headline_counts):
            part = (headline_counts[group] / N) * 100
            print(f"Group {group}: {headline_counts[group]} visits ({part:.2f}%)")

    exp_name = "homepage_button_test"
    visits, clicks = await count_exp_visits_clicks(exp_name)
    if len(visits) == 0:
        return
    print(f"Button Exp /events:")
    for group in sorted(visits | clicks):
        v, c = visits[group], clicks[group]
        ctr, ci = ctr_ci(v, c)
        print(f"Group {group}: {v} visits, {c} clicks, Conv={ctr*100:.2f} +- {ci*100:.2f}%, Exact: {CLICK_PROBS.get(group)*100:.2f}%")

    exps = await fetch_experiments()
    if exps is None or len(exps) == 1:
        return
    button_split = exps.get("homepage_button_test", {}).get('groups')
    total = sum(button_split.values())
    normalized = {k: v / total for k, v in button_split.items()}

    exp_name = "headline_test"
    visits, clicks = await count_exp_visits_clicks(exp_name)
    print(f"Headline Exp /events:")
    for group in sorted(visits | clicks):
        v, c = visits[group], clicks[group]
        ctr, ci = ctr_ci(v, c)
        expected_ctr = sum([normalized[g] * CLICK_PROBS[g] for g in normalized.keys()])
        print(f"Group {group}: {v} visits, {c} clicks, Conv={ctr*100:.2f} +- {ci*100:.2f}%, Expected: {expected_ctr*100:.2f}%")

    #todo: check independence. use events
    #P(a & b) = p(a) * p(b)

if __name__ == "__main__":
    asyncio.run(main())
