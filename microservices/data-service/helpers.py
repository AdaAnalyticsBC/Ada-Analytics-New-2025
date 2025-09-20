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

    end_date = datetime.today().date()
    start_estimate = end_date - timedelta(days=365 * 10)
    schedule = nyse.valid_days(start_estimate, end_date)

    if unit == "day":
        num_bars = quantity
    elif unit == "week":
        num_bars = quantity * 5
    elif unit == "month":
        num_bars = quantity * 21
    elif unit == "year":
        num_bars = quantity * 252
    else:
        num_bars = quantity

    actual_days = list(schedule)[-num_bars:]
    if not actual_days:
        raise ValueError("No valid NYSE trading days in range.")

    return quantity, unit, actual_days[0].date().isoformat(), end_date.isoformat(), len(actual_days)


def resolve_lookback_window(quantity: int, unit: str):
    now = datetime.today().date()
    
    # Estimate total days from timeframe
    if unit == "minute":
        total_days = max(1, (quantity * 1) // 1440)
    elif unit == "hour":
        total_days = max(1, quantity // 24)
    elif unit == "day":
        total_days = quantity
    elif unit == "week":
        total_days = quantity * 7
    elif unit == "month":
        total_days = quantity * 30
    elif unit == "year":
        total_days = quantity * 365
    else:
        total_days = quantity * 30

    # Determine the smallest granularity that keeps us under MAX_CANDLE_LIMIT
    if total_days <= 5:
        unit_final, mult = "minute", 5
    elif total_days <= 20:
        unit_final, mult = "hour", 1
    elif total_days <= 60:
        unit_final, mult = "day", 1
    elif total_days <= 180:
        unit_final, mult = "day", 2
    elif total_days <= 365:
        unit_final, mult = "day", 3
    elif total_days <= 730:
        unit_final, mult = "day", 5
    elif total_days <= 1095:
        unit_final, mult = "week", 1
    elif total_days <= 1825:
        unit_final, mult = "week", 2
    else:
        unit_final, mult = "month", 1

    start_date = now - timedelta(days=int(total_days))
    return mult, unit_final, start_date.isoformat(), now.isoformat()


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