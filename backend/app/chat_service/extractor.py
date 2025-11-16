# backend/app/chat_service/extractor.py
import json
import re
import httpx
from typing import Tuple, Dict, Any

OLLAMA_API = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "llama3:8b"

# allowed values
COINS = {"bitcoin", "ethereum", "solana"}
CURRENCIES = {"usd", "inr", "eur"}
INTENTS = {"price", "trend", "summary", "general"}

# small regex maps for fallback
COIN_ALIASES = {
    "bitcoin": ["bitcoin", "btc", "bit"],
    "ethereum": ["ethereum", "eth", "ether"],
    "solana": ["solana", "sol"],
}
CURRENCY_ALIASES = {
    "usd": ["usd", "dollar", "dollars", "usdt", "usd$"],
    "inr": ["inr", "rupee", "rupees", "rs", "₹"],
    "eur": ["eur", "euro", "€"],
}
INTENT_KEYWORDS = {
    "price": ["price", "rate", "cost", "value", "quote"],
    "trend": ["trend", "direction", "moving", "momentum", "going", "up or down", "up/down", "up or down"],
    "summary": ["summary", "summarize", "overview", "overview of", "what happened"],
}

async def _llm_extract_json(user_text: str, timeout: int = 20) -> Dict[str, Any]:
    """
    Ask the local Ollama model to extract structured fields from user_text.
    It MUST return strict JSON (no commentary). We parse it.
    """
    prompt = f"""
You are a small extraction assistant. Extract the following fields from the user's question and return ONLY valid JSON (no explanation, no extra text):

Fields:
- coin: one of ["bitcoin","ethereum","solana"]
- currency: one of ["usd","inr","eur"]
- intent: one of ["price","trend","summary","general"]

Rules:
- If coin is not mentioned, default to "bitcoin".
- If currency is not mentioned, default to "usd".
- If intent is unclear, choose "general".
- Output only valid JSON, no code fences.

User question:
\"\"\"{user_text}\"\"\"
"""
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(OLLAMA_API, json={"model": MODEL_NAME, "prompt": prompt, "stream": False})
        resp.raise_for_status()
        data = resp.json()
        # best-effort extraction of returned text
        raw = ""
        if isinstance(data, dict):
            raw = data.get("response", "")
        else:
            raw = str(data)

    # try to find JSON substring
    try:
        # sometimes the model may return whitespace - find first '{' ... last '}'
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_text = raw[start:end+1]
            parsed = json.loads(json_text)
            return parsed
    except Exception:
        pass

    # if LLM failed to give valid JSON, return empty -> fallback
    return {}

def _regex_fallback(user_text: str) -> Dict[str, str]:
    text = user_text.lower()

    # detect coin
    detected_coin = None
    for coin, aliases in COIN_ALIASES.items():
        for a in aliases:
            if a in text:
                detected_coin = coin
                break
        if detected_coin:
            break

    # detect currency
    detected_currency = None
    for cur, aliases in CURRENCY_ALIASES.items():
        for a in aliases:
            if a in text:
                detected_currency = cur
                break
        if detected_currency:
            break

    # detect intent
    detected_intent = None
    for intent, keys in INTENT_KEYWORDS.items():
        for k in keys:
            if k in text:
                detected_intent = intent
                break
        if detected_intent:
            break

    # defaults
    if not detected_coin:
        detected_coin = "bitcoin"
    if not detected_currency:
        detected_currency = "usd"
    if not detected_intent:
        detected_intent = "general"

    return {"coin": detected_coin, "currency": detected_currency, "intent": detected_intent}


async def extract(user_text: str) -> Tuple[str, str, str]:
    """
    Returns (coin, currency, intent). Uses LLM extraction first, falls back to regex.
    """
    try:
        parsed = await _llm_extract_json(user_text)
        if parsed:
            coin = parsed.get("coin", "").lower() if isinstance(parsed.get("coin", ""), str) else ""
            currency = parsed.get("currency", "").lower() if isinstance(parsed.get("currency", ""), str) else ""
            intent = parsed.get("intent", "").lower() if isinstance(parsed.get("intent", ""), str) else ""
            # validate
            if coin not in COINS:
                coin = ""
            if currency not in CURRENCIES:
                currency = ""
            if intent not in INTENTS:
                intent = ""
            if coin and currency and intent:
                return coin, currency, intent
    except Exception:
        # don't break on extraction error; fallback below
        pass

    # fallback to regex heuristic
    fb = _regex_fallback(user_text)
    return fb["coin"], fb["currency"], fb["intent"]
