import asyncio
from playwright.async_api import async_playwright
import os

async def test_auth():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Handle Alerts
        page.on("dialog", lambda dialog: dialog.accept())

        try:
            print("Opening Dashboard...")
            await page.goto("http://localhost:8080/index.html")
            await page.wait_for_url("**/login.html")
            print("SUCCESS: Redirected to login.")
            
            # 1. Sign Up
            print("Going to Signup...")
            await page.goto("http://localhost:8080/signup.html")
            await page.fill("#email", "test2@user.com")
            await page.fill("#password", "password123")
            await page.click("#submit-btn")
            await page.wait_for_url("**/login.html")
            print("Signup complete and redirected to login.")
            
            # 2. Login
            print("Logging in...")
            await page.fill("#email", "test2@user.com")
            await page.fill("#password", "password123")
            await page.click("#submit-btn")
            await page.wait_for_url("**/index.html")
            
            print("SUCCESS: Logged in to dashboard.")
            user_email = await page.inner_text("#user-email")
            print(f"Logged in as: {user_email}")
            
            # 3. Create Bot
            print("Testing bot creation...")
            await page.fill("#url-input", "https://example.com")
            await page.click("#create-btn")
            await page.wait_for_selector("#status-section", state="visible")
            status = await page.inner_text("#status-text")
            print(f"Status: {status}")
            
            # 4. Logout
            print("Logging out...")
            await page.click("#logout-btn")
            await page.wait_for_url("**/login.html")
            print("SUCCESS: Logged out.")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_auth())
