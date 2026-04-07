import json
import httpx
from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from app.graph.workflow import aegis_engine
from app.core.mcp_client import aegis_mcp_client
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager

router = APIRouter()

class KeywordRequest(BaseModel):
    keyword: str

@router.post("/analyze")
async def analyze_market_intel(req: KeywordRequest):
    user_keyword = req.keyword.strip()
    target_sku = user_keyword
    
    print("\n" + "="*60)
    print(f"🚀 [API GATEWAY] INCOMING INTELLIGENCE REQUEST FOR: {user_keyword}")
    print("="*60)
    
    try:
        # 1. First, check Neo4j with the user's exact keyword
        mcp_tools = await aegis_mcp_client.get_tools()
        check_tool = next((t for t in mcp_tools if t.name == "check_product_exists"), None)
        
        db_status = "Product is NEW."
        if check_tool:
            raw_status = await check_tool.ainvoke({"sku": target_sku})
            db_status = raw_status[0].get('text', str(raw_status)) if isinstance(raw_status, list) else str(raw_status)
            print(f"🚦 [TRAFFIC COP] DB Context: {db_status}")

        payload_dict = {}

        # 2. THE LOGIC FORK: Scrape ONLY if the product is genuinely new
        # We check if "EXISTS" is in the string, making sure it doesn't say "DOES NOT EXIST"
        db_upper = db_status.upper()
        is_existing = "EXISTS" in db_upper and "DOES NOT EXIST" not in db_upper

        if not is_existing:
            print(f"📡 [API GATEWAY] Product not found in graph. Reaching out to Scraper API (Port 8000)...")
            
            async with httpx.AsyncClient(timeout=180.0) as client:
                try:
                    scrape_resp = await client.post(
                        "http://127.0.0.1:8000/api/v1/scrape", 
                        json={"keyword": target_sku}
                    )
                    scrape_resp.raise_for_status()
                    payload_dict = scrape_resp.json()
                    print("✅ [API GATEWAY] Scraper data successfully retrieved.")
                except Exception as e:
                    print(f"⚠️ [API GATEWAY ERROR] Scraper failed or timed out: {e}")
                    raise HTTPException(status_code=502, detail=f"Scraper API failed: {e}")

            # 3. Extract Official Title from Scraper JSON using Micro-LLM
            print("🔍 [API GATEWAY] Normalizing Official Product Title...")
            try:
                llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0.0)
                prompt = f"""
                Extract the full, human-readable primary product title from this JSON. 
                Do NOT return an ASIN or SKU. Return ONLY the clean string identifier.
                JSON: {json.dumps(payload_dict)[:2000]}
                """
                ext_response = await llm.ainvoke([HumanMessage(content=prompt)])
                target_sku = ext_response.content[0].get('text').strip() if isinstance(ext_response.content, list) else ext_response.content.strip()
            except Exception:
                target_sku = user_keyword # Fallback to what the user typed

            print(f"🎯 [API GATEWAY] Official Database Target: {target_sku}")

            # 4. THE DOUBLE CHECK: Re-check db_status just in case the official title actually DOES exist!
            if check_tool and target_sku != user_keyword:
                raw_status = await check_tool.ainvoke({"sku": target_sku})
                db_status = raw_status[0].get('text', str(raw_status)) if isinstance(raw_status, list) else str(raw_status)
                print(f"🚦 [TRAFFIC COP] Updated DB Context for Official Title: {db_status}")

        else:
            # IT ALREADY EXISTS - SKIP THE SCRAPER!
            print(f"⚡ [API GATEWAY] Product already exists in Neo4j. Skipping Scraper API to save time.")
            target_sku = user_keyword
            # Provide a minimal payload so the AI doesn't crash, but instruct it to rely on the DB
            payload_dict = {
                "scrape_metadata": {"target_product": target_sku},
                "system_directive": "No new JSON data provided. Rely entirely on Neo4j GraphRAG for strategy."
            }

        # 5. Prepare LangGraph State
        initial_state = {
            "intel_payload": payload_dict,
            "detected_anomalies": [],
            "extracted_entities": [],
            "c_pivot_score": 0.0,
            "strategy_reasoning": "",
            "winning_strategy": "",
            "execution_payload": {},
            "human_approval_required": False,
            "current_status": f"{db_status}. MUST USE THIS EXACT PRODUCT ID: {target_sku}"
        }
        
        # 6. Execute the LangGraph Swarm
        print("🧠 [API GATEWAY] Dispatching payload to LangGraph Swarm...")
        final_state = await aegis_engine.ainvoke(initial_state)
        
        print(f"\n{'='*60}")
        print("🎯 [AEGIS SYSTEM: FINAL EXECUTION COMMAND]")
        print(f"{'='*60}")
        print(f"▶ TARGET PRODUCT : {target_sku}")
        print(f"▶ C_PIVOT SCORE  : {final_state.get('c_pivot_score')}")
        print("▶ EXECUTION PAYLOAD:")
        print(json.dumps(final_state.get('execution_payload', {}), indent=2))
        print(f"{'='*60}\n")
        
        return {
            "status": "success",
            "target_sku": target_sku,
            "c_pivot_score": final_state.get("c_pivot_score"),
            "execution_payload": final_state.get("execution_payload")
        }
        
    except Exception as e:
        print(f"❌ [API ERROR] System Failure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# BACKGROUND SENTINEL LOGIC
# ==========================================

# Initialize the global background scheduler
scheduler = AsyncIOScheduler()

async def run_sentinel_pipeline(keyword: str, email: str):
    """The background worker that wakes up, runs the AI, and emails the result."""
    print(f"\n🕵️ [SENTINEL] Waking up for scheduled scan on: {keyword}")
    
    try:
        # 1. Run the exact same AI pipeline we already built!
        req = KeywordRequest(keyword=keyword)
        result = await analyze_market_intel(req)
        
        # 2. Extract the UI report data
        payload = result.get("execution_payload", {})
        sku = result.get("target_sku", keyword)
        score = result.get("c_pivot_score", 0.0)
        
        # 3. Format the JSON into a beautiful, readable email body
        email_body = f"""
        🛡️ AEGIS MARKET INTELLIGENCE REPORT 🛡️
        Target Asset: {sku}
        C_Pivot Volatility Score: {score}

        === EXECUTIVE SUMMARY ===
        {payload.get('executive_summary', 'No summary generated.')}

        === KEY INSIGHTS ===
        {chr(10).join(['- ' + i for i in payload.get('key_insights', [])])}

        === TACTICAL STEPS ===
        {chr(10).join(['- ' + s for s in payload.get('tactical_steps', [])])}

        === RESOURCE ALLOCATION ===
        {payload.get('resource_allocation', 'N/A')}

        === PROJECTED OUTCOME ===
        {payload.get('projected_outcome', 'N/A')}
        """
        
        # 4. Grab the Mail tool from the MCP Client and send it!
        mcp_tools = await aegis_mcp_client.get_tools()
        send_email_tool = next((t for t in mcp_tools if t.name == "send_email"), None)
        
        if send_email_tool:
            print(f"📧 [SENTINEL] Formatting complete. Dispatching email to {email}...")
            # Execute the MCP tool directly!
            await send_email_tool.ainvoke({
                "recipient_email": email,
                "subject": f"AEGIS Alert: {sku} Strategy Update (Score: {score})",
                "body": email_body
            })
            print("✅ [SENTINEL] Email dispatched successfully.")
        else:
            print("❌ [SENTINEL ERROR] 'send_email' tool not found in MCP client!")
            
    except Exception as e:
        print(f"❌ [SENTINEL ERROR] Pipeline failed during background run: {e}")


class MonitorRequest(BaseModel):
    keyword: str
    email: str
    interval_minutes: int = 60 # Default to 1 hour, but adjustable for the Datathon demo

@router.post("/monitor/start")
async def start_monitoring(req: MonitorRequest):
    """API Endpoint to lock a product in and start the background clock."""
    job_id = f"monitor_{req.keyword.replace(' ', '_')}"
    
    # Remove existing job if it exists to avoid duplicate emails
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        
    # Schedule the recurring job
    scheduler.add_job(
        run_sentinel_pipeline, 
        'interval', 
        minutes=req.interval_minutes, 
        args=[req.keyword, req.email],
        id=job_id
    )
    # BONUS: Kick off the very first run immediately in the background so you don't have to wait an hour!
    scheduler.add_job(run_sentinel_pipeline, 'date', args=[req.keyword, req.email])
    
    return {
        "status": "success", 
        "message": f"🛡️ AEGIS Sentinel deployed for '{req.keyword}'. Emailing {req.email} every {req.interval_minutes} minutes."
    }

@router.post("/monitor/stop")
async def stop_monitoring(req: KeywordRequest):
    """API Endpoint to kill a running background monitor."""
    # Reconstruct the exact job_id we used to create it
    job_id = f"monitor_{req.keyword.strip().replace(' ', '_')}"
    
    # Check if the job exists and remove it
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        print(f"🛑 [SYSTEM] Sentinel deactivated for: {req.keyword}")
        return {
            "status": "success", 
            "message": f"🛑 Sentinel deactivated for '{req.keyword}'. No further emails will be sent."
        }
    else:
        print(f"⚠️ [SYSTEM] Tried to stop Sentinel for '{req.keyword}', but no active job was found.")
        return {
            "status": "error", 
            "message": f"Could not find an active Sentinel monitoring '{req.keyword}'."
        }
        
@asynccontextmanager            
async def lifespan(app: FastAPI):
    # This runs when the server boots up
    print("⏰ [SYSTEM] Starting Background Scheduler...")
    scheduler.start()
    yield
    # This runs when you hit CTRL+C to stop the server
    print("🛑 [SYSTEM] Shutting down Scheduler...")
    scheduler.shutdown()

app = FastAPI(title="Aegis Core API", lifespan=lifespan)
app.include_router(router)