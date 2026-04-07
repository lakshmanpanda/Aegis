"""
Node 3: Wargaming Strategist - Advanced Tool-Loop Edition
Lead Architect: CHEDDE LAKSHMAN | Roll No: 22PT08
"""

import json
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.models.state import AgentState
from app.core.prompts import WARGAMING_STRATEGIST_PROMPT
from app.core.mathematics import calculate_c_pivot
from app.core.mcp_client import aegis_mcp_client

class StrategyOutput(BaseModel):
    strategy_reasoning: str = Field(description="The Tree of Thoughts critique of the options.")
    winning_strategy: str = Field(description="The final selected business strategy.")
    w1: float = Field(description="Weight for Price Velocity")
    w2: float = Field(description="Weight for Review Sentiment")
    w3: float = Field(description="Weight for Social Virality")
    w4: float = Field(description="Weight for Macro Impact")
    w5: float = Field(description="Weight for Internal Risk")

async def strategist_node(state: AgentState) -> dict:
    print("--- [NODE: WARGAMING STRATEGIST] Executing Multi-Step Tool Loop ---")
    
    # 1. Setup LLM and Tools
    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0.1)
    mcp_tools = await aegis_mcp_client.get_tools()
    llm_with_tools = llm.bind_tools(mcp_tools)
    
    # 2. Extract Identifier
    pricing = state.get("intel_payload", {}).get("1_pricing_signals", {})
    target_sku = pricing.get("asin") or state.get("intel_payload", {}).get("scrape_metadata", {}).get("target_product", "Unknown_Product")
    
    # 3. Initial Call: Forces the LLM to realize it needs the Graph and Inventory
    messages = [
        SystemMessage(content=WARGAMING_STRATEGIST_PROMPT),
        HumanMessage(content=f"Product Identity: {target_sku}. Retrieve database context and inventory risk before calculating scores.")
    ]
    
    try:
        # FIRST PASS: The LLM will generate Tool Calls
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        # 4. Handle Tool Calls and Feed Results Back
        if response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                print(f"[STRATEGIST] Executing Tool: {tool_name}...")
                
                # Dynamically find and run the tool from the MCP client
                tool_to_run = next(t for t in mcp_tools if t.name == tool_name)
                tool_result = await tool_to_run.ainvoke(tool_call["args"])
                
                # Append the result back to the message history
                messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"]))

            # SECOND PASS: Now the LLM has the graph data in its history
            # We use with_structured_output to get the final Pydantic result

            structured_llm = llm.with_structured_output(StrategyOutput)
            final_response: StrategyOutput = await structured_llm.ainvoke(messages)
            print(final_response)
        else:
            # Fallback if it didn't call tools (unlikely with our new prompt)
            print("⚠️ [STRATEGIST] No tool calls triggered. Using raw data.")
            structured_llm = llm.with_structured_output(StrategyOutput)
            final_response = await structured_llm.ainvoke(messages)

# 5. Math Execution
        # Extract basic signals for the math formula from the payload
        raw_delta_p = pricing.get("price_drop_pct", 0) or 0.0
        # Normalize percentages (e.g., 20 becomes 0.20)
        delta_p = float(raw_delta_p) / 100.0 if float(raw_delta_p) > 1.0 else float(raw_delta_p)
        
        # Calculate review severity based on the number of negative themes
        s_rev = min(len(state.get("intel_payload", {}).get("2_sentiment_signals", {}).get("negative_themes", [])) / 5.0, 1.0)
        
        # We tie the baseline variables to the AI's weightings to make the score hyper-dynamic
        v_soc = 0.8 if final_response.w3 > 0.5 else 0.2
        m_macro = 0.8 if final_response.w4 > 0.5 else 0.2
        r_risk = 0.8 if final_response.w5 > 0.5 else 0.2
        
        c_pivot = calculate_c_pivot(
            delta_p=delta_p, 
            s_rev=s_rev, 
            v_soc=v_soc, 
            m_macro=m_macro, 
            r_risk=r_risk,
            w1=final_response.w1, 
            w2=final_response.w2, 
            w3=final_response.w3, 
            w4=final_response.w4, 
            w5=final_response.w5
        )

        print(f"[STRATEGIST] Causal Logic finalized. Score: {c_pivot}")
        return {
            "c_pivot_score": c_pivot,
            "strategy_reasoning": final_response.strategy_reasoning,
            "winning_strategy": final_response.winning_strategy
        }

    except Exception as e:
        print(f"❌ [STRATEGIST ERROR] Loop failed: {e}")
        return {"c_pivot_score": 0.0, "winning_strategy": "MANUAL_INTERVENTION_REQUIRED"}