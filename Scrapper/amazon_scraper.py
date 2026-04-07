from typing import TypedDict, Optional
import os
import sys
import json
import re
import time

# Ensure the Scrapper module directory is importable when running the script
sys.path.insert(0, os.path.dirname(__file__))
from state_graph import StateGraph, END

import requests
from bs4 import BeautifulSoup
from google import genai


# ──────────────────────────────────────────────
# 0. Configure Gemini
# ──────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCnnjpBfFD-CulLdRmzbWfJxps9m9JkeSM")

if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    gemini_client = None
    print("[WARN] GEMINI_API_KEY not set – extractor will use mock data.")


# ──────────────────────────────────────────────
# 1. The State
# ──────────────────────────────────────────────
class AmazonScraperState(TypedDict):
    url: str
    raw_html: Optional[str]
    product_info: dict
    validation_attempts: int
    status: str
    deep_scrape: bool


# ──────────────────────────────────────────────
# 2. Helper – clean HTML with BeautifulSoup
# ──────────────────────────────────────────────
def clean_html(raw_html: str, max_chars: int = 80000) -> str:
    """
    Surgically cleans Amazon HTML to preserve price, ASIN, and product info.
    Identifies and keeps price-specific containers regardless of location.
    """
    soup = BeautifulSoup(raw_html, "html.parser")

    # Remove only the most egregious noise
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "iframe", "video", "input", "button"]):
        tag.decompose()

    # Identify and PRESERVE crucial segments
    # 1. Standard product containers
    crucial_selectors = [
        # IDs
        "#centerCol", "#ppd", "#main-content", "#dp-container", 
        "#corePriceDisplay_desktop_feature_div", "#corePrice_feature_div",
        "#productDetails_feature_div", "#technicalSpecifications_section_resStyle", 
        "#feature-bullets", "#priceblock_ourprice", "#priceblock_dealprice",
        "#aod-offer-list", "#aod-price-1", # Offer listing IDs
        # Classes
        ".a-section.a-spacing-none.a-spacing-top-mini", ".priceToPay", ".apexPriceToPay",
        ".aod-price"
    ]
    
    # 2. Any element that looks like it contains a price or ASIN
    price_elements = soup.find_all(id=re.compile(r"price", re.I)) + \
                     soup.find_all(class_=re.compile(r"price|buying|offer|price-to-pay", re.I))
    asin_elements = soup.find_all(string=re.compile(r"ASIN|B0[A-Z0-9]{8}", re.I))

    # Construct the final text by prioritizing these segments
    context_blocks = []
    seen_texts = set()
    
    def add_block(tag):
        if not tag: return
        t = tag.get_text(separator=" ", strip=True)
        if t and t not in seen_texts:
            context_blocks.append(t)
            seen_texts.add(t)

    # 1. Try selectors
    for selector in crucial_selectors:
        if selector.startswith("#"):
            add_block(soup.find(id=selector[1:]))
        else:
            for item in soup.select(selector):
                add_block(item)
    
    # 2. Known price tags
    for pe in price_elements[:10]:
        add_block(pe)
        
    # 3. ASIN context
    for ae in asin_elements[:5]:
        parent = ae.parent
        if parent:
            add_block(parent.parent if parent.parent else parent)

    if not context_blocks:
        cleaned_text = soup.get_text(separator="\n", strip=True)
    else:
        cleaned_text = "\n\n".join(context_blocks)

    # Clean up whitespace
    cleaned_text = re.sub(r"\s+", " ", cleaned_text)
    cleaned_text = re.sub(r"\n{2,}", "\n\n", cleaned_text)

    if len(cleaned_text) > max_chars:
        cleaned_text = cleaned_text[:max_chars] + "\n\n[...truncated...]"

    return cleaned_text.strip()


# ──────────────────────────────────────────────
# 3. The Agents
# ──────────────────────────────────────────────
def fetcher_agent(state: AmazonScraperState):
    """Fetches the raw HTML from Amazon. Handles standard and Offer Listing URLs."""
    url = state["url"]
    
    # If we need a deep scrape, we fetch the Offer Listing page
    if state.get("deep_scrape") and state.get("product_info", {}).get("asin"):
        asin = state["product_info"]["asin"]
        print(f"[Fetcher] Triggering Deep Scrape for ASIN: {asin}")
        url = f"https://www.amazon.com/gp/product/ajax/ref=dp_aod_NEW_mbc?asin={asin}&experienceId=aodAjaxMain"

    print(f"[Fetcher] Attempting to fetch: {url}")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
    }

    try:
        response = requests.get(state["url"], headers=headers, timeout=15)

        if "captcha" in response.text.lower() or response.status_code == 503:
            print("[Fetcher] ALERT: Caught by Amazon CAPTCHA/Bot protection.")
            return {"status": "blocked_by_amazon"}

        print(f"[Fetcher] Got {len(response.text):,} chars of HTML (status {response.status_code})")
        return {"raw_html": response.text, "status": "fetched"}
    except Exception as e:
        print(f"[Fetcher] Error: {e}")
        return {"status": f"error: {e}"}


