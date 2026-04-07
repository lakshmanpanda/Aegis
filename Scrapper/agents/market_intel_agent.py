"""
market_intel_agent.py
─────────────────────
Extracts social-media signals and macro/supply-chain news from page HTML
using the shared google.genai client passed from main_agent.
"""

import re
import json
import time
from google import genai
from utils.html_cleaner import clean_html


def market_intel_agent(state: dict, client: genai.Client, model_name: str) -> dict:
    """
    Extracts 3_social_media_signals and 4_macro_economic_and_supply_chain_news.

    State reads:  raw_html
    State writes: social_data, macro_data
    """
    print(f"[Market Intel Agent] Running with model: {model_name}")

    html = state.get("raw_html") or ""
    if not html:
        print("[Market Intel Agent] No HTML available — skipping.")
        return {"social_data": {}, "macro_data": {}}

    cleaned = clean_html(html)

    prompt = f"""You are a market intelligence scout. Extract two categories of signals from the product page text below.

Return ONLY a JSON object with these two top-level keys:

"3_social_media_signals":
  - trending_platforms : list of strings — social platforms where the product is trending (e.g. TikTok, Reddit)
  - viral_mentions      : list of strings — notable viral moments or trending hashtags mentioned
  - influencer_refs     : list of strings — any influencer or creator mentions found

"4_macro_economic_and_supply_chain_news":
  - material_alerts     : list of strings — mentions of key materials (e.g. GDDR7, nylon, copper)
  - shipping_news       : list of strings — any shipping, import duty, or logistics mentions
  - supply_constraints  : list of strings — stock warnings, shortage signals, or lead time hints
  - regional_notes      : list of strings — region-specific pricing or availability notes

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
            print(f"[Market Intel Agent] Social signals: {len(data.get('3_social_media_signals', {}))} fields | Macro: {len(data.get('4_macro_economic_and_supply_chain_news', {}))} fields")
            return {
                "social_data": data.get("3_social_media_signals", {}),
                "macro_data":  data.get("4_macro_economic_and_supply_chain_news", {}),
            }

        except Exception as exc:
            if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                wait = (attempt + 1) * 6
                print(f"[Market Intel Agent] Rate limited — waiting {wait}s (attempt {attempt+1}/3)")
                time.sleep(wait)
            else:
                print(f"[Market Intel Agent] Error on attempt {attempt+1}: {exc}")
                break

    return {"social_data": {}, "macro_data": {}}
