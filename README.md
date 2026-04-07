# AEGIS

A multi-agent competitive intelligence pipeline that extracts dynamic market signals and computes deterministic wargaming strategies using **Causal GraphRAG**. Built for modern e-commerce, AEGIS shifts sellers from reactive data-gathering to proactive, autonomous market pivoting.

## 🔗 Live Deployments & Assets
* **Command Center UI:** [https://appapppy-xpoeymdfuezerc6vv4qjnd.streamlit.app/](https://appapppy-xpoeymdfuezerc6vv4qjnd.streamlit.app/)
* **Aegis Core API (Brain):** [https://aegis-core.onrender.com](https://aegis-core.onrender.com)
* **Scraper API (Sensor):** [https://aegis-scraper.onrender.com](https://aegis-scraper.onrender.com)
* **Presentation Pitch Deck:** [Datathon_Team_UB (Google Slides)](https://docs.google.com/presentation/d/1lBWxlehAVeHtb3YF99FxSpKUpDQoBYip/edit?usp=sharing&ouid=106915806088206113312&rtpof=true&sd=true)

---

## 🚀 Overview

Aegis Perception Scout maps the true cause-and-effect of market shifts. Instead of dumping raw, disconnected data on a dashboard, the system utilizes a swarm of specialized LLM agents to scrape the web, build a **Neo4j Knowledge Graph**, calculate mathematical volatility scores, and autonomously email executive strategies.

The repository is divided into two distinct microservices:
1. **`Scrapper/` (The Sensor):** A highly fault-tolerant web extraction API.
2. **`aegis_core/` (The Brain):** The central LangGraph orchestrator, Neo4j GraphRAG engine, and background email sentinel.

---

## 🌟 Key Features

* **Causal GraphRAG Engine:** Moves beyond standard Vector RAG. Uses **Neo4j** to map hidden causal relationships between competitor pricing, customer sentiment defects, and macro-economic supply chain events.
* **Deterministic Wargaming ($C_{pivot}$):** Translates qualitative market chaos into a quantitative, math-backed volatility score to recommend exact business maneuvers.
* **The "Always-On" Sentinel:** An autonomous background scheduler (`APScheduler`) that continuously monitors target SKUs and dispatches executive email alerts via Gmail when threat thresholds are crossed.
* **Model Context Protocol (MCP):** Enterprise-grade security architecture where database operations (Neo4j) and communication tools (Gmail via Groq) run as isolated child processes.
* **Deep Fault-Tolerance:** Intelligent scraper fallbacks that bypass CAPTCHAs by synthesizing artificial HTML blobs from DuckDuckGo live search data.

---

## 🏗️ System Architecture

### 1. The Scraper Pipeline (`Scrapper/`)
* **Input Resolution:** Resolves chaotic keywords into clean `amazon.in` URLs.
* **Data Ingestion:** Fetches raw HTML. If blocked, triggers the **Central DDG Fallback** to rebuild context via live DuckDuckGo searches.
* **Parallel Extraction:** Five parallel agents (Pricing, Sentiment, Market Intel, Competitor Intel) extract and structure data into a strict JSON schema.

### 2. The Core Pipeline (`aegis_core/`)
* **API Gateway (`FastAPI`):** Receives the UI request and routes it to the AI swarm.
* **Traffic Cop Agent:** Checks the Neo4j database. If the product exists, it skips scraping to save time. If new, it calls the live Scraper API.
* **Graph Architect Agent:** Parses the scraper JSON and builds `[Nodes]` and `-[RELATIONSHIPS]->` in Neo4j AuraDB.
* **Wargaming Strategist Agent:** Interrogates the graph to score market severity, executes the $C_{pivot}$ math formula, and writes a tactical business pivot.
* **Execution Commander:** Formats the final JSON and triggers the MCP Mail server to alert stakeholders.

---

## 🛠️ Tech Stack

* **Orchestration:** LangGraph, LangChain
* **AI/LLMs:** Google Gemini 3.1 Flash-Lite, Groq (Llama-3)
* **Database:** Neo4j AuraDB (Cypher)
* **Backend API:** FastAPI, Uvicorn, Pydantic
* **Web Scraping:** BeautifulSoup4, DuckDuckGo Search (`ddgs`)
* **Infrastructure:** MCP (Model Context Protocol), APScheduler
* **Frontend:** Streamlit

---

## ⚙️ Local Installation & Setup

Because this is a microservice architecture, you will need to set up both folders.

### Part 1: Setup The Scraper API
```bash
git clone <your_repo_url>
cd Scrapper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the Scraper Server (Port 8000)
python -m uvicorn api:app --reload --port 8000
```

### Part 2: Setup The Aegis Core API
Open a **new terminal window** and navigate to the core folder:
```bash
cd aegis_core

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 🔐 Environment Variables (`aegis_core/.env`)
Create a `.env` file inside the `aegis_core/` folder with the following keys:
```env
# API Keys
GOOGLE_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key

# Database
NEO4J_URI=neo4j+s://your-database-id.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password

# Email Alert System
SENDER_EMAIL=your_email@gmail.com
GMAIL_APP_PASSWORD=your_16_digit_app_password

# Internal Routing
SCRAPER_URL=[http://127.0.0.1:8000/api/v1/scrape](http://127.0.0.1:8000/api/v1/scrape)  # Local testing
# SCRAPER_URL=[https://aegis-scraper.onrender.com/api/v1/scrape](https://aegis-scraper.onrender.com/api/v1/scrape) # Production
```

### Run the Core Server (Port 8001)
```bash
python -m uvicorn app.api.routes:app --reload --port 8001
```

---

## 🛡️ The Scraper Fallback Mechanism (Graceful Degradation)
Because scraping e-commerce sites is highly prone to IP blocking, AEGIS implements deep fault-tolerance:
1. **Search Fallback**: If Amazon search is blocked, it switches to parsing `site:amazon.in {keyword}` on DuckDuckGo.
2. **Fetcher Fallback**: If reading the target URL fails, it generates "Fake HTML" consisting of targeted DuckDuckGo snippets regarding the product's price, reviews, and news. 
3. **Robust Extractions**: The downstream LLM agents accept this snippet blob transparently and accurately estimate values based on aggregated news publications.

---
*Built for the CIT Datathon by Team UB.*
