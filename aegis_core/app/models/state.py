from typing import TypedDict, List, Dict, Any, Annotated
import operator

# We use operator.add for lists so that when multiple agents append to a list,
# LangGraph knows to combine them rather than overwrite them.

class GraphEntity(TypedDict, total=False):
    """
    total=False allows optional keys, making it flexible for our new Neo4j properties.
    """
    source: str
    target: str
    relationship: str
    properties: dict
    
class AgentState(TypedDict):
    """
    The shared memory object for the LangGraph swarm.
    """
    # 1. The Raw Validated Input
    intel_payload: dict  # We will store the parsed AegisIntelPayload.model_dump() here
    
    # 2. Agent 1 (Perception Scout) Outputs
    detected_anomalies: Annotated[List[str], operator.add]
    
    # 3. Agent 2 (GraphRAG Architect) Outputs
    extracted_entities: Annotated[List[GraphEntity], operator.add]
    
    # 4. Agent 3 (Wargaming Strategist) Outputs
    c_pivot_score: float
    strategy_reasoning: str
    winning_strategy: str
    
    # 5. Agent 4 (Execution Commander) Outputs
    execution_payload: dict
    human_approval_required: bool
    current_status: str