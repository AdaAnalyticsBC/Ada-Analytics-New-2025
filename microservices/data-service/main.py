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
            "1. /historical-data/{ticker} - Historical market data",
            "2. /live-data/{ticker} - WebSocket live data",
            "3. /strategy/{strategy_name}/historical-data - Strategy historical data",
            "4. /strategy/{strategy_name}/chart-data - Strategy chart data",
            "5. /strategy/{strategy_name}/performance-data - Strategy performance data"
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


# Strategy Backtesting and Chart Data Endpoints

@app.get("/strategy/{strategy_name}/historical-data")
async def get_strategy_historical_data(
    strategy_name: str,
    timeframe: str = Query("5Y", description="Time range for historical data"),
    tickers: str = Query("SOXX,NVDA,AMD", description="Comma-separated list of tickers")
):
    """
    Fetch historical data for all tickers used in a strategy
    Used for backtesting and chart generation
    """
    try:
        ticker_list = [ticker.strip().upper() for ticker in tickers.split(",")]

        strategy_data = {
            "strategy_name": strategy_name,
            "timeframe": timeframe,
            "tickers": ticker_list,
            "data": {},
            "meta": {
                "description": f"Historical data for {strategy_name} strategy",
                "generated_at": datetime.now().isoformat(),
                "timeframe_config": get_timeframe_config(timeframe)
            }
        }

        # Fetch data for each ticker
        for ticker in ticker_list:
            try:
                # Use existing helper function
                ticker_data = await get_polygon_aggregates(ticker, timeframe)
                strategy_data["data"][ticker] = ticker_data
            except Exception as e:
                strategy_data["data"][ticker] = {
                    "error": f"Failed to fetch data for {ticker}: {str(e)}",
                    "ticker": ticker
                }

        return strategy_data

    except Exception as e:
        return {
            "error": f"Failed to fetch strategy historical data: {str(e)}",
            "strategy_name": strategy_name,
            "timeframe": timeframe
        }

@app.get("/strategy/{strategy_name}/chart-data")
async def get_strategy_chart_data(
    strategy_name: str,
    backtest_id: str = Query(None, description="Backtest ID to include backtest results"),
    timeframe: str = Query("1Y", description="Chart timeframe"),
    benchmark: str = Query("SPY", description="Benchmark ticker for comparison")
):
    """
    Fetch chart data for strategy visualization
    Includes historical price data and optionally backtest results
    """
    try:
        # Get strategy configuration (assuming it exists)
        strategy_tickers = get_strategy_tickers(strategy_name)

        chart_data = {
            "strategy_name": strategy_name,
            "backtest_id": backtest_id,
            "timeframe": timeframe,
            "benchmark": benchmark,
            "generated_at": datetime.now().isoformat(),
            "price_data": {},
            "backtest_data": None
        }

        # Fetch price data for main ticker and benchmark
        main_ticker = strategy_tickers[0] if strategy_tickers else "SOXX"

        for ticker in [main_ticker, benchmark]:
            try:
                ticker_data = await get_polygon_aggregates(ticker, timeframe)
                chart_data["price_data"][ticker] = {
                    "ticker": ticker,
                    "data": ticker_data,
                    "role": "main" if ticker == main_ticker else "benchmark"
                }
            except Exception as e:
                chart_data["price_data"][ticker] = {
                    "error": f"Failed to fetch {ticker}: {str(e)}"
                }

        # If backtest_id provided, fetch backtest results from backtesting service
        if backtest_id:
            chart_data["backtest_data"] = await fetch_backtest_results(backtest_id)

        return chart_data

    except Exception as e:
        return {
            "error": f"Failed to generate chart data: {str(e)}",
            "strategy_name": strategy_name
        }

@app.get("/strategy/{strategy_name}/performance-data")
async def get_strategy_performance_data(
    strategy_name: str,
    backtest_id: str = Query(..., description="Backtest ID for performance data"),
    include_trades: bool = Query(False, description="Include detailed trade history"),
    include_daily_values: bool = Query(True, description="Include daily portfolio values")
):
    """
    Fetch comprehensive performance data for a strategy backtest
    Used for detailed performance analysis and charts
    """
    try:
        # Fetch from backtesting service
        backtest_results = await fetch_backtest_results(backtest_id)

        if not backtest_results:
            return {
                "error": f"No backtest results found for ID: {backtest_id}",
                "backtest_id": backtest_id
            }

        performance_data = {
            "strategy_name": strategy_name,
            "backtest_id": backtest_id,
            "generated_at": datetime.now().isoformat(),
            "metrics": backtest_results.get("metrics", {}),
            "benchmark_metrics": backtest_results.get("benchmark_metrics", {}),
            "risk_metrics": backtest_results.get("risk_metrics", {})
        }

        if include_daily_values:
            performance_data["daily_values"] = backtest_results.get("daily_values", [])

        if include_trades:
            performance_data["trades"] = backtest_results.get("trades", [])
            performance_data["trade_summary"] = backtest_results.get("trade_summary", {})

        return performance_data

    except Exception as e:
        return {
            "error": f"Failed to fetch performance data: {str(e)}",
            "backtest_id": backtest_id
        }

# Helper functions for strategy data

def get_strategy_tickers(strategy_name: str) -> list:
    """Get list of tickers used by a strategy"""
    strategy_configs = {
        "nancy-p-chips": ["SOXX", "NVDA", "AMD"],
        "pairs-trading": ["SPY", "QQQ"]
    }
    return strategy_configs.get(strategy_name, ["SOXX"])

async def fetch_backtest_results(backtest_id: str):
    """Fetch backtest results from backtesting service"""
    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:8001/backtest/{backtest_id}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
    except Exception as e:
        print(f"Failed to fetch backtest results: {e}")
        return None


