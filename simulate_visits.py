import random
import asyncio
import argparse
from collections import Counter
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:5000"
CLICK_PROBS = {
    'A': 0.1,
    'B': 0.2
}

async def simulate_visit(context):
    page = await context.new_page()
    await page.goto(BASE_URL)
    cookies = await context.cookies()
    exp_group = next((c["value"] for c in cookies if c["name"] == "exp_group"), None)
    if not exp_group:
        heading = await page.text_content("h3")
        if heading and "Variant A" in heading:
            exp_group = "A"
        elif heading and "Variant B" in heading:
            exp_group = "B"
        else:
            exp_group = None
    if random.random() < CLICK_PROBS[exp_group]:
        await page.click("button")
        await page.wait_for_load_state('load')
    await page.close()
    return exp_group

async def main():
    parser = argparse.ArgumentParser(description="Simulate A/B test visits")
    parser.add_argument(
        "-n", "--num-visits", type=int, default=1000,
        help="Number of visits to simulate (default: 1000)"
    )
    args = parser.parse_args()
    N = args.num_visits
    counts = Counter()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for _ in range(N):
            context = await browser.new_context()
            group = await simulate_visit(context)
            counts[group] += 1
            await context.close()
        await browser.close()
    print("A/B Test Split:")
    for group, count in counts.items():
        pct = (count / N) * 100
        print(f"Group {group}: {count} visits ({pct:.2f}%)")

if __name__ == "__main__":
    asyncio.run(main())
