"""
pricing_agent.py
────────────────
Extracts price, inventory, and product identity from page HTML
using the shared google.genai client passed from main_agent.
"""

import re
import json
import time
from google import genai
from utils.html_cleaner import clean_html


def pricing_agent(state: dict, client: genai.Client, model_name: str) -> dict:
    """
    Extracts 1_pricing_signals from raw HTML.

    State reads:  raw_html
    State writes: pricing_data
    """
    print(f"[Pricing Agent] Running with model: {model_name}")

    html = state.get("raw_html") or ""
    if not html:
        print("[Pricing Agent] No HTML available — skipping.")
        return {"pricing_data": {}}

    cleaned = clean_html(html)

    prompt = f"""You are a pricing intelligence expert. Extract the following fields from the product page text below.

Fields to extract (return ONLY a JSON object with these fields under the key "1_pricing_signals"):
- title              : string — full product title
- asin               : string — Amazon ASIN (10-char code) if present
- current_price      : float  — the price the customer pays right now
- original_price     : float  — list/strikethrough price, null if absent
- price_drop_pct     : float  — discount percentage, calculate if both prices available, else null
- currency           : string — e.g. "USD", "INR"
- inventory_estimate : string — one of "High", "Medium", "Low", "Out of Stock"
- availability       : string — "in stock", "out of stock", or "buying options only"

--- PAGE TEXT ---
{cleaned}
"""

    for attempt in range(3):
        try:
            resp = client.models.generate_content(model=model_name, contents=prompt)
            raw = resp.text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            data = json.loads(raw)
            signals = data.get("1_pricing_signals", data)   # tolerate flat response
            print(f"[Pricing Agent] Extracted: title={signals.get('title','?')!r}  price={signals.get('current_price')}")
            return {"pricing_data": signals}

        except Exception as exc:
            if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                wait = (attempt + 1) * 6
                print(f"[Pricing Agent] Rate limited — waiting {wait}s (attempt {attempt+1}/3)")
                time.sleep(wait)
            else:
                print(f"[Pricing Agent] Error on attempt {attempt+1}: {exc}")
                break

    return {"pricing_data": {}}
