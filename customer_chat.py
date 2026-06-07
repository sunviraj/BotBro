import asyncio
from playwright.async_api import async_playwright
import os

async def customer_chat():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            print("Opening SiteGPT-Plus Demo...")
            await page.goto("http://localhost:8080/index.html", wait_until="networkidle")
            await asyncio.sleep(2)
            
            # Open chat
            await page.click("#sitegpt-button")
            await asyncio.sleep(1)
            
            questions = [
                "Do you deliver to Banasree?",
                "What is your most expensive burger?",
                "Do you have anything for someone who loves spicy food?"
            ]
            
            for q in questions:
                print(f"Customer: {q}")
                await page.fill("#sitegpt-query-input", q)
                await page.click("#sitegpt-send-btn")
                await asyncio.sleep(10) # Wait for AI
            
            os.makedirs("screenshots", exist_ok=True)
            path = "screenshots/customer_chat_flow.png"
            await page.screenshot(path=path, full_page=True)
            print(f"Customer session saved to {path}")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(customer_chat())
