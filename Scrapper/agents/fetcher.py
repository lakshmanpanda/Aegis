# """
# fetcher.py
# ──────────
# Fetches raw HTML from a product page (Amazon / Flipkart).
# Handles standard URLs and deep-scrape Offer-Listing redirects.
# """

# import requests

# def fetcher_agent(state: dict) -> dict:
#     """
#     Fetches raw HTML from the target URL.

#     State reads:  url, deep_scrape, pricing_data.asin
#     State writes: raw_html, status
#     """
#     url = state["url"]

#     # If a deep scrape was requested and we already know the ASIN, hit the
#     # All-Offers page instead of the standard PDP.
#     asin = state.get("pricing_data", {}).get("asin")
#     if state.get("deep_scrape") and asin:
#         print(f"[Fetcher] Deep scrape triggered for ASIN: {asin}")
#         url = f"https://www.amazon.com/dp/{asin}/ref=olp_aod_redir?_encoding=UTF8&aod=1"

#     print(f"[Fetcher] Fetching: {url}")

#     headers = {
#         "User-Agent": (
#             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#             "AppleWebKit/537.36 (KHTML, like Gecko) "
#             "Chrome/124.0.0.0 Safari/537.36"
#         ),
#         "Accept-Language": "en-US,en;q=0.9",
#         "Accept-Encoding": "gzip, deflate, br",
#         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#         "Connection": "keep-alive",
#     }

#     try:
#         response = requests.get(url, headers=headers, timeout=20)

#         if "captcha" in response.text.lower() or response.status_code == 503:
#             print("[Fetcher] ALERT: Bot protection / CAPTCHA detected.")
#             return {"raw_html": None, "status": "blocked_by_amazon"}

#         print(f"[Fetcher] Success — {len(response.text):,} chars (HTTP {response.status_code})")
#         return {"raw_html": response.text, "status": "fetched"}

#     except Exception as exc:
#         print(f"[Fetcher] Request failed: {exc}")
#         return {"raw_html": None, "status": f"error: {exc}"}


import time
import random
import requests
from typing import Dict

# A list of diverse, modern User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"
]

def fetcher_agent(state: dict) -> dict:
    url = state["url"]
    asin = state.get("pricing_data", {}).get("asin")
    
    if state.get("deep_scrape") and asin:
        url = f"https://www.amazon.com/dp/{asin}/ref=olp_aod_redir?_encoding=UTF8&aod=1"

    # 1. Random Delay to mimic human behavior
    time.sleep(random.uniform(1.5, 3.5))

    # 2. Dynamic Headers
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/", # Make it look like you came from a search engine
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        # 3. Use a Session to handle cookies automatically
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=20)

        # 4. Check for CAPTCHA or Amazon's 'Dogs' page (404/503)
        low_html = response.text.lower()
        if "captcha" in low_html or "api-services-support@amazon.com" in low_html:
            print("[Fetcher] ALERT: Blocked by Amazon Bot Protection. Initiating Central DDG Fallback...")
            
            # Centralized Fallback: Generate an artificial "raw_html" comprised of focused search snippets
            import re
            slug = re.sub(r"https?://[^/]+/", "", url).split("?")[0]
            slug = re.sub(r"/dp/[A-Z0-9]+.*", "", slug)
            product_name = re.sub(r"[-/]", " ", slug).strip() or "Unknown Product"
            
            try:
                from ddgs import DDGS
                with DDGS() as ddgs:
                    combined_text = "SEARCH RESULTS:\n\n"
                    
                    print("[Fetcher] Fetching pricing signals from search...")
                    for r in list(ddgs.text(f"{product_name} price India Amazon", max_results=3)):
                        combined_text += f"[Price] {r.get('title')}: {r.get('body')}\n"
                        
                    print("[Fetcher] Fetching review signals from search...")
                    for r in list(ddgs.text(f"{product_name} reviews sentiment pros cons", max_results=4)):
                        combined_text += f"[Review] {r.get('title')}: {r.get('body')}\n"
                        
                    print("[Fetcher] Fetching market signals from search...")
                    for r in list(ddgs.text(f"{product_name} market news supply chain trends", max_results=3)):
                        combined_text += f"[Market] {r.get('title')}: {r.get('body')}\n"
                        
                return {"raw_html": combined_text, "status": "fallback_search_used"}
            except Exception as exc:
                print(f"[Fetcher] Central DDG fallback failed: {exc}")
                return {"raw_html": None, "status": "blocked_by_amazon"}

        if response.status_code != 200:
            print(f"[Fetcher] Failed with Status Code: {response.status_code}")
            return {"raw_html": None, "status": f"http_error_{response.status_code}"}

        print(f"[Fetcher] Success — {len(response.text):,} chars")
        return {"raw_html": response.text, "status": "fetched"}

    except Exception as exc:
        print(f"[Fetcher] Request failed: {exc}")
        return {"raw_html": None, "status": f"error: {exc}"}