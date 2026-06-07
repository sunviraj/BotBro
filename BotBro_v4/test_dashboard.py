import asyncio
from playwright.async_api import async_playwright
import os

async def test_dashboard():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            print("Opening Dashboard...")
            await page.goto("http://localhost:8080/index.html", wait_until="networkidle")
            
            print("Creating Bot for americanburgerbd.com...")
            await page.fill("#url-input", "https://americanburgerbd.com/")
            await page.click("#create-btn")
            
            # Wait for progress
            for i in range(10):
                await asyncio.sleep(5)
                status = await page.inner_text("#status-text")
                percent = await page.inner_text("#percent-text")
                print(f"Status: {status} ({percent})")
                if "Ready" in status:
                    break
            
            os.makedirs("screenshots", exist_ok=True)
            path = "screenshots/dashboard_success.png"
            await page.screenshot(path=path, full_page=True)
            print(f"Dashboard success screenshot saved to {path}")
            
            # Extract bot ID from embed code
            code = await page.inner_text("#embed-code")
            print(f"Embed Code: {code}")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_dashboard())
