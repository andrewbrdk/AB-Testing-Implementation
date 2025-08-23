import random
import asyncio
import argparse
from collections import Counter
from math import sqrt
from playwright.async_api import async_playwright
import aiohttp

BASE_URL = "http://127.0.0.1:5000"
CLICK_PROBS = {
    'Moon': 0.1,
    'Mars': 0.2
}

MAX_CONCURRENT = 30
SEM = asyncio.Semaphore(MAX_CONCURRENT)

async def simulate_visit(browser):
    async with SEM:
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(BASE_URL)
        moon_mars_group = None
        await page.wait_for_selector("h1")
        moon_mars_h1 = await page.query_selector("h1")
        if moon_mars_h1:
            h = await moon_mars_h1.text_content()
            if "Moon" in h:
                moon_mars_group = "Moon"
            elif "Mars" in h:
                moon_mars_group = "Mars"
        white_gold_group = None
        await page.wait_for_selector("button")
        white_gold_btn = await page.query_selector("button")
        if white_gold_btn:
            classes = await white_gold_btn.get_attribute("class")
            if classes is None:
                white_gold_group = "White"
            elif "gold" in classes.split():
                white_gold_group = "Gold"
        if random.random() < CLICK_PROBS.get(moon_mars_group):
            await page.click("button")
            await page.wait_for_load_state('load')
        await page.close()
        await context.close()
        return moon_mars_group, white_gold_group

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
    if events is None:
        return None, None
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

async def check_split_independence(exp1, exp2):
    exps = await fetch_experiments()
    if exps is None:
        return
    exp1_split = exps.get(exp1, {}).get('groups')
    exp1_split = {k: v / sum(exp1_split.values()) for k, v in exp1_split.items()}
    exp2_split = exps.get(exp2, {}).get('groups')
    exp2_split = {k: v / sum(exp2_split.values()) for k, v in exp2_split.items()}
    expected_split = {}
    for g1, s1 in exp1_split.items():
        for g2, s2 in exp2_split.items():
            expected_split[(g1, g2)] = s1 * s2
    events = await fetch_events()
    if events is None:
        return
    device_groups = {}
    for e in events:
        if e.get("event") == "exp_groups":
            device_groups[e.get("deviceId")] = {
                exp1: e["params"].get(exp1).get('group'),
                exp2: e["params"].get(exp2).get('group')
            }
    split = Counter()
    for d in device_groups.values():
        split[(d[exp1], d[exp2])] += 1
    total = sum(split.values())
    print(f"Split Independence {exp1}/{exp2}:")
    for g in sorted(split):
        print(f'{g}: {split[g] / total * 100:.2f}%, independence {expected_split[g] * 100:.2f}%')

async def main():
    parser = argparse.ArgumentParser(description="Simulate A/B test visits")
    parser.add_argument(
        "-n", "--num-visits", type=int, default=1000,
        help="Number of visits to simulate (default: 1000)"
    )
    args = parser.parse_args()
    N = args.num_visits

    moon_mars_counts = Counter()
    white_gold_counts = Counter()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        t = [simulate_visit(browser) for i in range(N)]
        results = await asyncio.gather(*t)
        for moon_mars_group, white_gold_group in results:
            moon_mars_counts[moon_mars_group] += 1
            if white_gold_group is not None:
                white_gold_counts[white_gold_group] += 1
        await browser.close()

    if moon_mars_counts:
        print("Moon/Mars Exp Split:")
        for group in sorted(moon_mars_counts):
            part = (moon_mars_counts[group] / N) * 100
            print(f"Group {group}: {moon_mars_counts[group]} visits ({part:.2f}%)")
        print("")
    if white_gold_counts:
        print("White/Gold Exp Split:")
        for group in sorted(white_gold_counts):
            part = (white_gold_counts[group] / N) * 100
            print(f"Group {group}: {white_gold_counts[group]} visits ({part:.2f}%)")
        print("")

    exp_name = "moon_mars"
    visits, clicks = await count_exp_visits_clicks(exp_name)
    if visits is None:
        return
    print("Moon/Mars Exp events:")
    for group in sorted(visits | clicks):
        v, c = visits[group], clicks[group]
        ctr, ci = ctr_ci(v, c)
        print(f"Group {group}: {v} visits, {c} clicks, Conv={ctr*100:.2f} +- {ci*100:.2f}%, Exact: {CLICK_PROBS.get(group)*100:.2f}%")
    print("")

    exps = await fetch_experiments()
    if exps is None or len(exps) == 1:
        return
    moon_mars_split = exps.get("moon_mars", {}).get('groups')
    total = sum(moon_mars_split.values())
    normalized = {k: v / total for k, v in moon_mars_split.items()}

    exp_name = "white_gold_btn"
    visits, clicks = await count_exp_visits_clicks(exp_name)
    print("White/Gold Exp events:")
    for group in sorted(visits | clicks):
        v, c = visits[group], clicks[group]
        ctr, ci = ctr_ci(v, c)
        expected_ctr = sum([normalized[g] * CLICK_PROBS[g] for g in normalized.keys()])
        print(f"Group {group}: {v} visits, {c} clicks, Conv={ctr*100:.2f} +- {ci*100:.2f}%, Exact: {expected_ctr*100:.2f}%")
    print("")

    await check_split_independence("moon_mars", "white_gold_btn")

if __name__ == "__main__":
    asyncio.run(main())
