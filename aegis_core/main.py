"""
AEGIS MARKET INTELLIGENCE
Root Execution File
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as market_router
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 1. Initialize the FastAPI Application
app = FastAPI(
    title="Aegis Market Intelligence API",
    description="Autonomous Agentic Layer for E-Commerce Strategy",
    version="1.0.0"
)

# 2. Add CORS Middleware 
# (Crucial so your Streamlit frontend can talk to this backend without browser blocks)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Mount the API Routes
app.include_router(market_router, prefix="/api/v1")

@app.get("/", tags=["Health"])
async def health_check():
    """Simple endpoint to verify the server is running."""
    return {"system": "Aegis Core", "status": "Online"}

if __name__ == "__main__":
    print("""
      ___   ___  ___ _____ ___ 
     / _ \ / _ \/ __|_   _/ __|
    |  _  |  __/ (_ | | | \__ \
    |_| |_|\___|\___| |_| |___/
    Autonomous Market Intelligence Engine
    """)
    # Run the server on port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)