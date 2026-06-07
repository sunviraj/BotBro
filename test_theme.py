import asyncio
from playwright.async_api import async_playwright
import os

async def test_theme():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            print("Opening Dashboard...")
            await page.goto("http://localhost:8080/index.html")
            
            print("Creating Bot...")
            await page.fill("#url-input", "https://example.com")
            await page.click("#create-btn")
            
            while "AI Online!" not in await page.inner_text("#status-text"):
                await asyncio.sleep(2)
            
            print("Bot Ready. Testing Theme Customization...")
            await asyncio.sleep(2)
            
            # 1. Change color to Red
            print("Changing color to Red (#FF0000)...")
            await page.fill("#theme-color-hex", "#FF0000")
            await page.evaluate("updateLivePreview()")
            
            # 2. Change name
            print("Changing name to 'Red Bot'...")
            await page.fill("#bot-display-name", "Red Bot")
            await page.evaluate("updateLivePreview()")
            
            # 3. Save
            print("Saving theme...")
            await page.click("#save-theme-btn")
            await asyncio.sleep(3)
            
            # 4. Verify mini preview
            bg = await page.evaluate("document.getElementById('mini-header').style.background")
            name = await page.inner_text("#mini-name")
            print(f"Mini Preview: Color={bg}, Name={name}")
            
            os.makedirs("screenshots", exist_ok=True)
            await page.screenshot(path="screenshots/theme_test.png", full_page=True)
            print("Screenshot saved to screenshots/theme_test.png")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_theme())
