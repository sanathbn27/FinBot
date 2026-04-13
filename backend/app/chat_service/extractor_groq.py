# backend/app/chat_service/extractor_groq.py
# Groq-based extractor — replaces the local Ollama extractor.py
# Same interface: extract(user_text) -> (coin, currency, intent)

import os
import json
from typing import Tuple, Dict
from groq import AsyncGroq

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Allowed values
COINS = {"bitcoin", "ethereum", "solana"}
CURRENCIES = {"usd", "inr", "eur"}
INTENTS = {"price", "trend", "summary", "general"}

# Regex fallback maps
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
    "trend": [
        "trend",
        "direction",
        "moving",
        "momentum",
        "going",
        "up or down",
        "up/down",
    ],
    "summary": ["summary", "summarize", "overview", "what happened"],
}

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable is not set.")
        _client = AsyncGroq(api_key=api_key)
    return _client


async def _llm_extract_json(user_text: str) -> Dict:
    """
    Ask Groq to extract coin, currency, intent from the user's question.
    Returns a dict or empty dict on failure (triggers regex fallback).
    """
    system_prompt = (
        "You are a small extraction assistant. "
        "Extract fields from the user's question and return ONLY valid JSON — "
        "no explanation, no extra text, no code fences."
    )

    user_prompt = f"""Extract the following fields and return ONLY valid JSON:

                    Fields:
                    - coin: one of ["bitcoin","ethereum","solana"]
                    - currency: one of ["usd","inr","eur"]
                    - intent: one of ["price","trend","summary","general"]

                    Rules:
                    - If coin is not mentioned, default to "bitcoin".
                    - If currency is not mentioned, default to "usd".
                    - If intent is unclear, choose "general".
                    - Output only valid JSON, no code fences.

                    User question: \"\"\"{user_text}\"\"\""""

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=100,
            temperature=0.0,
        )
        raw = response.choices[0].message.content.strip()

        # Extract JSON substring defensively
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start : end + 1])
    except Exception:
        pass

    return {}


def _regex_fallback(user_text: str) -> Dict:
    """Same regex fallback as the original extractor.py."""
    text = user_text.lower()

    detected_coin = None
    for coin, aliases in COIN_ALIASES.items():
        if any(a in text for a in aliases):
            detected_coin = coin
            break

    detected_currency = None
    for cur, aliases in CURRENCY_ALIASES.items():
        if any(a in text for a in aliases):
            detected_currency = cur
            break

    detected_intent = None
    for intent, keys in INTENT_KEYWORDS.items():
        if any(k in text for k in keys):
            detected_intent = intent
            break

    return {
        "coin": detected_coin or "bitcoin",
        "currency": detected_currency or "usd",
        "intent": detected_intent or "general",
    }


async def extract(user_text: str) -> Tuple[str, str, str]:
    """
    Returns (coin, currency, intent).
    Uses Groq LLM first, falls back to regex on failure.
    Same interface as the original extract() in extractor.py.
    """
    try:
        parsed = await _llm_extract_json(user_text)
        if parsed:
            coin = str(parsed.get("coin", "")).lower()
            currency = str(parsed.get("currency", "")).lower()
            intent = str(parsed.get("intent", "")).lower()

            # Validate against allowed values
            if coin in COINS and currency in CURRENCIES and intent in INTENTS:
                return coin, currency, intent
    except Exception:
        pass

    fb = _regex_fallback(user_text)
    return fb["coin"], fb["currency"], fb["intent"]


__all__ = ["extract"]
