import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, List
import json
import sys

# 1. Load the environment variables securely
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Initialize the Neo4j Driver
db_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

# Initialize the FastMCP Server
command_mcp = FastMCP("Aegis-Command-Server")

@command_mcp.tool()
def check_product_exists(sku: str) -> str:
    """
    Checks the Neo4j database to see if we already have a knowledge graph for this product.
    Returns a status string to guide the LangGraph routing.
    """
    print(f"[COMMAND SERVER] Checking DB for existing graph on SKU: {sku}", file=sys.stderr)
    query = """
    MATCH (p:Product {name: $sku})
    RETURN p.name AS name
    """
    try:
        with db_driver.session() as session:
            result = session.run(query, sku=sku).data()
            if result:
                return f"Product '{sku}' exists in the Knowledge Graph. Append new insights to it."
            else:
                return f"Product '{sku}' is NEW. Create a foundational Knowledge Graph."
    except Exception as e:
        print(f"[COMMAND SERVER ERROR] DB Check Failed: {e}")
        return "Database connection error. Treat as new product."

@command_mcp.tool()
def upsert_knowledge_graph(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
    """
    Writes complex schema-validated nodes and relationships into Neo4j.
    Expects nodes with 'label', 'name', and 'properties'.
    Expects edges with 'source', 'target', 'relationship', and 'properties'.
    """
    print(f"[COMMAND SERVER] Upserting {len(nodes)} Nodes and {len(edges)} Edges into Neo4j...", file=sys.stderr)
    
    try:
        with db_driver.session() as session:
            # 1. Process Nodes
            for node in nodes:
                label = node.get("label", "Entity").replace(" ", "") # e.g., "Brand", "Product"
                name = node.get("name")
                props = node.get("properties", {})
                
                # MERGE ensures we don't duplicate. SET += appends/updates the new properties securely.
                node_query = f"""
                MERGE (n:{label} {{name: $name}})
                SET n += $props
                """
                session.run(node_query, name=name, props=props)
                print(f"  -> Upserted Node: ({label}: {name})", file=sys.stderr)

            # 2. Process Edges
            for edge in edges:
                source = edge.get("source")
                target = edge.get("target")
                rel_type = edge.get("relationship", "RELATED_TO").upper().replace(" ", "_")
                props = edge.get("properties", {})
                
                # Match the source and target by their Primary Key (name), then MERGE the relationship
                edge_query = f"""
                MATCH (s {{name: $source}})
                MATCH (t {{name: $target}})
                MERGE (s)-[r:{rel_type}]->(t)
                SET r += $props
                """
                session.run(edge_query, source=source, target=target, props=props)
                print(f"  -> Upserted Edge: ({source}) -[:{rel_type}]-> ({target})", file=sys.stderr)

        return f"Successfully committed {len(nodes)} nodes and {len(edges)} edges to Neo4j AuraDB."
    
    except Exception as e:
        error_msg = f"[COMMAND SERVER ERROR] Graph Upsert Failed: {e}"
        print(error_msg)
        return error_msg

@command_mcp.tool()
def fetch_product_knowledge_graph(sku: str) -> str:
    """
    Retrieves the entire causal subgraph for a specific product.
    Used by the Wargaming Strategist to calculate the C_pivot score based on graph logic, not raw JSON.
    """
    print(f"[COMMAND SERVER] Fetching Knowledge Graph for SKU: {sku}")
    
    # This Cypher query finds the Product and all its immediate neighbors (Brands, Events, Competitors, Features)
    query = """
    MATCH (p:Product {name: $sku})
    OPTIONAL MATCH (p)-[r]-(n)
    RETURN p.name AS Product, labels(n)[0] AS NodeType, n.name AS NodeName, type(r) AS Relationship, properties(n) AS NodeProps, properties(r) AS EdgeProps
    """
    
    try:
        with db_driver.session() as session:
            results = session.run(query, sku=sku).data()
            
            if not results or results[0].get('NodeType') is None:
                return f"No graph context found for {sku}. The graph might be empty."
            
            # Format the output cleanly for the LLM
            graph_context = []
            for record in results:
                rel = record.get('Relationship', 'UNKNOWN')
                node_type = record.get('NodeType', 'Entity')
                node_name = record.get('NodeName', 'Unknown')
                node_props = record.get('NodeProps', {})
                
                # e.g., "(Product) -[COMPETES_WITH]-> (Competitor: TitanGear) | Props: {'price': 400}"
                entry = f"({record['Product']}) -[{rel}]-> ({node_type}: {node_name}) | Properties: {json.dumps(node_props)}"
                graph_context.append(entry)
                
            formatted_graph = "\n".join(graph_context)
            print(f"[COMMAND SERVER] Successfully retrieved {len(results)} graph connections.")
            return formatted_graph
            
    except Exception as e:
        print(f"[COMMAND SERVER ERROR] Failed to fetch graph: {e}")
        return "Error retrieving knowledge graph."

if __name__ == "__main__":
    print("[COMMAND SERVER] MCP Server is UP and listening for AI commands...", file=sys.stderr)
    command_mcp.run(transport="stdio")