# ---- I M P O R T S  ---- #
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from polygon import RESTClient
import redis
import os
import re

load_dotenv()

# ---- R E D I S  ---- #
r = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=11515,
    decode_responses=True,
    username="default",
    password=os.getenv('REDIS_PASSWORD'),
)

# ---- F A S T A P I  ---- #
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- P O L Y G O N  ---- #
POLYGON_KEY = os.getenv("POLYGON_API_KEY")
polygon_client = RESTClient(POLYGON_KEY)

# ---- H E L P E R S  ---- #

def parse_timeframe(tf: str, unit: str):
    """
    Parses timeframe string (e.g., '7days', '1month') and returns:
    - multiplier: always 1
    - start: far-back date
    - end: today
    - limit: how many candles (based on unit granularity)
    """
    m = re.match(r"(\d+)\s*(minute|min|hour|day|week|month|year)s?", tf.strip().lower())
    if not m:
        raise ValueError(f"Invalid timeframe string: '{tf}'")

    quantity = int(m.group(1))
    timeframe_unit_raw = m.group(2)
    timeframe_unit = {
        "min": "minute",
        "minute": "minute",
        "hour": "hour",
        "day": "day",
        "week": "week",
        "month": "month",
        "year": "year"
    }[timeframe_unit_raw]

    today = datetime.today()
    if timeframe_unit == "minute":
        delta = timedelta(minutes=quantity)
    elif timeframe_unit == "hour":
        delta = timedelta(hours=quantity)
    elif timeframe_unit == "day":
        delta = timedelta(days=quantity)
    elif timeframe_unit == "week":
        delta = timedelta(weeks=quantity)
    elif timeframe_unit == "month":
        delta = timedelta(days=30 * quantity)  # Optional: make this more precise later
    elif timeframe_unit == "year":
        delta = timedelta(days=365 * quantity)
    else:
        raise ValueError("Invalid timeframe unit")

    start_date = today - delta
    end_date = today

    # calculate expected candle count
    if unit == "minute":
        limit = int((end_date - start_date).total_seconds() // 60)
    elif unit == "hour":
        limit = int((end_date - start_date).total_seconds() // 3600)
    elif unit == "day":
        limit = int((end_date - start_date).days)
    else:
        raise ValueError("Invalid candle unit")

    return 1, unit, start_date.date().isoformat(), end_date.date().isoformat(), limit



def get_polygon_aggregates(ticker: str, mult: int, unit: str, start: str, end: str, limit: int):
    """
    Calls Polygon API, fetches candles from start → end, then returns the latest N (`limit`) candles.
    """
    aggs = []
    try:
        for a in polygon_client.list_aggs(
            ticker,
            mult,
            unit,
            start,
            end,
            adjusted=True,
            sort="asc",
            limit=5000
        ):
            aggs.append({
                "open": a.open,
                "high": a.high,
                "low": a.low,
                "close": a.close,
                "volume": a.volume,
                "timestamp": a.timestamp
            })
    except Exception as e:
        return {"error": "Polygon API error", "details": str(e)}

    return aggs[-limit:]

# ---- E N D P O I N T S  ---- #

# Redis Test
@app.get("/test-redis")
async def test_redis():
    r.set('Foo', 'Bar')
    return {"Message": r.get('Foo')}


# Historical Data
@app.get("/historical-data")
async def fetch_historical_data(
    ticker: str = Query(..., description="Ticker symbol, e.g., AAPL"),
    timeframe: str = Query(..., description="Timeframe, e.g., '30days', '6months'"),
    unit: str = Query("day", description="Candle unit: 'minute', 'hour', or 'day'")
):
    try:
        # Validate unit
        allowed_units = ["minute", "hour", "day"]
        if unit not in allowed_units:
            return {"error": f"Invalid unit. Must be one of: {allowed_units}"}

        mult, unit, start, end, limit = parse_timeframe(timeframe, unit)
        data = get_polygon_aggregates(ticker, mult, unit, start, end, limit)

        if "error" in data:
            return data

        return {
            "ticker": ticker,
            "unit": unit,
            "multiplier": mult,
            "start": start,
            "end": end,
            "data_points": len(data),
            "data": data
        }

    except ValueError as ve:
        return {"error": "Invalid timeframe format", "details": str(ve)}
    except Exception as e:
        return {"error": "Unexpected error", "details": str(e)}


# Live Data Placeholder
@app.get("/live-data")
async def fetch_live_data():
    return {"Message": "Live WebSocket Data Endpoint – not yet implemented"}