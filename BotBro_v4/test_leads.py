import asyncio
from playwright.async_api import async_playwright
import os

async def test_leads():
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
            
            print("Bot Ready. Enabling Lead Capture...")
            await page.check("#lead-capture-toggle")
            await page.click("#save-theme-btn")
            await asyncio.sleep(2)
            
            # 1. Chat and provide email
            print("Testing Lead Capture in Preview...")
            await page.fill("#preview-input", "My email is test@example.com")
            await page.click("#preview-send")
            await asyncio.sleep(3)
            
            # 2. Check Leads tab
            print("Switching to Leads tab...")
            await page.click('[data-target="leads-section"]')
            await asyncio.sleep(2)
            
            leads_html = await page.inner_html("#leads-table-body")
            if "test@example.com" in leads_html:
                print("SUCCESS: Lead captured and visible in dashboard!")
            else:
                print("FAILURE: Lead not found in table.")
            
            os.makedirs("screenshots", exist_ok=True)
            await page.screenshot(path="screenshots/leads_test.png", full_page=True)
            print("Screenshot saved to screenshots/leads_test.png")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_leads())