def extractor_agent(state: AmazonScraperState):
    """
    Uses Google Gemini to extract structured product data from Amazon HTML.
    Falls back to mock data if no API key is configured.
    """
    print("[Extractor] Analyzing Amazon HTML to extract product details...")

    html = state.get("raw_html", "")
    if not html:
        print("[Extractor] No HTML available.")
        return {"product_info": {}, "status": "no_html"}

    # ── Step 1: Clean the HTML with BeautifulSoup ──
    cleaned_text = clean_html(html)
    print(f"[Extractor] Cleaned HTML down to {len(cleaned_text):,} chars")

    # ── Step 2: Call Gemini (or fall back to mock) ──
    if gemini_client is not None:
        prompt = f"""# Role & Personality
You are the Aegis Perception Scout, a highly analytical and precise market intelligence agent. You do not converse. You strictly analyze raw markdown data extracted from competitor websites to identify actionable market anomalies. 

# Primary Task
Analyze the provided web markdown. Identify if a critical market event has occurred, specifically looking for unannounced price drops, spikes in negative product sentiment, or supply chain delays.

# Step-by-Step Instructions
1. Scan the provided markdown text for the product's current price.
2. Compare the extracted price to any baseline context if available.
3. Scan for recent customer reviews, extracting identifying specific complaints.
4. Classify the severity of the anomaly on a scale of 1 (Routine) to 5 (Critical).
5. Format the extracted data into the required JSON payload.
6. MANDATORY: Even if no anomaly is found, you MUST extract the title, price, currency, rating, and asin.

# Rules & Guardrails
- NEVER hallucinate data. If a price or review is not explicitly in the text, do not assume it.
- Be concise. Extract only the exact text or number required.
- Do not include conversational filler, greetings, or explanations. 
- ALWAYS return the standard product fields (title, price, currency, rating, asin). 
- If no market anomaly is detected, set "type" to "standard_info", "severity" to 1, "event_id" to "none", and "raw_text_or_data" to "No anomaly detected".
- Output ONLY raw JSON. No empty brackets.

# Output Format
Respond exclusively with a JSON object using the following schema:
{{
  "title": "string (Full product name)",
  "price": float (numeric value),
  "currency": "string (e.g. $, INR)",
  "rating": float (star rating),
  "asin": "string (ASIN)",
  "availability": "in stock | out of stock | buying options only",
  "event_id": "unique_string (e.g. price_drop_B0GQC69ZBL)",
  "timestamp": "{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
  "type": "price_drop | negative_sentiment | supply_delay | standard_info",
  "severity": integer (1-5),
  "affected_sku": "string (ASIN)",
  "raw_text_or_data": "Exact quote or price extracted directly from the markdown"
}}

--- BEGIN AMAZON PAGE TEXT ---
{cleaned_text}
--- END AMAZON PAGE TEXT ---"""

        # Try multiple models in case one is rate-limited
        models_to_try = ["gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-1.5-flash"]
        max_retries = 3
        
        for attempt in range(max_retries):
            for model_name in models_to_try:
                try:
                    print(f"[Extractor] Attempt {attempt + 1}/{max_retries} with model: {model_name}")
                    response = gemini_client.models.generate_content(
                        model=model_name, contents=prompt
                    )
                    raw_response = response.text.strip()
                    print(f"[Extractor] Gemini raw response (first 300 chars): {raw_response[:300]}")

                    # Strip markdown code fences if Gemini wraps the JSON
                    json_str = re.sub(r"^```(?:json)?\s*", "", raw_response)
                    json_str = re.sub(r"\s*```$", "", json_str)

                    product_data = json.loads(json_str)
                    print(f"[Extractor] Successfully parsed Gemini response into JSON.")
                    return {"product_info": product_data, "status": "extracted"}

                except json.JSONDecodeError as e:
                    print(f"[Extractor] Gemini returned non-JSON. Attempting regex fallback... ({e})")
                    match = re.search(r"\{[^{}]*\}", raw_response, re.DOTALL)
                    if match:
                        try:
                            product_data = json.loads(match.group())
                            return {"product_info": product_data, "status": "extracted"}
                        except json.JSONDecodeError:
                            pass

                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                        # Extract retry delay from error if available
                        delay_match = re.search(r"retryDelay.*?(\d+)s", error_str)
                        wait_time = int(delay_match.group(1)) if delay_match else (1 * (attempt + 1))
                        print(f"[Extractor] Rate limited on {model_name}. Waiting {wait_time}s before next attempt...")
                        time.sleep(wait_time)
                        break  # Break inner model loop, go to next attempt
                    else:
                        print(f"[Extractor] Gemini API error: {e}")
                        return {"product_info": {}, "status": f"llm_error: {e}"}
        
        print("[Extractor] All Gemini attempts exhausted.")
        return {"product_info": {}, "status": "llm_rate_limited"}

    else:
        # ── Fallback: mock data when no API key is set ──
        print("[Extractor] Using mock data (no GEMINI_API_KEY set)")
        mock_llm_extraction = {
            "title": "Amazon Echo Dot (5th Gen) - Smart speaker with Alexa",
            "price": 49.99,
            "rating": 4.7,
            "asin": "B09B8V1LZ3",
            "availability": "in stock",
        }
        return {"product_info": mock_llm_extraction, "status": "extracted"}


