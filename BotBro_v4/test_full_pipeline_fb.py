import asyncio
from playwright.async_api import async_playwright
import os

async def test_full_pipeline_fb():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            print("Opening Dashboard...")
            await page.goto("http://localhost:8080/index.html", wait_until="networkidle")
            
            # 1. Fill Website and Facebook URL
            print("Creating Bot with Website & Facebook...")
            await page.fill("#url-input", "https://americanburgerbd.com/")
            await page.fill("#fb-url-input", "https://www.facebook.com/americanburgerbd")
            await page.click("#create-btn")
            
            # 2. Wait for completion (status polling)
            print("Waiting for bot creation...")
            while True:
                await asyncio.sleep(5)
                status_text = await page.inner_text("#status-text")
                percent = await page.inner_text("#percent-text")
                print(f"Status: {status_text} ({percent})")
                if "AI Online!" in status_text:
                    break
                if "error" in status_text.lower():
                    print("Error during creation!")
                    break
            
            # 3. Save Bot
            page.on("dialog", lambda dialog: dialog.accept())
            await page.click("#save-bot-btn")
            await asyncio.sleep(1)
            
            # 4. Verify in My Bots (check for FB badge)
            await page.click("text=My Bots")
            await asyncio.sleep(1)
            
            os.makedirs("screenshots", exist_ok=True)
            await page.screenshot(path="screenshots/fb_integration_success.png", full_page=True)
            print("Screenshot saved to screenshots/fb_integration_success.png")
            
            # 5. Test Query (Ask about something from FB)
            print("Testing Query with FB context...")
            await page.click("text=Dashboard")
            await page.fill("#preview-input", "Tell me about your Valentine's Day couple set offer.")
            await page.click("#preview-send")
            await asyncio.sleep(10) # Wait for AI
            
            await page.screenshot(path="screenshots/fb_query_test.png", full_page=True)
            print("Query test screenshot saved to screenshots/fb_query_test.png")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_full_pipeline_fb())
