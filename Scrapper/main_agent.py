"""
main_agent.py
─────────────
Aegis Perception Scout — Multi-Agent Market Intelligence System
Orchestrates: fetcher → pricing → sentiment → intel → competitor → validator → aggregator
"""

import os
import sys
import json
import time
from typing import TypedDict, Optional

sys.path.insert(0, os.path.dirname(__file__))

from state_graph import StateGraph, END
from google import genai

from agents.fetcher                import fetcher_agent
from agents.pricing_agent          import pricing_agent
from agents.sentiment_agent        import sentiment_agent
from agents.market_intel_agent     import market_intel_agent
from agents.competitor_intel_agent import competitor_intel_agent
from agents.amazon_search_agent    import get_target_url

# ──────────────────────────────────────────────────────────────────────────────
# 0. Configuration
# ──────────────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyASuQ24rQGAXFuxOnCkzhjkn_zhyboI9G4")
MODEL_NAME     = "gemini-3.1-flash-lite-preview"
client         = genai.Client(api_key=GEMINI_API_KEY)

# ──────────────────────────────────────────────────────────────────────────────
# 1. State Schema
# ──────────────────────────────────────────────────────────────────────────────
class MarketIntelState(TypedDict):
    url:                str
    raw_html:           Optional[str]
    status:             str
    validation_attempts: int
    deep_scrape:        bool
    model_name:         str

    # Agent outputs (section keys match final JSON sections)
    pricing_data:       dict   # 1_pricing_signals
    sentiment_data:     dict   # 2_sentiment_signals
    social_data:        dict   # 3_social_media_signals
    macro_data:         dict   # 4_macro_economic_and_supply_chain_news
    competitor_data:    dict   # 5_competitor_corporate_intel

    final_payload:      dict

# ──────────────────────────────────────────────────────────────────────────────
# 2. Graph Nodes
# ──────────────────────────────────────────────────────────────────────────────

def pricing_node(state: MarketIntelState):
    res = pricing_agent(state, client, state.get("model_name", MODEL_NAME))
    return {"pricing_data": res.get("pricing_data", {})}


def sentiment_node(state: MarketIntelState):
    res = sentiment_agent(state, client, state.get("model_name", MODEL_NAME))
    return {"sentiment_data": res.get("sentiment_data", {})}


def market_intel_node(state: MarketIntelState):
    res = market_intel_agent(state, client, state.get("model_name", MODEL_NAME))
    return {
        "social_data": res.get("social_data", {}),
        "macro_data":  res.get("macro_data",  {}),
    }


def competitor_intel_node(state: MarketIntelState):
    """Searches DuckDuckGo + Gemini to find competitor products and their prices."""
    res = competitor_intel_agent(state, client, state.get("model_name", MODEL_NAME))
    return {"competitor_data": res.get("competitor_data", {})}


def aggregator_node(state: MarketIntelState):
    """Assembles all agent outputs into the final market intelligence JSON."""
    print("[Aggregator] Composing final payload...")
    payload = {
        "scrape_metadata": {
            "scrape_id":    f"intel_{int(time.time())}",
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "target_url":   state["url"],
        },
        "1_pricing_signals":                      state.get("pricing_data",    {}),
        "2_sentiment_signals":                    state.get("sentiment_data",  {}),
        "3_social_media_signals":                 state.get("social_data",     {}),
        "4_macro_economic_and_supply_chain_news": state.get("macro_data",      {}),
        "5_competitor_corporate_intel":           state.get("competitor_data", {}),
    }
    return {"final_payload": payload, "status": "success"}


def validator_node(state: MarketIntelState):
    """Checks if key data is present; triggers a deep scrape if price is missing."""
    price    = state.get("pricing_data", {}).get("current_price")
    attempts = state.get("validation_attempts", 0) + 1

    if price is None and not state.get("deep_scrape") and attempts < 2:
        print("[Validator] Price missing — triggering deep scrape fallback...")
        return {"status": "needs_deep_scrape", "validation_attempts": attempts, "deep_scrape": True}

    print("[Validator] Validation complete.")
    return {"status": "success", "validation_attempts": attempts}


