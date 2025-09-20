from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from helpers import get_timeframe_config, get_polygon_aggregates, get_polygon_live_data, start_polygon_websocket, get_websocket_live_data, is_market_open
import asyncio
import json
from datetime import datetime


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    #TODO: change to whitlist URLS to configure internal APIs only. 
    allow_credentials=True, 
    allow_methods=["*"],    #TODO: Change the method to secure.
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "Message": "Running data-service",
        "Endpoints": [
            "1. /historical-datat/{ticker}",
            "2. /live-data/{ticker}"
        ]
    }

@app.get("/historical-data/{ticker}")
async def fetch_historical_data(
    ticker: str,
    timeframe: str = Query(..., description="1D, 1W, 1M, 3M, 6M, YTD, 3Y, 5Y, 7Y")
):
    try:
        # Get preset timeframe configuration
        mult, unit, start, end, description = get_timeframe_config(timeframe)

        # Fetch candles
        data = get_polygon_aggregates(ticker, mult, unit, start, end)

        if "error" in data:
            return data

        return {
            "ticker": ticker.upper(),
            "timeframe": timeframe.upper(),
            "description": description,
            "unit": unit,
            "multiplier": mult,
            "start": start,
            "end": end,
            "data_points": len(data),
            "data": data
        }

    except ValueError as ve:
        return {"error": "Invalid timeframe", "details": str(ve)}
    except Exception as e:
        return {"error": "Server error", "details": str(e)}



@app.websocket("/live-data/{ticker}")
async def websocket_live_data(websocket: WebSocket, ticker: str):
    print(f"🔗 New websocket connection for {ticker}")
    await websocket.accept()

    polygon_ws_client = None
    connection_status = "initializing"

    try:
        # Send connection attempt status
        status_msg = {
            "status": "connecting",
            "ticker": ticker.upper(),
            "message": "🔄 Attempting to connect to Polygon websocket...",
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send_text(json.dumps(status_msg))

        # Check if market is open - only connect to websocket during market hours
        market_open = is_market_open()

        if market_open:
            # Start Polygon websocket connection for this ticker
            try:
                polygon_ws_client = await start_polygon_websocket(ticker.upper())

                if polygon_ws_client:
                    connection_status = "connected"
                    success_msg = {
                        "status": "connected",
                        "ticker": ticker.upper(),
                        "message": f"✅ Connected to live feed for {ticker.upper()} (market open)",
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send_text(json.dumps(success_msg))
                else:
                    connection_status = "failed"
                    fail_msg = {
                        "status": "connection_failed",
                        "ticker": ticker.upper(),
                        "message": "❌ Failed to connect to websocket. Using REST fallback.",
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send_text(json.dumps(fail_msg))

            except Exception as ws_error:
                connection_status = "failed"
                fail_msg = {
                    "status": "connection_error",
                    "ticker": ticker.upper(),
                    "message": f"❌ Websocket error: {str(ws_error)}. Using REST fallback.",
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send_text(json.dumps(fail_msg))
        else:
            # Market closed - skip websocket, use REST only
            connection_status = "failed"
            market_closed_msg = {
                "status": "market_closed",
                "ticker": ticker.upper(),
                "message": "🌙 Market closed. Using previous close data only.",
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_text(json.dumps(market_closed_msg))

        data_count = 0
        last_data_hash = None
        market_status_sent = False

        while True:
            current_data = None
            should_send = False

            # Check market status
            market_open = is_market_open()

            if connection_status == "connected":
                # Get latest websocket data from Polygon
                current_data = get_websocket_live_data(ticker.upper())
                current_data["connection_status"] = "🟢 Websocket Active"
                current_data["data_source"] = "polygon_websocket"

                # Check if we're actually receiving data
                if current_data.get("type") == "no_data":
                    if not market_open:
                        current_data["message"] = "🌙 Market is closed. Data will resume during market hours (9:30 AM - 4:00 PM ET)"
                    else:
                        current_data["message"] = f"⏳ Waiting for data... (15min delay on free tier)"
                else:
                    current_data["message"] = f"📈 Live data streaming (15min delayed)"

            else:
                # Fallback to REST API
                current_data = get_polygon_live_data(ticker.upper())
                current_data["connection_status"] = "🟡 REST Fallback"
                current_data["data_source"] = "polygon_rest"

                if not market_open:
                    current_data["message"] = "🌙 Market is closed. Using previous close data."
                else:
                    current_data["message"] = "Using REST API fallback (less frequent updates)"

            # Add market status
            current_data["market_open"] = market_open
            current_data["timestamp"] = datetime.now().isoformat()

            # Create a hash of the relevant data to detect changes
            # Only include trade/quote data, not timestamps or counters
            data_to_hash = {
                "trade": current_data.get("trade"),
                "quote": current_data.get("quote"),
                "market_open": market_open,
                "connection_status": current_data.get("connection_status"),
                "type": current_data.get("type")
            }
            current_hash = hash(str(data_to_hash))

            # Send data if:
            # 1. It's the first message
            # 2. The data has changed
            # 3. Market status changed and we haven't sent a market status update yet
            if (last_data_hash is None or
                current_hash != last_data_hash or
                (not market_open and not market_status_sent)):

                current_data["data_count"] = data_count
                await websocket.send_text(json.dumps(current_data))

                last_data_hash = current_hash
                data_count += 1

                if not market_open:
                    market_status_sent = True

            # Reset market status flag when market opens
            if market_open and market_status_sent:
                market_status_sent = False

            # Wait 3 seconds before checking for updates (shorter for responsiveness)
            await asyncio.sleep(3)

    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected for ticker: {ticker}")
    except Exception as e:
        error_msg = {
            "status": "error",
            "ticker": ticker.upper(),
            "connection_status": "❌ Error",
            "message": f"💥 Live data error: {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "error_details": str(e)
        }
        await websocket.send_text(json.dumps(error_msg))
        await websocket.close()


