# ---- I M P O R T S  ---- #
from datetime import datetime, timedelta
from polygon import RESTClient
from pandas_market_calendars import get_calendar
import re
import os
from dotenv import load_dotenv

load_dotenv()

# ---- C O N S T A N T S ---- #
MAX_CANDLE_LIMIT = 300
ALLOWED_UNITS = {"minute", "hour", "day", "week", "month", "quarter", "year"}

# ---- P O L Y G O N  ---- #
POLYGON_KEY = os.getenv("POLYGON_API_KEY")
polygon_client = RESTClient(POLYGON_KEY)

# ---- M A R K E T  C A L ---- #
nyse = get_calendar("XNYS")


# ---- H E L P E R S  ---- #

def parse_timeframe(tf: str):
    m = re.match(r"(\d+)\s*(minute|min|hour|day|week|month|year)s?", tf.strip().lower())
    if not m:
        raise ValueError(f"Invalid timeframe string: '{tf}'")

    quantity = int(m.group(1))
    unit_raw = m.group(2)

    unit = {
        "min": "minute",
        "minute": "minute",
        "hour": "hour",
        "day": "day",
        "week": "week",
        "month": "month",
        "year": "year"
    }[unit_raw]

    if unit not in ALLOWED_UNITS:
        raise ValueError(f"Unsupported unit: {unit}")

    return quantity, unit


def resolve_lookback_window(quantity: int, unit: str):
    """
    Determine the appropriate multiplier and unit so we return up to MAX_CANDLE_LIMIT data points.
    This ensures:
    - More data points for larger timeframes (e.g., '10 years' yields ~300 months)
    - Less data for small timeframes (e.g., '7 days' yields daily/hourly data)
    """
    now = datetime.today().date()

    if unit == "minute":
        total_days = max(1, (quantity * 1) // 1440)  # 1440 minutes/day
        granularity = ("minute", 15)
    elif unit == "hour":
        total_days = max(1, quantity // 24)
        granularity = ("minute", 30)
    elif unit == "day":
        total_days = quantity
        granularity = ("day", 1)
    elif unit == "week":
        total_days = quantity * 7
        granularity = ("day", 1)
    elif unit == "month":
        total_days = quantity * 30
        granularity = ("week", 1)
    elif unit == "year":
        total_days = quantity * 365
        granularity = ("month", 1)
    else:
        total_days = quantity * 30
        granularity = ("month", 1)

    # Apply lookback window that ensures we don’t exceed 300 candles
    _, mult = granularity
    candle_span_days = total_days / MAX_CANDLE_LIMIT
    start_date = now - timedelta(days=int(total_days))
    return granularity[1], granularity[0], start_date.isoformat(), now.isoformat()


def get_polygon_aggregates(ticker: str, mult: int, unit: str, start: str, end: str):
    if unit not in ALLOWED_UNITS:
        return {"error": "Invalid unit", "details": f"Unit '{unit}' not allowed by Polygon"}

    try:
        aggs = [
            {
                "open": a.open,
                "high": a.high,
                "low": a.low,
                "close": a.close,
                "volume": a.volume,
                "timestamp": a.timestamp
            }
            for a in polygon_client.list_aggs(
                ticker,
                mult,
                unit,
                start,
                end,
                adjusted=True,
                sort="asc",
                limit=MAX_CANDLE_LIMIT
            )
        ]
    except Exception as e:
        return {"error": "Polygon API error", "details": str(e)}

    return aggs