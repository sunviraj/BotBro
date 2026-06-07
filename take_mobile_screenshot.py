import asyncio
from playwright.async_api import async_playwright

async def take_screenshot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Mobile viewport (iPhone 13)
        context = await browser.new_context(
            viewport={'width': 390, 'height': 844},
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
        )
        page = await context.new_page()
        
        # Screenshot landing page
        await page.goto("http://localhost:8080/index.html", wait_until="networkidle")
        await asyncio.sleep(2)
        await page.screenshot(path="screenshots/mobile_landing.png", full_page=True)
        
        # Screenshot dashboard
        await page.goto("http://localhost:8080/dashboard/index.html", wait_until="networkidle")
        await asyncio.sleep(2)
        await page.screenshot(path="screenshots/mobile_dashboard.png", full_page=True)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshot())
