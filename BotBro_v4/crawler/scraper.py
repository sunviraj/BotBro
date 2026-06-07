import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
import os
import re
from urllib.parse import urljoin, urlparse

class Scraper:
    def __init__(self):
        self.browser = None
        self.context = None

    async def start(self):
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'pw'):
            await self.pw.stop()

    def _extract_structured_text(self, soup, url=""):
        """
        Intelligent extraction that preserves product/service structure.
        Instead of dumping all text, we build a structured document.
        """
        text_parts = []

        # ── Page title as a strong signal ──
        title = soup.find('title')
        if title:
            text_parts.append(f"PAGE TITLE: {title.get_text(strip=True)}")

        # ── Heading hierarchy (H1-H4) with their nearby content ──
        for hx in soup.find_all(['h1', 'h2', 'h3', 'h4']):
            heading = hx.get_text(strip=True)
            if not heading or len(heading) < 2:
                continue
            text_parts.append(f"\n## {heading}")

            # Grab the next sibling paragraphs / list items right after this heading
            sibling = hx.find_next_sibling()
            for _ in range(6):  # grab up to 6 adjacent siblings
                if sibling is None:
                    break
                if sibling.name in ['h1', 'h2', 'h3', 'h4']:
                    break  # stop at the next heading
                sib_text = sibling.get_text(strip=True)
                if sib_text and len(sib_text) > 5:
                    text_parts.append(sib_text)
                sibling = sibling.find_next_sibling()

        # ── Standalone paragraphs ──
        for p in soup.find_all('p'):
            t = p.get_text(strip=True)
            if len(t) > 20:
                text_parts.append(t)

        # ── List items (often used for product features / menu items) ──
        for li in soup.find_all('li'):
            t = li.get_text(strip=True)
            if 5 < len(t) < 600:
                text_parts.append(f"• {t}")

        # ── Product / card containers ──
        # Look for elements with product-like classes/attributes
        product_selectors = [
            'article', '[class*="product"]', '[class*="item"]',
            '[class*="card"]', '[class*="menu"]', '[class*="service"]',
            '[class*="collection"]', '[class*="catalog"]', '[class*="price"]',
            '[data-product]', '[itemtype*="Product"]'
        ]
        seen_texts = set()
        for sel in product_selectors:
            for el in soup.select(sel):
                t = el.get_text(separator=' | ', strip=True)
                t = re.sub(r'\s+', ' ', t)
                if len(t) > 15 and t not in seen_texts:
                    seen_texts.add(t)
                    
                    # Extract image
                    img = el.find('img')
                    img_url = ""
                    if img and img.get('src'):
                        img_url = urljoin(url, img['src'])
                        
                    # Extract link
                    link = el.find('a', href=True)
                    link_url = ""
                    if link:
                        link_url = urljoin(url, link['href'])
                    
                    # Build string
                    item_str = f"PRODUCT/SERVICE: {t}"
                    if img_url:
                        item_str += f" | IMAGE: {img_url}"
                    if link_url:
                        item_str += f" | LINK: {link_url}"
                        
                    text_parts.append(item_str)

        # ── Price tags specifically ──
        for price_el in soup.select('[class*="price"], [class*="cost"], [class*="rate"], [class*="tk"], [class*="bdt"], [class*="taka"]'):
            t = price_el.get_text(strip=True)
            if t:
                text_parts.append(f"PRICE: {t}")

        # ── Meta description (very useful for business summary) ──
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            text_parts.insert(1, f"META DESCRIPTION: {meta_desc['content']}")

        return "\n".join(filter(None, text_parts))

    def _find_internal_links(self, soup, base_url, max_links=12):
        """Find internal links that likely contain product/service/menu/about info."""
        parsed_base = urlparse(base_url)
        base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"

        priority_keywords = [
            'product', 'shop', 'store', 'menu', 'item', 'catalog', 'collection',
            'service', 'about', 'portfolio', 'offer', 'package', 'price', 'pricing',
            'category', 'brand', 'range', 'shoe', 'cloth', 'food', 'tour', 'hotel',
            'course', 'class', 'event', 'book', 'rent', 'sell', 'buy'
        ]

        links = set()
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            # Resolve relative links
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)

            # Only same-domain links
            if parsed.netloc != parsed_base.netloc:
                continue
            # No anchors or mailto/tel
            if parsed.scheme not in ('http', 'https'):
                continue
            # No media files
            if re.search(r'\.(jpg|jpeg|png|gif|pdf|mp4|zip|exe)$', parsed.path, re.I):
                continue

            # Score by priority keywords in the URL path
            path_lower = parsed.path.lower()
            for kw in priority_keywords:
                if kw in path_lower:
                    links.add(full_url)
                    break

        # Also grab nav/menu links (high value regardless of URL)
        for a in soup.select('nav a, header a, .menu a, .nav a'):
            href = a.get('href', '').strip()
            if href:
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)
                if parsed.netloc == parsed_base.netloc and parsed.scheme in ('http', 'https'):
                    links.add(full_url)

        return list(links)[:max_links]

    async def scrape_url(self, url, crawl_depth=1):
        """
        Scrape a URL and optionally crawl important internal pages.
        crawl_depth=1 means: scrape homepage + discovered product/service pages.
        """
        all_texts = []
        visited = set()

        async def scrape_single(target_url, label=""):
            if target_url in visited:
                return None
            visited.add(target_url)
            print(f"Scraping: {target_url} {label}")

            page = await self.context.new_page()
            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
                # Scroll to trigger lazy loading
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                # Scroll back up to catch sticky nav
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(0.5)

                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')

                # Remove noisy structural elements
                for tag in soup(['script', 'style', 'iframe', 'noscript', 'svg', 'path']):
                    tag.decompose()

                return soup, content
            except Exception as e:
                print(f"Error scraping {target_url}: {e}")
                return None, None
            finally:
                await page.close()

        # ── Step 1: Scrape the main URL ──
        result = await scrape_single(url, "[main page]")
        if result is None or result[0] is None:
            return None

        main_soup, main_html = result
        main_text = self._extract_structured_text(main_soup, url)
        all_texts.append(f"=== PAGE: {url} ===\n{main_text}")

        # ── Step 2: Discover and crawl internal pages ──
        if crawl_depth > 0:
            internal_links = self._find_internal_links(main_soup, url, max_links=10)
            print(f"  Found {len(internal_links)} internal links to crawl: {internal_links[:5]}")

            for link in internal_links[:8]:  # Max 8 sub-pages
                result = await scrape_single(link, "[sub-page]")
                if result and result[0] is not None:
                    sub_soup, _ = result
                    sub_text = self._extract_structured_text(sub_soup, link)
                    if sub_text and len(sub_text) > 100:
                        all_texts.append(f"\n=== PAGE: {link} ===\n{sub_text}")
                await asyncio.sleep(0.5)  # Be polite

        combined = "\n\n".join(all_texts)
        print(f"  Total scraped text: {len(combined)} chars across {len(visited)} pages")
        return combined if combined.strip() else None


