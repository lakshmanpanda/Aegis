"""
The Aegis Orchestrator
Compiles the AI nodes into a LangGraph State Machine.
Lead Architect: CHEDDE LAKSHMAN | Roll No: 22PT08
"""

from langgraph.graph import StateGraph, START, END
from app.models.state import AgentState

# Import the 4 specialized agent nodes (Now all async)
from app.agents.perception_scout import perception_node
from app.agents.graph_architect import architect_node
from app.agents.wargame_strategist import strategist_node
from app.agents.execution_commander import execution_node

from dotenv import load_dotenv
load_dotenv()

def build_aegis_graph():
    """
    Constructs and compiles the multi-agent workflow.
    LangGraph natively supports async nodes.
    """
    print("--- [SYSTEM] Initializing Aegis Graph Orchestrator ---")
    
    # 1. Initialize the Graph with our strict AgentState
    workflow = StateGraph(AgentState)

    # 2. Add the Nodes (The "Actors")
    # LangGraph will automatically detect these are async functions
    workflow.add_node("PerceptionScout", perception_node)
    workflow.add_node("GraphRAGArchitect", architect_node)
    workflow.add_node("WargamingStrategist", strategist_node)
    workflow.add_node("ExecutionCommander", execution_node)

    # 3. Define the Edges
    workflow.add_edge(START, "PerceptionScout")
    workflow.add_edge("PerceptionScout", "GraphRAGArchitect")
    workflow.add_edge("GraphRAGArchitect", "WargamingStrategist")
    workflow.add_edge("WargamingStrategist", "ExecutionCommander")
    workflow.add_edge("ExecutionCommander", END)

    # 4. Compile the graph
    # We do not use a checkpointer for this hackathon to keep it fast and stateless
    aegis_app = workflow.compile()
    
    print("--- [SYSTEM] Graph Compiled Successfully (Async Ready). ---")
    
    return aegis_app

# Instantiate the graph engine
aegis_engine = build_aegis_graph()