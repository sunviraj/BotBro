import asyncio
from playwright.async_api import async_playwright
import os

async def test_dashboard_v2():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            print("Opening Dashboard...")
            await page.goto("http://localhost:8080/index.html", wait_until="networkidle")
            
            # 1. Test Navigation
            print("Testing Analytics Nav...")
            await page.click("text=Analytics")
            await asyncio.sleep(1)
            os.makedirs("screenshots", exist_ok=True)
            await page.screenshot(path="screenshots/dashboard_analytics.png")
            
            # 2. Go back and Create Bot
            print("Returning to Dashboard...")
            await page.click("text=Dashboard")
            await page.fill("#url-input", "https://americanburgerbd.com/")
            await page.click("#create-btn")
            
            # Wait for completion
            print("Waiting for Bot creation...")
            while True:
                await asyncio.sleep(5)
                status = await page.inner_text("#status-text")
                if "Complete!" in status:
                    break
            
            # 3. Test Preview
            print("Testing Bot Preview...")
            await page.fill("#preview-input", "Hi, what's on the menu?")
            await page.click("#preview-send")
            await asyncio.sleep(8) # Wait for AI
            
            await page.screenshot(path="screenshots/dashboard_preview_success.png", full_page=True)
            print("Success screenshots saved.")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_dashboard_v2())