class FacebookScraper:
    def __init__(self):
        self.browser = None
        self.context = None

    async def start(self):
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1"
        )

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'pw'):
            await self.pw.stop()

    async def scrape_page(self, url):
        print(f"Scraping Facebook: {url}...")
        page = await self.context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            for tag in soup(['script', 'style']):
                tag.decompose()
            
            data = {"name": "", "about": "", "posts": []}

            name_tag = soup.find('h1')
            if name_tag:
                data["name"] = name_tag.get_text(strip=True)

            about_keywords = ["About", "Intro", "Address", "Phone", "Hours"]
            about_section = []
            for kw in about_keywords:
                match = soup.find(string=lambda t: t and kw in t)
                if match:
                    parent = match.find_parent()
                    if parent:
                        about_section.append(parent.get_text(strip=True))
            data["about"] = " | ".join(about_section)

            post_containers = soup.find_all(['div', 'span'], attrs={"role": None})
            for container in post_containers:
                text = container.get_text(strip=True)
                if 50 < len(text) < 500:
                    if text not in data["posts"]:
                        data["posts"].append(text)
            
            data["posts"] = data["posts"][:30]

            full_fb_text = (
                f"Business Name: {data['name']}\n"
                f"About: {data['about']}\n"
                f"Recent Posts:\n" + "\n---\n".join(data["posts"])
            )
            return full_fb_text
        except Exception as e:
            print(f"Error scraping Facebook {url}: {e}")
            return None
        finally:
            await page.close()


async def main():
    url = "https://americanburgerbd.com/"
    scraper = Scraper()
    await scraper.start()
    text = await scraper.scrape_url(url)
    await scraper.stop()
    
    if text:
        os.makedirs("data", exist_ok=True)
        with open("data/scraped_content.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Successfully scraped content: {len(text)} chars")
    else:
        print("Scraping failed.")

if __name__ == "__main__":
    asyncio.run(main())
