# backend/app/models.py
from pydantic import BaseModel
from typing import List, Optional

class PriceRequest(BaseModel):
    ids: List[str]                # e.g. ["bitcoin","ethereum"]
    vs_currencies: List[str] = ["usd"]

class AnalysisResult(BaseModel):
    first_price: float
    last_price: float
    pct_change: Optional[float]
    points: int
