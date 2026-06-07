import asyncio
from playwright.async_api import async_playwright
import os

async def take_screenshot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            print("Opening http://localhost:8080/index.html...")
            await page.goto("http://localhost:8080/index.html", wait_until="networkidle")
            await asyncio.sleep(2)
            
            # Click the bubble to open chat
            await page.click("#sitegpt-button")
            await asyncio.sleep(1)
            
            # Type a question
            await page.fill("#sitegpt-query-input", "What kind of beef burgers do you have?")
            await page.click("#sitegpt-send-btn")
            
            # Wait for response
            print("Waiting for AI response...")
            await asyncio.sleep(15)
            
            os.makedirs("screenshots", exist_ok=True)
            path = "screenshots/chat_demo.png"
            await page.screenshot(path=path, full_page=True)
            print(f"Screenshot saved to {path}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshot())
