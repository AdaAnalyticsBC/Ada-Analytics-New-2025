from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from helpers import parse_timeframe, resolve_lookback_window, get_polygon_aggregates

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/historical-data")
async def fetch_historical_data(
    ticker: str = Query(..., description="e.g., AAPL"),
    timeframe: str = Query(..., description="e.g., 10 years, 30 days")
):
    try:
        # Step 1: Parse timeframe
        quantity, unit, _, _, _ = parse_timeframe(timeframe)

        # Step 2: Resolve candle spacing
        mult, final_unit, start, end = resolve_lookback_window(quantity, unit)

        # Step 3: Fetch candles
        data = get_polygon_aggregates(ticker, mult, final_unit, start, end)

        if "error" in data:
            return data

        return {
            "ticker": ticker.upper(),
            "unit": final_unit,
            "multiplier": mult,
            "start": start,
            "end": end,
            "data_points": len(data),
            "data": data
        }

    except ValueError as ve:
        return {"error": "Invalid timeframe format", "details": str(ve)}
    except Exception as e:
        return {"error": "Server error", "details": str(e)}