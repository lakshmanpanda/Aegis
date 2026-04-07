"""
amazon_search_agent.py
──────────────────────
Takes a search keyword, hits Amazon's search results page,
and returns the URL of the top organic product listing.

Usage (standalone):
    from agents.amazon_search_agent import search_amazon
    url = search_amazon("ASUS RTX 5060 GPU")

Usage (as pipeline entry):
    Replaces the hardcoded target_url in main_agent.py.
    Call  get_target_url(keyword)  which returns a ready-to-use URL string.
"""

import re
import time
import requests
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
AMAZON_SEARCH_URL = "https://www.amazon.in/s?k={query}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
}


# ──────────────────────────────────────────────────────────────────────────────
# Public helpers
# ──────────────────────────────────────────────────────────────────────────────

def search_amazon(keyword: str) -> str | None:
    """
    Search Amazon for *keyword* and return the URL of the first product result.

    Returns None if blocked or no products found.
    """
    keyword = keyword.strip()
    if not keyword:
        raise ValueError("Keyword must not be empty.")

    search_url = AMAZON_SEARCH_URL.format(query=requests.utils.quote(keyword))
    print(f"[Amazon Search] Querying: {search_url}")

    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=20)
    except Exception as exc:
        print(f"[Amazon Search] Request failed: {exc}")
        return None

    if "captcha" in resp.text.lower() or resp.status_code == 503:
        print("[Amazon Search] ALERT: Amazon CAPTCHA / bot protection hit.")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Amazon wraps each result in a div with data-asin attribute
    # We skip sponsored items and grab the first organic result.
    result_divs = soup.select("div[data-asin]")

    for div in result_divs:
        asin = div.get("data-asin", "").strip()
        if not asin:
            continue

        # Skip sponsored / ad slots (they have a specific class)
        if div.find("span", string=re.compile(r"Sponsored", re.I)):
            continue

        # Find the product link inside this card
        link_tag = div.select_one("a.a-link-normal[href*='/dp/']")
        if link_tag:
            href = link_tag.get("href", "")
            # href is relative — make it absolute
            if href.startswith("/"):
                href = "https://www.amazon.in" + href
            # Strip tracking params for a clean URL
            clean_url = re.sub(r"\?.*", "", href)
            print(f"[Amazon Search] Top result ASIN: {asin}  →  {clean_url}")
            return clean_url

    print("[Amazon Search] No product links found in search results.")
    return None


def get_target_url(keyword: str, retries: int = 2) -> str | None:
    """
    Wrapper with retry logic. Returns the product URL or None.
    If Amazon direct search is blocked/fails, falls back to DuckDuckGo "site:amazon.in" search.
    """
    
    for attempt in range(retries):
        url = search_amazon(keyword)
        if url:
            return url
        if attempt < retries - 1:
            wait = (attempt + 1) * 4
            print(f"[Amazon Search] Retrying in {wait}s...")
            time.sleep(wait)

    # ── Fallback to DuckDuckGo if direct Amazon fails ──
    print("[Amazon Search] Amazon direct search failed. Falling back to DuckDuckGo parser...")
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            # Drop the typo-prone string parsing and use standard site operator
            ddg_query = f"site:amazon.in {keyword}"
            results = list(ddgs.text(ddg_query, max_results=8))
            for r in results:
                href = r.get("href", "")
                if "amazon.in" in href and ("/dp/" in href or "/product/" in href):
                    clean_url = re.sub(r"\?.*", "", href)
                    print(f"[Amazon Search] DDG Fallback found: {clean_url}")
                    return clean_url
    except Exception as exc:
        print(f"[Amazon Search] DDG Fallback failed: {exc}")

    return None


# ──────────────────────────────────────────────────────────────────────────────
# Standalone test
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    kw = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "boAt Airdopes wireless earbuds"
    result = get_target_url(kw)
    print(f"\nTarget URL: {result}")
