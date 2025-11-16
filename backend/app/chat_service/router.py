# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel
# from .llm_client import query_llm

# router = APIRouter()

# class ChatRequest(BaseModel):
#     message: str

# @router.post("/chat/")
# async def chat(req: ChatRequest):
#     try:
#         response = await query_llm(req.message)
#         return {"reply": response}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# backend/app/chat_service/router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .extractor import extract
from .llm_client import explain_with_llm
from ..data_service import fetch_market_history  # use your existing function
from typing import Dict

router = APIRouter(prefix="/chat", tags=["Chatbot"])


class ChatRequest(BaseModel):
    message: str


@router.post("/")
async def chat(req: ChatRequest):
    user_message = req.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Empty message")

    # 1) Extract coin, currency, intent
    coin, currency, intent = await extract(user_message)
    # defensive defaults
    if not coin:
        coin = "bitcoin"
    if not currency:
        currency = "usd"

    # 2) Fetch recent history (1 day) and compute metrics (server-side)
    try:
        # fetch 1 day of hourly data (your fetch_market_history returns (points, analysis))
        points, analysis = await fetch_market_history(coin, currency, days=1)
        # points should be list of dicts with 'ts' and 'price'
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed fetching price history: {e}")

    if not points:
        return {"reply": f"No recent price data available for {coin} in {currency}."}

    # compute numeric facts
    try:
        prices = [float(p["price"]) for p in points if ("price" in p)]
        times = [p["ts"] for p in points if ("ts" in p)]
        first_price = prices[0]
        last_price = prices[-1]
        pct_change = (last_price - first_price) / first_price * 100 if first_price != 0 else 0.0
        trend = "UP" if last_price > first_price else "DOWN"
        trend_icon = "📈" if trend == "UP" else "📉"

        # Build human-friendly summary for LLM (facts only)
        summary_text = (
            f"Coin: {coin.upper()}\n"
            f"Currency: {currency.upper()}\n"
            f"First Price: {first_price:.2f} {currency.upper()}\n"
            f"Last Price: {last_price:.2f} {currency.upper()}\n"
            f"Change (%): {pct_change:.2f}%\n"
            f"Trend: {trend} {trend_icon}\n"
        )

        # small series sample for context (optional)
        series_text = "\n".join([f"{t} → {float(p):.2f}" for t, p in zip(times, prices)])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute metrics: {e}")

    # 3) Decide behavior based on intent
    if intent == "price":
        # direct fact: respond with last price
        reply = f"Last recorded {coin.upper()} price: {last_price:.2f} {currency.upper()} (at {times[-1]})."
        return {"reply": reply}

    elif intent == "trend":
        # direct fact: return trend with pct change
        reply = (
            f"Based on the last {len(prices)} points, {coin.upper()} is {trend} {trend_icon}. "
            f"First: {first_price:.2f} {currency.upper()}, Last: {last_price:.2f} {currency.upper()}, "
            f"Change: {pct_change:.2f}%."
        )
        return {"reply": reply}

    elif intent in {"summary", "general"}:
        # Hand-off to LLM for a natural-language explanation using only summary_text
        # provide summary_text and the short series_text as context
        llm_summary = summary_text + "\nRecent series (timestamp -> price):\n" + series_text
        explanation = await explain_with_llm(llm_summary, user_message)
        return {"reply": explanation}

    else:
        # fallback: treat as general
        explanation = await explain_with_llm(summary_text + "\n" + series_text, user_message)
        return {"reply": explanation}
