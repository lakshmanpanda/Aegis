"""
sentiment_agent.py
──────────────────
Analyses customer reviews and ratings from page HTML
using the shared google.genai client passed from main_agent.
"""

import re
import json
import time
from google import genai
from utils.html_cleaner import clean_html


def sentiment_agent(state: dict, client: genai.Client, model_name: str) -> dict:
    """
    Extracts 2_sentiment_signals from raw HTML.

    State reads:  raw_html
    State writes: sentiment_data
    """
    print(f"[Sentiment Agent] Running with model: {model_name}")

    html = state.get("raw_html") or ""
    if not html:
        print("[Sentiment Agent] No HTML available — skipping.")
        return {"sentiment_data": {}}

    cleaned = clean_html(html)

    prompt = f"""You are a customer sentiment analyst. Examine the product reviews in the page text below.

Return ONLY a JSON object under the key "2_sentiment_signals" with these fields:
- aggregate_rating     : float  — average star rating (e.g. 4.3)
- total_reviews        : int    — total number of ratings if shown
- positive_themes      : list of strings — top recurring praise points (max 5)
- negative_themes      : list of strings — top recurring complaints (max 5)
- recent_critical_reviews : list of objects, each with:
    - date   : string
    - rating : int
    - body   : verbatim quote of the complaint (max 200 chars)

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
            signals = data.get("2_sentiment_signals", data)
            print(f"[Sentiment Agent] Rating: {signals.get('aggregate_rating')} | Reviews: {signals.get('total_reviews')}")
            return {"sentiment_data": signals}

        except Exception as exc:
            if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                wait = (attempt + 1) * 6
                print(f"[Sentiment Agent] Rate limited — waiting {wait}s (attempt {attempt+1}/3)")
                time.sleep(wait)
            else:
                print(f"[Sentiment Agent] Error on attempt {attempt+1}: {exc}")
                break

    return {"sentiment_data": {}}
