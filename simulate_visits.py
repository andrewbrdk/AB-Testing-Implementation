import random
import asyncio
import argparse
from collections import Counter
from playwright.async_api import async_playwright
import aiohttp

BASE_URL = "http://127.0.0.1:5000"
CLICK_PROBS = {
    'A': 0.1,
    'B': 0.2
}

async def simulate_visit(browser):
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(BASE_URL)
    heading = await page.text_content("h3")
    if heading and "Variant A" in heading:
        button_group = "A"
    elif heading and "Variant B" in heading:
        button_group = "B"
    else:
        button_group = None
    headline = await page.text_content("#headline-container h2")
    if headline and "Future" in headline:
        headline_group = "Future"
    elif headline and "Journey" in headline:
        headline_group = "Journey"
    else:
        headline_group = None
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
        #todo: parallelize
        for _ in range(N):
            button_group, headline_group = await simulate_visit(browser)
            button_counts[button_group] += 1
            headline_counts[headline_group] += 1
        await browser.close()

    print("Button Test Split:")
    for group in sorted(button_counts):
        pct = (button_counts[group] / N) * 100
        print(f"Group {group}: {button_counts[group]} visits ({pct:.2f}%)")

    print("Headline Test Split:")
    for group in sorted(headline_counts):
        pct = (headline_counts[group] / N) * 100
        print(f"Group {group}: {headline_counts[group]} visits ({pct:.2f}%)")

    events = await fetch_events()
    if events is not None:
        print("Event Stats from /events:")
        visits = Counter(e.get("exp_group") for e in events if e.get("event") == "pageview")
        clicks = Counter(e.get("exp_group") for e in events if e.get("event") == "button_click")
        for group in sorted(visits | clicks):
            ctr = (clicks[group] / visits[group] * 100) if visits[group] else 0
            print(f"Group {group}: {visits[group]} visits, {clicks[group]} clicks, CTR={ctr:.2f}%")

if __name__ == "__main__":
    asyncio.run(main())
