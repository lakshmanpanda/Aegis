"""
Node 2: GraphRAG Architect
Lead Architect: CHEDDE LAKSHMAN | Roll No: 22PT08
"""

import json
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.models.state import AgentState
from app.core.prompts import GRAPHRAG_ARCHITECT_PROMPT
from app.core.mcp_client import aegis_mcp_client

async def architect_node(state: AgentState) -> dict:
    print("--- [NODE: GRAPHRAG ARCHITECT] Mapping Causality to Neo4j ---")
    
    # 1. Extract the "Official" ID from the routing context
    # We grab this from the status string we built in routes.py
    current_status = state.get("current_status", "")
    # Or more reliably, we can pass it via the payload. 
    # Let's assume the Gateway logic we wrote earlier is working.
    
    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0.0)
    mcp_tools = await aegis_mcp_client.get_tools()
    llm_with_tools = llm.bind_tools(mcp_tools)
    
    payload_str = json.dumps(state.get("intel_payload", {}))
    
    # DEBUG PRINT: Verify alignment
    print(f"DEBUG: Architect is processing nodes. System Context: {current_status}")

    messages = [
        SystemMessage(content=GRAPHRAG_ARCHITECT_PROMPT),
        HumanMessage(content=f"""
        CONTEXT: {current_status}
        PAYLOAD: {payload_str}
        
        MANDATE: Ensure the primary :Product node uses the name identifier specified in the Routing Context above.
        """)
    ]
        
    try:
        # 4. Execute LLM Call (It will generate the tool call instead of text)
        response = await llm_with_tools.ainvoke(messages)
        edges_extracted = []
        
        # 5. Intercept the Tool Call and Execute via MCP Client
        if response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call["name"] == "upsert_knowledge_graph":
                    print("[ARCHITECT] Triggering Neo4j Upsert MCP Tool...")
                    
                    # Find the specific tool adapter
                    graph_tool = next(t for t in mcp_tools if t.name == "upsert_knowledge_graph")
                    
                    # Securely send the LLM's structured payload to the isolated server
                    mcp_result = await graph_tool.ainvoke(tool_call["args"])
                    print(f"[ARCHITECT] MCP Server Response: {mcp_result}")
                    
                    # Extract edges for the state update so the terminal looks nice
                    edges = tool_call["args"].get("edges", [])
                    edges_extracted = [{"source": e["source"], "target": e["target"], "relationship": e["relationship"]} for e in edges]
        else:
            print("[ARCHITECT WARNING] LLM failed to trigger the Neo4j upsert tool.")
            
        print(f"[ARCHITECT] Successfully mapped {len(edges_extracted)} causal edges.")
        return {"extracted_entities": edges_extracted}

    except Exception as e:
        print(f"[ARCHITECT ERROR] Graph mapping failed: {e}")
        return {"extracted_entities": []}