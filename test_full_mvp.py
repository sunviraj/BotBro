import asyncio
import subprocess
import os
import time

async def test_total_mvp(url):
    print(f"🚀 Starting Total MVP Test for: {url}")
    
    # 1. Crawl
    print("--- Phase 1: Crawling ---")
    # We'll use the existing scraper.py but pass the URL as an argument or edit it
    with open("crawler/scraper.py", "r") as f:
        scraper_code = f.read()
    
    # Temporarily update the URL in scraper.py main
    new_scraper_code = scraper_code.replace('url = "https://americanburgerbd.com/"', f'url = "{url}"')
    with open("crawler/temp_scraper.py", "w") as f:
        f.write(new_scraper_code)
    
    process = subprocess.run(["venv/bin/python3", "crawler/temp_scraper.py"], capture_output=True, text=True)
    print(process.stdout)
    
    # 2. Vectorize
    print("--- Phase 2: Vectorizing ---")
    process = subprocess.run(["venv/bin/python3", "crawler/vectorizer.py"], capture_output=True, text=True)
    print(process.stdout)
    
    # 3. Restart Backend (not strictly necessary if it's already running and watching DB, but safe)
    print("--- Phase 3: Refreshing Knowledge ---")
    # Backend handles dynamic collection updates, so we just need to wait a bit
    time.sleep(2)
    
    # 4. Test Chat
    print("--- Phase 4: Chatting ---")
    test_questions = [
        "What categories of toys do you have?",
        "Do you have any LEGO sets?",
        "Where is your shop located?"
    ]
    
    # I'll use curl to test the API directly
    import httpx
    async with httpx.AsyncClient() as client:
        for q in test_questions:
            print(f"Q: {q}")
            response = await client.post("http://localhost:8000/query", json={"query": q}, timeout=30.0)
            data = response.json()
            print(f"A: {data['answer']}\n")

if __name__ == "__main__":
    # Target a new niche: Toy Store
    target_url = "https://www.lego.com/en-us"
    asyncio.run(test_total_mvp(target_url))
