# ---- I M P O R T S  ---- #
from datetime import datetime, timedelta
from polygon import RESTClient, WebSocketClient
from polygon.websocket.models import WebSocketMessage, EquityTrade, EquityQuote
from pandas_market_calendars import get_calendar
import re
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

# ---- C O N S T A N T S ---- #
MAX_CANDLE_LIMIT = 300
ALLOWED_UNITS = {"minute", "hour", "day", "week", "month", "quarter", "year"}

# ---- P O L Y G O N  ---- #
POLYGON_KEY = os.getenv("POLYGON_API_KEY")
polygon_client = RESTClient(POLYGON_KEY)

# ---- W E B S O C K E T ---- #
websocket_data = {}
websocket_connections = {}

# ---- M A R K E T  C A L ---- #
nyse = get_calendar("XNYS")

# ---- H E L P E R S  ---- #

def is_market_open():
    """Check if the market is currently open"""
    now = datetime.now()
    # Market hours: 9:30 AM - 4:00 PM ET, Monday-Friday

    # Check if it's a weekday
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False

    # Simple time check (assumes ET timezone - could be enhanced)
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

    return market_open <= now <= market_close

def get_timeframe_config(timeframe: str):
    """Get candle configuration for preset timeframes (Robinhood style)"""

    tf = timeframe.upper().strip()
    now = datetime.today().date()

    # PRESET TIMEFRAMES
    configs = {
        "1D": {
            "mult": 15,
            "unit": "minute",
            "days_back": 1,
            "description": "1 day, 15-minute candles"
        },
        "1W": {
            "mult": 1,
            "unit": "hour",
            "days_back": 7,
            "description": "1 week, 1-hour candles"
        },
        "1M": {
            "mult": 4,
            "unit": "hour",
            "days_back": 30,
            "description": "1 month, 4-hour candles"
        },
        "3M": {
            "mult": 1,
            "unit": "day",
            "days_back": 90,
            "description": "3 months, daily candles"
        },
        "6M": {
            "mult": 1,
            "unit": "day",
            "days_back": 180,
            "description": "6 months, daily candles"
        },
        "YTD": {
            "mult": 1,
            "unit": "day",
            "days_back": (now - datetime(now.year, 1, 1).date()).days,
            "description": "Year-to-date, daily candles"
        },
        "3Y": {
            "mult": 1,
            "unit": "week",
            "days_back": 365 * 3,
            "description": "3 years, weekly candles"
        },
        "5Y": {
            "mult": 1,
            "unit": "week",
            "days_back": 365 * 5,
            "description": "5 years, weekly candles"
        },
        "7Y": {
            "mult": 1,
            "unit": "month",
            "days_back": 365 * 7,
            "description": "7 years, monthly candles"
        }
    }

    if tf not in configs:
        raise ValueError(f"Invalid timeframe: {tf}. Valid options: {', '.join(configs.keys())}")

    config = configs[tf]
    start_date = now - timedelta(days=config["days_back"])

    return config["mult"], config["unit"], start_date.isoformat(), now.isoformat(), config["description"]


def calculate_expected_candles(original_quantity: int, original_unit: str, target_mult: int = 1, target_unit: str = None):
    """Calculate expected number of candles for a given timeframe converted to target granularity"""

    # If no target unit specified, use original unit
    if target_unit is None:
        target_unit = original_unit

    # Convert original timeframe to total minutes
    if original_unit == "minute":
        total_minutes = original_quantity
    elif original_unit == "hour":
        total_minutes = original_quantity * 60
    elif original_unit == "day":
        total_minutes = original_quantity * 390  # 390 trading minutes per day
    elif original_unit == "week":
        total_minutes = original_quantity * 5 * 390  # 5 trading days per week
    elif original_unit == "month":
        total_minutes = original_quantity * 21 * 390  # 21 trading days per month
    elif original_unit == "year":
        total_minutes = original_quantity * 252 * 390  # 252 trading days per year
    else:
        total_minutes = original_quantity * 390  # Default to days

    # Convert to target unit
    if target_unit == "minute":
        target_minutes_per_candle = target_mult
    elif target_unit == "hour":
        target_minutes_per_candle = target_mult * 60
    elif target_unit == "day":
        target_minutes_per_candle = target_mult * 390
    elif target_unit == "week":
        target_minutes_per_candle = target_mult * 5 * 390
    elif target_unit == "month":
        target_minutes_per_candle = target_mult * 21 * 390
    elif target_unit == "year":
        target_minutes_per_candle = target_mult * 252 * 390
    else:
        target_minutes_per_candle = target_mult * 390  # Default to days

    return max(1, int(total_minutes / target_minutes_per_candle))


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
    candidates = [
        ("minute", 5), ("minute", 15), ("minute", 30),
        ("hour", 1), ("hour", 4),
        ("day", 1), ("day", 2), ("day", 3), ("day", 5),
        ("week", 1), ("week", 2),
        ("month", 1), ("month", 3)
    ]

    # Find the first candidate that stays under the limit
    for unit_final, mult in candidates:
        expected_candles = calculate_expected_candles(quantity, unit, mult, unit_final)
        if expected_candles <= MAX_CANDLE_LIMIT:
            start_date = now - timedelta(days=int(total_days))
            return mult, unit_final, start_date.isoformat(), now.isoformat()

    # If we can't fit under the limit, use the coarsest granularity available
    # This ensures we still return data, just at the lowest resolution possible
    unit_final, mult = "month", 6  # 6-month candles as last resort
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

        # Safety check: if we somehow got more than the limit, truncate
        if len(aggs) > MAX_CANDLE_LIMIT:
            aggs = aggs[:MAX_CANDLE_LIMIT]

        # If we got exactly the limit, add a warning that data may be truncated
        if len(aggs) == MAX_CANDLE_LIMIT:
            print(f"Warning: Result truncated at {MAX_CANDLE_LIMIT} candles for {ticker}")

    except Exception as e:
        return {"error": "Polygon API error", "details": str(e)}

    return aggs


