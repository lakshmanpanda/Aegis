from mcp.server.fastmcp import FastMCP
from typing import Dict, Any
import numpy as np



# Initialize the FastMCP Server
intel_mcp = FastMCP("Aegis-Intel-Server")

@intel_mcp.tool()
def get_internal_inventory(sku: str) -> Dict[str, Any]:
    """
    Retrieves the current inventory risk level for our own products.
    The Wargaming Strategist uses this to calculate R_risk.
    """
    # MOCK DATABASE CALL: In a real app, this queries PostgreSQL/Shopify
    print(f"[INTEL SERVER] Fetching inventory for SKU: {sku}")
    
    mock_db = {
        "OWN-BKP-01": {"stock": 1450, "status": "High Inventory", "risk_score": 0.1},
        "OWN-TENT-02": {"stock": 12, "status": "Critical Low", "risk_score": 0.9}
    }
    
    # Default to a safe medium risk if SKU isn't in our mock DB
    return mock_db.get(sku, {"stock": 500, "status": "Stable", "risk_score": 0.5})

@intel_mcp.tool()
def fetch_historical_competitor_data(competitor_name: str) -> str:
    """
    Checks if this competitor has a history of suddenly dropping prices.
    Helps the AI determine if a price drop is an anomaly or a routine sale.
    """
    print(f"[INTEL SERVER] Fetching history for Competitor: {competitor_name}")
    
    if competitor_name.lower() == "titangear":
        return "Competitor TitanGear rarely discounts products by more than 15%. A drop > 30% is highly anomalous and indicates distress."
    
    return "No significant historical pricing anomalies detected."

if __name__ == "__main__":
    intel_mcp.run(transport="stdio")