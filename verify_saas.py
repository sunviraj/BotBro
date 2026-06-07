import asyncio
from playwright.async_api import async_playwright
import os

async def verify_saas_features():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            print("Opening Dashboard...")
            await page.goto("http://localhost:8080/index.html", wait_until="networkidle")
            
            # 1. Create a bot
            print("Creating Bot for americanburgerbd.com...")
            await page.fill("#url-input", "https://americanburgerbd.com/")
            await page.click("#create-btn")
            
            # Wait for completion
            print("Waiting for Bot creation...")
            while True:
                await asyncio.sleep(5)
                status = await page.inner_text("#status-text")
                if "Online!" in status:
                    break
            
            # 2. Click Save
            print("Saving Bot to Library...")
            # Handle alert
            page.on("dialog", lambda dialog: dialog.accept())
            await page.click("#save-bot-btn")
            await asyncio.sleep(1)
            
            # 3. Check My Bots
            print("Checking My Bots Library...")
            await page.click("text=My Bots")
            await asyncio.sleep(1)
            
            os.makedirs("screenshots", exist_ok=True)
            path = "screenshots/my_bots_library.png"
            await page.screenshot(path=path, full_page=True)
            print(f"Library screenshot saved to {path}")
            
            # 4. Test Chat UI in Preview (go back to Dashboard)
            print("Testing Chat UI...")
            await page.click("text=Dashboard")
            await page.fill("#preview-input", "Do you have any chicken burgers?")
            await page.click("#preview-send")
            await asyncio.sleep(8)
            
            path_chat = "screenshots/fixed_chat_ui.png"
            await page.screenshot(path=path_chat, full_page=True)
            print(f"Fixed Chat UI screenshot saved to {path_chat}")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_saas_features())
