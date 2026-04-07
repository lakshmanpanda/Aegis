"""
Node 4: Execution Commander
Translates strategy into a UI-ready Executive Briefing.
Lead Architect: CHEDDE LAKSHMAN | Roll No: 22PT08
"""

from typing import List
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.models.state import AgentState
from app.core.prompts import EXECUTION_COMMANDER_PROMPT

# The UI-Ready Presentation Schema
class UIExecutionReport(BaseModel):
    executive_summary: str = Field(description="High-level summary of the situation and chosen strategy.")
    key_insights: List[str] = Field(description="Bullet points explaining the market conditions and causal links.")
    tactical_steps: List[str] = Field(description="Step-by-step actions for the team to execute.")
    resource_allocation: str = Field(description="Where to focus budget and effort (e.g., Ad spend, Dev time).")
    projected_outcome: str = Field(description="What success looks like after execution.")

async def execution_node(state: AgentState) -> dict:
    print("--- [NODE: EXECUTION COMMANDER] Preparing UI Dashboard Report ---")
    
    c_pivot = state.get("c_pivot_score", 0.0)
    strategy = state.get("winning_strategy", "No strategy provided.")
    target_sku = state.get("intel_payload", {}).get("scrape_metadata", {}).get("target_product", "Unknown")
    
    # We lowered the threshold to 0.1 so you can see the payload generate for the demo
    if c_pivot > 0.1:
        print(f"[COMMANDER] Score {c_pivot} exceeds threshold. Generating Executive Report...")
        
        llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0.2)
        structured_llm = llm.with_structured_output(UIExecutionReport)
        
        messages = [
            SystemMessage(content=EXECUTION_COMMANDER_PROMPT),
            HumanMessage(content=f"Target SKU: {target_sku}\nStrategist Output to Format: {strategy}")
        ]
        
        try:
            response: UIExecutionReport = await structured_llm.ainvoke(messages)
            payload_dict = response.model_dump()
            print("[COMMANDER] UI Report generated successfully.")
            return {"execution_payload": payload_dict}
        except Exception as e:
            print(f"❌ [COMMANDER ERROR] Report generation failed: {e}")
            return {"execution_payload": {"error": str(e)}}
            
    else:
        print("[COMMANDER] Score too low. MONITOR_ONLY.")
        # Return a UI-friendly "Safe" payload so your frontend still looks good
        return {
            "execution_payload": {
                "executive_summary": "Market conditions are currently stable. The C_pivot score is below the intervention threshold.",
                "key_insights": [
                    "No critical anomalies detected in the current scrape.",
                    "Competitor positioning remains within acceptable parameters."
                ],
                "tactical_steps": [
                    "1. Maintain current pricing strategy.",
                    "2. Continue automated scraping and graph ingestion."
                ],
                "resource_allocation": "No changes required. Maintain baseline ad spend.",
                "projected_outcome": "Stable market share and margin preservation."
            }
        }