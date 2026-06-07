import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
import os

class Scraper:
    def __init__(self):
        self.browser = None
        self.context = None

    async def start(self):
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

    async def stop(self):
        await self.browser.close()
        await self.pw.stop()

    async def scrape_url(self, url):
        print(f"Scraping: {url}...")
        page = await self.context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            # Scroll to trigger lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove scripts, styles, and common nav/footer elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe', 'noscript']):
                tag.decompose()
            
            # Extract text from meaningful tags
            text_blocks = []
            for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'span', 'div']):
                text = tag.get_text(strip=True)
                if len(text) > 20: # Filter out short noise
                    text_blocks.append(text)
            
            full_text = "\n".join(text_blocks)
            return full_text
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None
        finally:
            await page.close()

async def main():
    url = "https://www.lego.com/en-us"
    scraper = Scraper()
    await scraper.start()
    text = await scraper.scrape_url(url)
    await scraper.stop()
    
    if text:
        os.makedirs("data", exist_ok=True)
        with open("data/scraped_content.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Successfully scraped {len(text)} characters.")
    else:
        print("Scraping failed.")

if __name__ == "__main__":
    asyncio.run(main())
