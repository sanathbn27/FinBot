# backend/app/chat_service/router_groq.py
# Groq-aware chat router — same logic as router.py but imports from Groq modules.
# To activate: in main_groq.py, include this router instead of router.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .extractor_groq import extract
from .llm_client_groq import explain_with_llm
from ..data_service import fetch_market_history

router = APIRouter(prefix="/chat", tags=["Chatbot"])


class ChatRequest(BaseModel):
    message: str


@router.post("/")
async def chat(req: ChatRequest):
    user_message = req.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Empty message")

    # 1) Extract coin, currency, intent via Groq
    coin, currency, intent = await extract(user_message)
    if not coin:
        coin = "bitcoin"
    if not currency:
        currency = "usd"

    # 2) Fetch recent history (1 day) from CoinGecko
    try:
        points, analysis = await fetch_market_history(coin, currency, days=1)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed fetching price history: {e}"
        )

    if not points:
        return {"reply": f"No recent price data available for {coin} in {currency}."}

    # 3) Compute numeric facts
    try:
        prices = [float(p["price"]) for p in points if "price" in p]
        times = [p["ts"] for p in points if "ts" in p]
        first_price = prices[0]
        last_price = prices[-1]
        pct_change = (
            (last_price - first_price) / first_price * 100 if first_price != 0 else 0.0
        )
        trend = "UP" if last_price > first_price else "DOWN"
        trend_icon = "📈" if trend == "UP" else "📉"

        summary_text = (
            f"Coin: {coin.upper()}\n"
            f"Currency: {currency.upper()}\n"
            f"First Price: {first_price:.2f} {currency.upper()}\n"
            f"Last Price: {last_price:.2f} {currency.upper()}\n"
            f"Change (%): {pct_change:.2f}%\n"
            f"Trend: {trend} {trend_icon}\n"
        )
        series_text = "\n".join(
            [f"{t} → {float(p):.2f}" for t, p in zip(times, prices)]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute metrics: {e}")

    # 4) Respond based on intent
    if intent == "price":
        return {
            "reply": f"Last recorded {coin.upper()} price: {last_price:.2f} {currency.upper()} (at {times[-1]})."
        }

    elif intent == "trend":
        return {
            "reply": (
                f"Based on the last {len(prices)} points, {coin.upper()} is {trend} {trend_icon}. "
                f"First: {first_price:.2f} {currency.upper()}, Last: {last_price:.2f} {currency.upper()}, "
                f"Change: {pct_change:.2f}%."
            )
        }

    else:
        # "summary" or "general" — hand off to Groq LLM
        llm_context = (
            summary_text + "\nRecent series (timestamp → price):\n" + series_text
        )
        explanation = await explain_with_llm(llm_context, user_message)
        return {"reply": explanation}
