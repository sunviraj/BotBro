import asyncio
from playwright.async_api import async_playwright
import os

async def shot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Opening Dashboard...")
        await page.goto("http://localhost:8080/index.html")
        
        print("Creating Bot...")
        await page.fill("#url-input", "https://example.com")
        await page.click("#create-btn")
        
        while True:
            await asyncio.sleep(2)
            status = await page.inner_text("#status-text")
            if "AI Online!" in status:
                break
        
        print("Waiting for suggestions...")
        await asyncio.sleep(10)
        
        os.makedirs("screenshots", exist_ok=True)
        await page.screenshot(path="screenshots/suggestions_final.png", full_page=True)
        print("Screenshot saved to screenshots/suggestions_final.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(shot())
