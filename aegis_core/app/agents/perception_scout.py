"""
Node 1: Perception Scout
Lead Architect: CHEDDE LAKSHMAN | Roll No: 22PT08
"""

import json
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.models.state import AgentState
from app.core.prompts import PERCEPTION_SCOUT_PROMPT
from app.core.mcp_client import aegis_mcp_client

async def perception_node(state: AgentState) -> dict:
    print("--- [NODE: PERCEPTION SCOUT] Initiating Analysis ---")
    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0.0)
    
    # Bind tools if you are using fetch_historical_competitor_data
    mcp_tools = await aegis_mcp_client.get_tools()
    llm_with_tools = llm.bind_tools(mcp_tools)
    
    payload_str = json.dumps(state.get("intel_payload", {}))
    messages = [
        SystemMessage(content=PERCEPTION_SCOUT_PROMPT),
        HumanMessage(content=f"Analyze this payload and extract anomalies:\n{payload_str}")
    ]
    
    try:
        response = await llm_with_tools.ainvoke(messages)
        
        # SAFELY PARSE THE NEW GEMINI OUTPUT
        content = response.content
        if isinstance(content, list):
            # Extract text from the blocks
            content = "\n".join([str(c.get("text", "")) for c in content if isinstance(c, dict) and "text" in c])
        elif not content:
            content = ""
            
        anomalies = [line.strip() for line in content.split('\n') if line.strip().startswith('-')]
        
        print(f"[SCOUT] Detected {len(anomalies)} critical anomalies.")
        return {"detected_anomalies": anomalies}
        
    except Exception as e:
        print(f"[SCOUT ERROR] Analysis failed: {e}")
        return {"detected_anomalies": []}