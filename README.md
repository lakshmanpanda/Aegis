# Aegis Perception Scout 

A multi-agent competitive intelligence pipeline that extracts dynamic market signals, pricing, sentiment, and competitor data for e-commerce products. Built using **FastAPI**, **LangGraph**, and the **Google Gemini API**.

## 🚀 Overview
Aegis Perception Scout is designed to take a messy e-commerce search term (e.g., `"samsung a55 mobile"`), locate the product on Amazon India (`amazon.in`), scrape the product page, and execute five parallel LLM-powered extraction agents to build a comprehensive, structured JSON market report.

If Amazon's anti-bot protections block the scraper, the system degrades gracefully by executing intelligent DuckDuckGo search fallbacks to rebuild the context so the pipeline continues to succeed.

---

## 🏗️ Architecture

The system is built as a stateful graph utilizing `langgraph`, where each node is an independent "agent" responsible for a specific slice of intelligence.

### Pipeline Flow (`main_agent.py`)

1. **Input Resolution (`amazon_search_agent.py`)**: Resolves chaotic user keywords into a clean `amazon.in` product URL. Falls back to DuckDuckGo search if Amazon search is blocked.
2. **Data Ingestion (`fetcher.py`)**: Fetches the raw HTML from the target URL. If blocked by CAPTCHA, it initiates a **Central DDG Fallback**, performing targeted searches for price, reviews, and market news, synthesizing them into an artificial HTML blob.
3. **Parallel Analysis (The Agents)**:
   - **`pricing_agent`**: Extracts exact numerical price, original price, discount percentage, and inventory flags.
   - **`sentiment_agent`**: Reads customer reviews to extract aggregate ratings, positive/negative themes, and highlighting recent critical quotes.
   - **`market_intel_agent`**: Hunts for macroeconomic signals (supply shortages, material alerts) and social media trends/viral moments.
   - **`competitor_intel_agent`**: Uses a two-step RAG process to convert the product name into an optimized search query, searches the web for alternative products, and uses Gemini to map out out at least two direct competitors (ensuring different brands) and their prices.
4. **Aggregation (`aggregator_node`)**: Merges the results of all specialized agents into a final, unified JSON schema.

---

## 🛠️ Tech Stack
- **Python 3.10+**
- **FastAPI / Uvicorn** (REST API)
- **LangGraph** (State orchestration)
- **Google GenAI / Gemini** (LLM extraction and structuring)
- **BeautifulSoup4** (HTML parsing and cleaning)
- **DuckDuckGo Search (`ddgs`)** (Live web fallbacks and RAG)

---

## ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <repo_url>
   cd CIT/Scrapper
   ```

2. **Set up a Virtual Environment & Install Dependencies:**
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```

3. **Environment Variables:**
   The `main_agent.py` script requires a valid Google Gemini API Key. By default, it looks for the `GEMINI_API_KEY` system environment variable. Ensure this is configured in your terminal or `.env` file before running.

---

## 🚦 Usage

### 1. Running the FastAPI Server
To launch the API, run the following in your configured virtual environment:
```bash
python -m uvicorn api:app --reload
```
The server will start on `http://127.0.0.1:8000`.

### 2. Making an API Request (Test Script)
You can test the server by running the standard testing script:
```bash
python test_scapper.py
```
This script sends a `POST` request to `/api/v1/scrape` with a payload: `{"keyword": "sasmsung galaxy s23"}`.

### 3. Running via CLI (Direct Execution)
You can bypass the FastAPI server completely and run the pipeline synchronously in your shell for debugging:
```bash
python main_agent.py "iphone 17 pro max"
```

---

## 🛡️ The Fallback Mechanisms
Because scraping Amazon is highly prone to IP blocking and CAPTCHAs, Aegis Scout implements deep fault-tolerance:
1. **Search Fallback**: If `amazon_search_agent.py` gets blocked searching `amazon.in`, it switches to parsing `site:amazon.in {keyword}` on DuckDuckGo to obtain the target `dp/` string.
2. **Fetcher Fallback**: If `fetcher.py` gets blocked trying to read the target URL, it generates a "Fake HTML" string consisting of 10 targeted DuckDuckGo snippets regarding the product's price, reviews, and news. 
3. **Robust Extractions**: The downstream RAG agents (`pricing`, `sentiment`, `market`) accept this fake HTML snippet blob transparently and estimate values based on news publications.
4. **Competitor Independence**: The `competitor_intel_agent` handles broken titles gracefully by extracting product names manually from the Amazon URL slug before querying the internet.

---

## 📊 Output Schema
The final JSON response strictly adheres to the following structure:
```json
{
  "scrape_metadata": {
    "scrape_id": "intel_123456789",
    "timestamp_utc": "2026-03-14T12:00:00Z",
    "target_url": "https://www.amazon.in/..."
  },
  "1_pricing_signals": {
    "title": "...",
    "current_price": 45000.0,
    ...
  },
  "2_sentiment_signals": {},
  "3_social_media_signals": {},
  "4_macro_economic_and_supply_chain_news": {},
  "5_competitor_corporate_intel": {}
}
```