def route_after_validator(state: MarketIntelState):
    if state["status"] == "needs_deep_scrape":
        return "fetcher"
    return "aggregator"

# ──────────────────────────────────────────────────────────────────────────────
# 3. Build the Graph
# ──────────────────────────────────────────────────────────────────────────────
workflow = StateGraph(MarketIntelState)

workflow.add_node("fetcher",    fetcher_agent)
workflow.add_node("pricing",    pricing_node)
workflow.add_node("sentiment",  sentiment_node)
workflow.add_node("intel",      market_intel_node)
workflow.add_node("competitor", competitor_intel_node)
workflow.add_node("validator",  validator_node)
workflow.add_node("aggregator", aggregator_node)

workflow.set_entry_point("fetcher")
workflow.add_edge("fetcher",    "pricing")
workflow.add_edge("pricing",    "sentiment")
workflow.add_edge("sentiment",  "intel")
workflow.add_edge("intel",      "competitor")
workflow.add_edge("competitor", "validator")

workflow.add_conditional_edges("validator", route_after_validator)
workflow.add_edge("aggregator", END)

app = workflow.compile()

# ──────────────────────────────────────────────────────────────────────────────
# 4. Public API — importable by FastAPI / any other caller
# ──────────────────────────────────────────────────────────────────────────────

def run_pipeline(keyword: str = "", target_url: str = "") -> dict:
    """
    Run the full Aegis intelligence pipeline.

    Provide EITHER:
      - keyword   : searches Amazon.in for the top result URL automatically
      - target_url: skips the search step and goes straight to scraping

    Returns the final_payload dict (the complete JSON report).
    Raises RuntimeError if search yields no results.
    """
    if not keyword and not target_url:
        raise ValueError("Provide at least one of: keyword or target_url")

    if not target_url:
        print(f"[Pipeline] Searching Amazon for: {keyword!r}")
        target_url = get_target_url(keyword)
        if not target_url:
            raise RuntimeError(f"Amazon search returned no results for keyword: {keyword!r}")

    print(f"[Pipeline] target_url = {target_url}")

    initial_state: MarketIntelState = {
        "url":                 target_url,
        "raw_html":            None,
        "status":              "started",
        "validation_attempts": 0,
        "deep_scrape":         False,
        "model_name":          MODEL_NAME,
        "pricing_data":        {},
        "sentiment_data":      {},
        "social_data":         {},
        "macro_data":          {},
        "competitor_data":     {},
        "final_payload":       {},
    }

    result = app.invoke(initial_state)
    return result.get("final_payload", {})


# ──────────────────────────────────────────────────────────────────────────────
# 5. CLI entry point
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # ── Resolve target URL ─────────────────────────────────────────────────
    # Priority 1: CLI argument      →  python main_agent.py "boAt Airdopes 141"
    # Priority 2: Interactive prompt
    # Priority 3: Fallback hardcoded URL (for quick dev runs)

    if len(sys.argv) > 1:
        keyword = " ".join(sys.argv[1:]).strip()
        print(f"[Main] Keyword supplied via CLI: {keyword!r}")
        try:
            payload = run_pipeline(keyword=keyword)
        except Exception as e:
            print(f"[Main] Pipeline failed: {e}")
            sys.exit(1)
    else:
        keyword = input("\nEnter search keyword (or press Enter for demo URL): ").strip()
        if keyword:
            print(f"[Main] Searching Amazon for: {keyword!r}")
            try:
                payload = run_pipeline(keyword=keyword)
            except Exception as e:
                print(f"[Main] Pipeline failed: {e}")
                sys.exit(1)
        else:
            # Demo fallback
            target_url = (
                "https://www.amazon.in/ASUS-DisplayPort-2-5-Slot-Axial-tech-Technology/dp/B0F8PR9L3X/"
            )
            print(f"[Main] Using demo URL: {target_url}")
            payload = run_pipeline(target_url=target_url)

    print("\n" + "=" * 60)
    print("  FINAL MARKET INTELLIGENCE REPORT")
    print("=" * 60)
    print(json.dumps(payload, indent=2))
