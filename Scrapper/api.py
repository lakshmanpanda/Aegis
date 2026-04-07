"""
api.py
──────
FastAPI server exposing the Aegis Perception Scout pipeline.

Run with:
    uvicorn api:app --reload
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# Import the pipeline runner from main_agent
from main_agent import run_pipeline

app = FastAPI(
    title="Aegis Perception Scout API",
    description="Multi-Agent Market Intelligence System",
    version="1.0.0"
)

class ScrapeRequest(BaseModel):
    keyword: Optional[str] = None
    target_url: Optional[str] = None

@app.post("/api/v1/scrape")
def scrape_endpoint(req: ScrapeRequest):
    """
    Run the multi-agent pipeline.
    Provide either a `keyword` (to search Amazon) or a Direct `target_url`.
    """
    if not req.keyword and not req.target_url:
        raise HTTPException(
            status_code=400, 
            detail="Must provide either 'keyword' or 'target_url'."
        )

    try:
        # run_pipeline blocks synchronously. In a production app, 
        # this would be pushed to a Celery/Redis queue for async processing.
        payload = run_pipeline(
            keyword=req.keyword or "",
            target_url=req.target_url or ""
        )
        return payload
    
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Aegis Intelligence API"}