def get_polygon_live_data(ticker: str):
    try:
        # Use delayed endpoints that work with Standard plan
        # Get previous close (should work with Standard plan)
        try:
            trade = polygon_client.get_last_trade(ticker)
        except Exception:
            trade = None

        try:
            quote = polygon_client.get_last_quote(ticker)
        except Exception:
            quote = None

        # If real-time fails, try previous close as fallback
        if not trade and not quote:
            try:
                # Get previous close price (usually available on Standard plan)
                prev_close = polygon_client.get_previous_close(ticker)
                if prev_close and len(prev_close) > 0:
                    close_data = prev_close[0]
                    trade = type('Trade', (), {
                        'price': close_data.close,
                        'size': close_data.volume,
                        'exchange': 'PREV_CLOSE',
                        'timestamp': close_data.timestamp
                    })()
            except Exception:
                pass

        # Format the live data response
        live_data = {
            "ticker": ticker.upper(),
            "timestamp": datetime.now().isoformat(),
            "quote": {
                "bid": quote.bid,
                "ask": quote.ask,
                "bid_size": quote.bid_size,
                "ask_size": quote.ask_size,
                "exchange": quote.exchange,
                "timestamp": quote.timestamp
            } if quote else None,
            "trade": {
                "price": trade.price,
                "size": trade.size,
                "exchange": trade.exchange,
                "timestamp": trade.timestamp
            } if trade else None
        }

        return live_data

    except Exception as e:
        return {"error": "Polygon live data error", "details": str(e)}




async def listen_to_polygon_messages(websocket, ticker):
    """Listen to messages from Polygon websocket"""
    import json
    try:
        while True:
            message = await websocket.recv()
            data = json.loads(message)

            for event in data:
                if event.get("ev") == "T" and event.get("sym") == ticker:
                    # Trade event
                    price = event.get("p")
                    size = event.get("s")
                    print(f"📈 Trade for {ticker}: ${price} (size: {size})")

                    websocket_data[ticker] = {
                        "ticker": ticker,
                        "timestamp": datetime.now().isoformat(),
                        "type": "trade",
                        "trade": {
                            "price": price,
                            "size": size,
                            "timestamp": event.get("t")
                        }
                    }
    except Exception as e:
        print(f"❌ Error listening to messages: {e}")

async def start_polygon_websocket(ticker: str):
    """Start a raw websocket connection for a specific ticker"""
    import websockets
    import json

    if ticker in websocket_connections:
        print(f"Reusing existing websocket connection for {ticker}")
        return websocket_connections[ticker]

    try:
        print(f"Creating raw websocket connection for {ticker}")

        # Connect to real-time feed
        uri = "wss://socket.polygon.io/stocks"
        ws = await websockets.connect(uri)
        print(f"✅ Connected to {uri}")

        # Authenticate
        auth_msg = {"action": "auth", "params": POLYGON_KEY}
        await ws.send(json.dumps(auth_msg))
        print(f"🔐 Sent authentication")

        # Wait for auth response
        auth_response = await ws.recv()
        print(f"📨 Auth response: {auth_response}")

        # Subscribe to trades for this ticker
        subscribe_msg = {"action": "subscribe", "params": f"T.{ticker}"}
        await ws.send(json.dumps(subscribe_msg))
        print(f"📡 Subscribed to trades for {ticker}")

        # Start listening for messages
        asyncio.create_task(listen_to_polygon_messages(ws, ticker))

        websocket_connections[ticker] = ws
        return ws

    except Exception as e:
        print(f"❌ Error starting websocket for {ticker}: {e}")
        return None


def get_websocket_live_data(ticker: str):
    """Get the latest websocket data for a ticker"""
    return websocket_data.get(ticker, {
        "ticker": ticker,
        "timestamp": datetime.now().isoformat(),
        "type": "no_data",
        "data": None,
        "message": "No recent websocket data available. Data may be 15 minutes delayed."
    })