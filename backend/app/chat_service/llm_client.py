# import httpx

# OLLAMA_API = "http://127.0.0.1:11434/api/generate"
# MODEL_NAME = "llama3:8b"


# async def query_llm(user_message: str) -> str:
#     """
#     Query the local Ollama LLM and include live Bitcoin data in context.
#     """

#     # Fetch live BTC data
#     try:
#         async with httpx.AsyncClient(timeout=30) as client:
#             res = await client.get(
#                 "http://127.0.0.1:8000/history/bitcoin?vs_currency=usd&days=1"
#             )
#             res.raise_for_status()
#             data = res.json()
#             # DEBUG: print the raw JSON top-level keys
#             print("DEBUG: /history response keys:", list(data.keys()))
#             data_points = data["prices"][-10:]  # last 10 entries
#     except Exception as e:
#         data_points = []
#         trend_text = f"(Could not fetch live BTC data: {e})"
#         print("DEBUG: failed to fetch history:", e)

#     # Format data for the LLM
#     print("DEBUG: data_points type:", type(data_points))
#     print("DEBUG: number of data_points:", len(data_points))
#     if len(data_points) > 0:
#         # show first/last samples for inspection
#         print("DEBUG: first point:", data_points[0])
#         print("DEBUG: last point:", data_points[-1])

#     if data_points:
#         formatted_rows = "\n".join(
#             [f"{row['ts']} → {row['price']}" for row in data_points]
#         )
#         prices_only = [row["price"] for row in data_points]

#         first_price = prices_only[0]
#         last_price = prices_only[-1]
#         pct_change = (last_price - first_price) / first_price * 100
#         trend_icon = "📈" if last_price > first_price else "📉"
#         trend_text = "UP" if last_price > first_price else "DOWN"

#         summary_text = f"""
#         First Price: {first_price:.2f} USD
#         Last Price: {last_price:.2f} USD
#         Change (%): {pct_change:.2f}%
#         Trend: {trend_text} {trend_icon}
#         """

#         # Detect trend
#         trend = "UP" if prices_only[-1] > prices_only[0] else "DOWN"
#         trend_icon = "📈" if trend == "UP" else "📉"

#         trend_text = (
#             f"Detected Trend: {trend_icon} {trend}\n"
#             f"First Price: {prices_only[0]}\n"
#             f"Last Price: {prices_only[-1]}\n"
#         )
#     else:
#         formatted_rows = "(No price data available)"

#     # Build the prompt
#     prompt = f"""
#     You are FinBot, a financial assistant specializing in cryptocurrency analysis.

#     Below is the recent Bitcoin price data (last 10 hours):

#     {formatted_rows}

#     {trend_text}

#     {summary_text}
#     User question: "{user_message}"

#     Instructions:
#     - Only use the numbers provided above.
#     - Do NOT invent data or current prices.
#     - Analyze trends strictly based on the provided data.
#     - If the question is unrelated to Bitcoin or trends, politely explain.
#     """
#     print("DEBUG: prompt length:", len(prompt))
#     # Send prompt to Ollama LLM
#     try:
#         payload = {
#             "model": MODEL_NAME,
#             "prompt": prompt,
#             "stream": False
#         }

#         async with httpx.AsyncClient(timeout=120) as client:
#             resp = await client.post(OLLAMA_API, json=payload)
#             resp.raise_for_status()
#             data = resp.json()
#             print("DEBUG: Ollama raw response keys:", list(data.keys()) if isinstance(data, dict) else type(data))
#             reply = data.get("response", "") if isinstance(data, dict) else str(data)
#             print("DEBUG: reply (truncated):", str(reply)[:300])
#             return reply.strip()

#     except Exception as e:
#         return f"LLM request failed: {e}"


# __all__ = ["query_llm"]




# backend/app/chat_service/llm_client.py
import httpx
import json
from typing import Dict

OLLAMA_API = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "llama3:8b"

async def explain_with_llm(summary_text: str, user_question: str, max_tokens: int = 400) -> str:
    """
    Ask the local model to produce a short, safe natural-language explanation based ONLY on summary_text.
    summary_text must contain numeric facts (first/last/percent/trend).
    """
    prompt = f"""
        You are FinBot, a concise cryptocurrency assistant.

        Below are verified facts (do NOT invent additional numbers):
        {summary_text}

        User question: "{user_question}"

        Instructions:
        - Use only the facts provided above.
        - Provide a short, factual answer (1-5 sentences) addressing the user's question.
        - If the question asks for a conversion or data not present, say you cannot convert and explain how to get that data.
        - Do NOT add any extra numerical claims outside the facts above.
        - Keep the answer helpful and concise.
        """

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(OLLAMA_API, json={"model": MODEL_NAME, "prompt": prompt, "stream": False})
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data.get("response", "").strip()
            return str(data)
    except Exception as e:
        return f"LLM request failed: {e}"
