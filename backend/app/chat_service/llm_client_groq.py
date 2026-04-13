# backend/app/chat_service/llm_client_groq.py
# Groq-based LLM client — replaces the local Ollama llm_client.py
# Switch to this file by importing from llm_client_groq instead of llm_client

import os
from groq import AsyncGroq

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY environment variable is not set. "
                "Create a key at https://console.groq.com and add it to your .env file."
            )
        _client = AsyncGroq(api_key=api_key)
    return _client


async def explain_with_llm(
    summary_text: str, user_question: str, max_tokens: int = 400
) -> str:
    """
    Ask Groq to produce a short, safe natural-language explanation
    based ONLY on summary_text (same interface as the Ollama version).
    """
    system_prompt = (
        "You are FinBot, a concise cryptocurrency assistant. "
        "Use ONLY the facts provided by the user — do NOT invent additional numbers or prices."
    )

    user_prompt = f"""Below are verified facts:
                    {summary_text}

                    User question: "{user_question}"

                    Instructions:
                    - Use only the facts provided above.
                    - Provide a short, factual answer (1-5 sentences) addressing the user's question.
                    - If the question asks for a conversion or data not present, say you cannot convert and explain how to get that data.
                    - Do NOT add any extra numerical claims outside the facts above.
                    - Keep the answer helpful and concise."""

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"LLM request failed: {e}"


__all__ = ["explain_with_llm"]
