import asyncio
from playwright.async_api import async_playwright
import os

async def test_suggestions():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            print("Opening Dashboard...")
            await page.goto("http://localhost:8080/index.html", wait_until="networkidle")
            
            # 1. Create a bot
            print("Creating Bot for americanburgerbd.com...")
            await page.fill("#url-input", "https://americanburgerbd.com/")
            await page.fill("#fb-url-input", "https://www.facebook.com/americanburgerbd")
            await page.click("#create-btn")
            
            # Wait for completion
            print("Waiting for Bot creation...")
            while True:
                await asyncio.sleep(5)
                status = await page.inner_text("#status-text")
                if "AI Online!" in status:
                    break
            
            # 2. Check for suggestions
            print("Checking for AI Suggestions...")
            await asyncio.sleep(5) # Wait for suggestions to load
            pills = await page.query_selector_all(".suggestion-pill")
            print(f"Found {len(pills)} suggestion pills.")
            
            for i, pill in enumerate(pills):
                text = await pill.inner_text()
                print(f"Pill {i+1}: {text}")
            
            # 3. Click a suggestion
            if pills:
                print(f"Clicking suggestion: {await pills[0].inner_text()}")
                await pills[0].click()
                await asyncio.sleep(8)
                
                os.makedirs("screenshots", exist_ok=True)
                await page.screenshot(path="screenshots/suggestions_test.png", full_page=True)
                print("Screenshot saved to screenshots/suggestions_test.png")
            
            # 4. Test Refresh
            print("Testing Refresh...")
            await page.click(".refresh-btn")
            await asyncio.sleep(5)
            new_pills = await page.query_selector_all(".suggestion-pill")
            print(f"Found {len(new_pills)} new suggestion pills after refresh.")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_suggestions())
