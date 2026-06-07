import asyncio
from crawler.scraper import FacebookScraper
import os

async def test_fb():
    fb_url = "https://www.facebook.com/americanburgerbd" # Public business page
    scraper = FacebookScraper()
    await scraper.start()
    print(f"Testing scraper on {fb_url}...")
    text = await scraper.scrape_page(fb_url)
    await scraper.stop()
    
    if text:
        print("\n--- SCRAPED CONTENT ---")
        print(text[:1000] + "...") # Show first 1000 chars
        print("\n--- END ---")
        
        os.makedirs("data", exist_ok=True)
        with open("data/test_fb_output.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Saved full output to data/test_fb_output.txt")
    else:
        print("Scraping failed.")

if __name__ == "__main__":
    asyncio.run(test_fb())
