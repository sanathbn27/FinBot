# backend/app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models import PriceRequest
from app.data_service import fetch_simple_price, fetch_market_history
from .chat_service.router import router as chat_router

app = FastAPI(title="FinBot Backend")

# Allow requests from local Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/price")
async def price(req: PriceRequest):
    try:
        data = await fetch_simple_price(req.ids, req.vs_currencies)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/{coin_id}")
async def history(coin_id: str, vs_currency: str = "usd", days: int = 7):
    try:
        points, analysis = await fetch_market_history(coin_id, vs_currency, days)
        return {"prices": points, "analysis": analysis.dict() if analysis else {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
app.include_router(chat_router)
