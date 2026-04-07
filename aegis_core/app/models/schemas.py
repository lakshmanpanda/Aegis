from pydantic import BaseModel, Field, ConfigDict
from typing import Any

class AegisIntelPayload(BaseModel):
    # This configuration makes the payload virtually indestructible
    model_config = ConfigDict(populate_by_name=True, extra="allow")
    
    scrape_metadata: Any = Field(default_factory=dict)
    pricing_signals: Any = Field(default_factory=dict, alias="1_pricing_signals")
    sentiment_signals: Any = Field(default_factory=dict, alias="2_sentiment_signals")
    social_media_signals: Any = Field(default_factory=list, alias="3_social_media_signals")
    macro_news: Any = Field(default_factory=list, alias="4_macro_economic_and_supply_chain_news")
    competitor_intel: Any = Field(default="", alias="5_competitor_corporate_intel")