import httpx
import pandas as pd
from .models import AnalysisResult

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

_cache = {}
CACHE_TTL = 60


async def fetch_simple_price(ids, vs_currencies):
    """
    Fetch current price data for given crypto IDs from CoinGecko.
    """
    ids_str = ",".join(ids)
    vs_str = ",".join(vs_currencies)
    url = f"{COINGECKO_BASE}/simple/price?ids={ids_str}&vs_currencies={vs_str}"
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


async def fetch_market_history(coin_id: str, vs_currency="usd", days=7):
    """
    Fetch historical market data (prices) for a given coin and period.
    Uses CoinGecko's market_chart endpoint.
    """

    cache_key = f"{coin_id}_{vs_currency}_{days}"
    now = time.time()

    # Return cached result if fresh
    if cache_key in _cache:
        cached_time, cached_data = _cache[cache_key]
        if now - cached_time < CACHE_TTL:
            return cached_data

    url = f"{COINGECKO_BASE}/coins/{coin_id}/market_chart?vs_currency={vs_currency}&days={days}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    # Extract price points: [ [timestamp_ms, price], ... ]
    prices = data.get("prices", [])
    if not prices:
        return [], None

    # Convert to DataFrame for analysis
    df = pd.DataFrame(prices, columns=["ts_ms", "price"])
    df["ts"] = pd.to_datetime(df["ts_ms"], unit="ms")
    # Take mean for every interval to reduce noise and also easy to plot
    df = df.set_index("ts").resample("1h").mean().ffill()

    first_price = float(df["price"].iloc[0])
    last_price = float(df["price"].iloc[-1])
    pct_change = (
        ((last_price - first_price) / first_price) * 100 if first_price != 0 else None
    )

    analysis = AnalysisResult(
        first_price=round(first_price, 4),
        last_price=round(last_price, 4),
        pct_change=round(pct_change, 3) if pct_change else None,
        points=len(df),
    )

    # Convert subset for plotting
    points = df.reset_index()[["ts", "price"]].tail(200).to_dict(orient="records")

    _cache[cache_key] = (now, (points, analysis))

    return points, analysis
