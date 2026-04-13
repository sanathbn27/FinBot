# backend/app/main.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import PriceRequest
from .data_service import fetch_simple_price, fetch_market_history
from .chat_service.router_groq import router as chat_router

load_dotenv()

app = FastAPI(title="FinBot Backend")

# # Allow requests from local Streamlit
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# ---------------------------------------------------------------------------
# CORS — allow localhost for dev + any deployed Streamlit URL from env
# Set ALLOWED_ORIGINS="https://yourapp.streamlit.app" in your deployment env
# ---------------------------------------------------------------------------
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501"
)
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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
