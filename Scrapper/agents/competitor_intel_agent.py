"""
competitor_intel_agent.py
─────────────────────────
Finds at least two direct competitor products and their prices using a
two-step approach:
  1. Search DuckDuckGo via the duckduckgo_search library for competitor names.
  2. Ask Gemini (via the shared google.genai client) to structure the results.

Uses the SAME google.genai client/model_name pattern as all other agents —
no separate LangChain env vars needed.

Output key: "competitor_data"  →  mapped to "5_competitor_corporate_intel"
            in the final JSON payload by aggregator_node.
"""

import re
import json
import time
from google import genai
from ddgs import DDGS


# ─────────────────────────────────────────────────────────────────────────────
# Public agent entry-point
# ─────────────────────────────────────────────────────────────────────────────

def competitor_intel_agent(state: dict, client: genai.Client, model_name: str) -> dict:
    """
    Searches for competitor products and structures the result with Gemini.

    State reads:  pricing_data (for product title), url (fallback)
    State writes: competitor_data
    """
    print(f"[Competitor Intel] Running with model: {model_name}")

    product_name = _get_product_name(state)
    if not product_name:
        print("[Competitor Intel] No product name found — skipping.")
        return {"competitor_data": _empty_result("Unknown")}

    print(f"[Competitor Intel] Target product: {product_name!r}")

    # ── Step 1: DuckDuckGo search ────────────────────────────────────────────
    query = _make_search_query(product_name, client, model_name)
    print(f"[Competitor Intel] Search query: {query!r}")
    search_results = _ddg_search(query)
    if not search_results:
        print("[Competitor Intel] DuckDuckGo returned no results — skipping.")
        return {"competitor_data": _empty_result(product_name)}

    search_text = _format_search_results(search_results)

    # ── Step 2: Gemini structures the results ────────────────────────────────
    prompt = f"""You are a competitive market intelligence analyst.

Here are DuckDuckGo search results about competitors for the product: "{product_name}"

{search_text}

From these results, identify AT LEAST TWO direct competitor products and return ONLY a JSON object (no markdown fences) with this exact structure:
{{
  "target_product": "{product_name}",
  "competitors": [
    {{
      "name": "<full competitor product name>",
      "brand": "<brand/manufacturer>",
      "price": "<price string, e.g. $299.99 or ₹25999>",
      "price_numeric": <numeric float or null if unknown>,
      "currency": "<USD / INR / EUR / etc.>",
      "key_features": ["<feature 1>", "<feature 2>", "<feature 3>"],
      "buy_link": "<URL from search results, or null>",
      "market_position": "<one sentence: how this competitor compares to the target product>",
      "source": "<URL of the search result this data came from>"
    }}
  ],
  "competitive_summary": "<2-3 sentences on the overall competitive landscape>",
  "price_comparison_note": "<how competitor prices compare to the target product>"
}}

Rules:
- Include AT LEAST 2 competitors.
- The competitors should not be of the same brand competitor should be from diffrent brand only no exceptions
- Use only information found in the search results above.
- always give me some output dont return none
- If price is not explicitly stated, set price to "Not listed" and price_numeric to null.
"""

    for attempt in range(3):
        try:
            resp = client.models.generate_content(model=model_name, contents=prompt)
            raw = resp.text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            data = json.loads(raw)
            count = len(data.get("competitors", []))

            if count >= 2:
                print(f"[Competitor Intel] Success — found {count} competitors.")
                return {"competitor_data": data}
            else:
                print(f"[Competitor Intel] Only {count} competitor(s) found on attempt {attempt+1} — retrying...")

        except json.JSONDecodeError as exc:
            print(f"[Competitor Intel] JSON parse error on attempt {attempt+1}: {exc}")
        except Exception as exc:
            if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                wait = (attempt + 1) * 8
                print(f"[Competitor Intel] Rate limited — waiting {wait}s (attempt {attempt+1}/3)")
                time.sleep(wait)
            else:
                print(f"[Competitor Intel] Gemini error on attempt {attempt+1}: {exc}")
                break

    print("[Competitor Intel] All retries exhausted — returning empty result.")
    return {"competitor_data": _empty_result(product_name)}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_product_name(state: dict) -> str:
    """Extract a clean product name from already-scraped pricing data or URL."""
    title = state.get("pricing_data", {}).get("title", "")
    
    # If the title is missing, or looks like a fallback search string snippet instead of a real title, use the URL
    if title and len(title) > 2 and "SEARCH RESULTS" not in title:
        return title[:100].strip()

    # Fallback: derive something readable from the URL
    url = state.get("url", "")
    slug = re.sub(r"https?://[^/]+/", "", url).split("?")[0]
    slug = re.sub(r"/dp/[A-Z0-9]+.*", "", slug)   # strip ASIN segment
    slug = re.sub(r"[-/]", " ", slug).strip()
    return slug[:80] if slug else "Unknown Product"


def _make_search_query(product_name: str, client: genai.Client, model_name: str) -> str:
    """
    Build a short, focused DDG query using the LLM.
    We ask the LLM to extract the core brand and model name, dropping boilerplate words.
    """
    prompt = f"""You are a search query optimisation expert.
I have a messy e-commerce product name. I need you to convert it into a highly concise 3-to-5 word search query designed to find competitors and alternative products.

Rules for the query:
1. Keep only the essential brand and model line.
2. Drop all specs (like 8GB, DDR7, Bluetooth, 4K, features).
3. Drop all promotional words (like Edition, Series, Dual, OC).
4. Append the literal words: competitors alternatives price 2025
5. Return ONLY the final search query string. No quotes, no markdown, no other text.
6. The competitors should be from a DIFFERENT brand than the target product.
Product Name: "{product_name}"
"""
    try:
        resp = client.models.generate_content(model=model_name, contents=prompt)
        query = resp.text.strip().replace('"', '')
        if query:
            return query
    except Exception as exc:
        print(f"[Competitor Intel] LLM query generation failed ({exc}), falling back to basic truncate.")
        
    # Fallback if LLM fails
    short_name = product_name[:40].strip()
    return f"{short_name} competitors alternatives price 2025"


def _ddg_search(query: str, max_results: int = 8) -> list:
    """
    Run a DuckDuckGo text search and return a list of result dicts.
    Each dict has keys: title, href, body.
    Falls back gracefully if the library raises.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        print(f"[Competitor Intel] DuckDuckGo returned {len(results)} results for: {query!r}")
        return results
    except Exception as exc:
        print(f"[Competitor Intel] DuckDuckGo search failed: {exc}")
        return []


def _format_search_results(results: list) -> str:
    """Format DuckDuckGo results into a numbered text block for the LLM prompt."""
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(
            f"[{i}] Title: {r.get('title', 'N/A')}\n"
            f"    URL:   {r.get('href', 'N/A')}\n"
            f"    Snippet: {r.get('body', 'N/A')}\n"
        )
    return "\n".join(lines)


def _empty_result(product_name: str) -> dict:
    return {
        "target_product": product_name,
        "competitors": [],
        "competitive_summary": "Competitor data could not be retrieved.",
        "price_comparison_note": "N/A",
    }