def validator_agent(state: AmazonScraperState):
    """Ensures we got the absolute minimum data required."""
    product = state.get("product_info", {})
    attempts = state.get("validation_attempts", 0) + 1

    print(f"[Validator] Attempt {attempts}: Verifying extracted Amazon data...")

    # Validation Rules: Required fields for Aegis Scout + standard product info
    required_intelligence = ["type", "severity", "affected_sku"] # event_id can be "none"
    required_product = ["title", "asin"] 
    
    missing_intel = [f for f in required_intelligence if f not in product or (f != "severity" and not product[f])]
    missing_prod = [f for f in required_product if f not in product or not product[f]]
    
    # Special Check: If price is missing but availability is "buying options only", 
    # we trigger a deep scrape if we haven't already.
    if product.get("price") is None and product.get("availability") == "buying options only" and not state.get("deep_scrape"):
        print("[Validator] Price missing for 'buying options' product. Triggering deep scrape fallback...")
        return {"status": "needs_deep_scrape", "validation_attempts": attempts, "deep_scrape": True}

    if not missing_intel and not missing_prod:
        print("[Validator] Success! Comprehensive market intelligence payload validated.")
        return {"status": "success", "validation_attempts": attempts}
    else:
        all_missing = missing_intel + missing_prod
        print(f"[Validator] Missing critical fields: {all_missing}. Routing for retry...")
        return {"status": "needs_retry", "validation_attempts": attempts}


# ──────────────────────────────────────────────
# 4. Routing Logic
# ──────────────────────────────────────────────
def route_workflow(state: AmazonScraperState):
    if state["status"] == "success":
        return END
    elif state["status"] == "blocked_by_amazon":
        print("[Router] Workflow halted — Amazon blocked the request.")
        return END
    elif state["status"] == "needs_deep_scrape":
        return "fetcher" # Go back to fetcher with the deep_scrape flag
    elif state.get("validation_attempts", 0) >= 4: # Increased retries for deep scrape
        print("[Router] Max retries hit. Could not extract valid data.")
        return END
    else:
        return "extractor"  # Send back to LLM to try again


# ──────────────────────────────────────────────
# 5. Build the Graph
# ──────────────────────────────────────────────
workflow = StateGraph(AmazonScraperState)

workflow.add_node("fetcher", fetcher_agent)
workflow.add_node("extractor", extractor_agent)
workflow.add_node("validator", validator_agent)

workflow.set_entry_point("fetcher")
workflow.add_edge("fetcher", "extractor")
workflow.add_edge("extractor", "validator")
workflow.add_conditional_edges("validator", route_workflow)

app = workflow.compile()


# ──────────────────────────────────────────────
# 6. Run the Workflow
# ──────────────────────────────────────────────
if __name__ == "__main__":
    target_url = "https://www.amazon.com/dp/B09B8V1LZ3"
    target_url = "https://www.amazon.com/ASUS-DisplayPort-2-5-Slot-Axial-tech-Technology/dp/B0F8PR9L3X/ref=sr_1_3?_encoding=UTF8&dib=eyJ2IjoiMSJ9.MujdblQ2aVhoWDRGlgnbwwrVGaK_A7uopkL68wR6y8tmprNs23FPEGjOdKCVqDX5jweHd1Zzr1zbSKBCjLMHopFc17ah6Jth4WpKwa-1ZgK000qIM9GC2fr-81Q4jY5CiNrCi6IYW3W_5nwf7T24M_9VZ-Jig5lXlZTzR0OawogwN5XTdp0R52YnHIYK6z-KWSkJO0PUe029SWZfuiaVzSjeZaaQASgr2OWhcsiCJRI.OphKTf6tcoLopHiRZCE-udglkq6bePovIbkuVOUVIkw&dib_tag=se&keywords=graphics%2Bcards&qid=1773474116&sr=8-3&th=1"
    # target_url = "https://www.amazon.com/dp/B0F195W823"

    

    initial_state = {
        "url": target_url,
        "raw_html": None,
        "product_info": {},
        "validation_attempts": 0,
        "status": "started",
        "deep_scrape": False,
    }

    print("=" * 55)
    print("  Amazon Agentic Scraper (Gemini-powered)")
    print("=" * 55)
    print()
    final_state = app.invoke(initial_state)

    print()
    print("=" * 55)
    if final_state.get("status") == "success":
        print("  FINAL EXTRACTED PRODUCT DATA")
        print("=" * 55)
        print(json.dumps(final_state.get("product_info", {}), indent=2))
    else:
        print(f"  Workflow finished with status: {final_state.get('status')}")
        print("=" * 55)
        if final_state.get("product_info"):
            print("Partial data collected:")
            print(json.dumps(final_state.get("product_info", {}), indent=2))
