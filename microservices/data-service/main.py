# ---- I M P O R T S ---- #
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from helper_functions import parse_timeframe, resolve_lookback_window, get_polygon_aggregates
from dotenv import load_dotenv
import redis
import os

load_dotenv()

# ---- R E D I S ---- #
r = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=11515,
    decode_responses=True,
    username="default",
    password=os.getenv('REDIS_PASSWORD'),
)

# ---- F A S T A P I ---- #
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- E N D P O I N T S ---- #

@app.get("/test-redis")
async def test_redis():
    r.set('Foo', 'Bar')
    return {"Message": r.get('Foo')}


@app.get("/historical-data")
async def fetch_historical_data(
    ticker: str = Query(..., description="Ticker symbol, e.g., AAPL"),
    timeframe: str = Query(..., description="Timeframe, e.g., '30days', '6months', '10years'")
):
    try:
        quantity, unit, start, end, total_days = parse_timeframe(timeframe)
        unit, mult = resolve_best_unit(quantity, unit)

        data = get_polygon_aggregates(ticker, mult, unit, start, end)

        if "error" in data:
            return data

        if len(data) == 0:
            return {"error": "No data found — invalid ticker or no trading history."}

        return {
            "ticker": ticker.upper(),
            "unit": unit,
            "multiplier": mult,
            "start": start,
            "end": end,
            "data_points": len(data),
            "data": data,
            "note": f"Results capped to 300 candles"
        }

    except ValueError as ve:
        return {"error": "Invalid timeframe format", "details": str(ve)}
    except Exception as e:
        return {"error": "Unexpected error", "details": str(e)}


@app.get("/live-data")
async def fetch_live_data():
    return {"Message": "Live WebSocket Data Endpoint – not yet implemented"}