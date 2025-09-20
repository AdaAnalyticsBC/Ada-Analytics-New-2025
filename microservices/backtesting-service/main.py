from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
import asyncio
import threading
from datetime import datetime, timedelta
import json

app = FastAPI(title="Backtesting Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store running backtests
running_backtests = {}
completed_backtests = {}

class BacktestRequest(BaseModel):
    strategy_name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_cash: float = 10000.0
    lookback: Optional[str] = "5Y"
    benchmark: Optional[str] = "SPY"
    risk_free_rate: Optional[float] = 0.02

@app.get("/")
async def root():
    return {
        "service": "Backtesting Service",
        "version": "1.0.0",
        "endpoints": [
            "POST /backtest - Submit backtest job",
            "GET /backtest/{backtest_id} - Get backtest results",
            "GET /backtest/{backtest_id}/status - Get backtest status",
            "GET /backtest/{backtest_id}/metrics - Get performance metrics",
            "GET /backtest/{backtest_id}/trades - Get trade history",
            "POST /backtest/compare - Compare multiple strategies",
            "GET /backtests/running - List running backtests"
        ]
    }

@app.post("/backtest")
async def submit_backtest(request: BacktestRequest, background_tasks: BackgroundTasks):
    """Submit a new backtest job"""
    backtest_id = str(uuid.uuid4())

    # Initialize backtest status
    running_backtests[backtest_id] = {
        "id": backtest_id,
        "status": "initializing",
        "strategy_name": request.strategy_name,
        "submitted_at": datetime.now().isoformat(),
        "progress": 0.0,
        "request": request.dict()
    }

    # Start backtest in background
    background_tasks.add_task(run_backtest, backtest_id, request)

    return {
        "backtest_id": backtest_id,
        "status": "submitted",
        "message": f"Backtest for {request.strategy_name} submitted successfully"
    }

@app.get("/backtest/{backtest_id}/status")
async def get_backtest_status(backtest_id: str):
    """Get the status of a backtest"""
    if backtest_id in running_backtests:
        return running_backtests[backtest_id]
    elif backtest_id in completed_backtests:
        return {
            "id": backtest_id,
            "status": "completed",
            "completed_at": completed_backtests[backtest_id].get("completed_at"),
            "progress": 100.0
        }
    else:
        raise HTTPException(status_code=404, detail="Backtest not found")

@app.get("/backtest/{backtest_id}")
async def get_backtest_results(backtest_id: str):
    """Get complete backtest results"""
    if backtest_id not in completed_backtests:
        if backtest_id in running_backtests:
            raise HTTPException(status_code=202, detail="Backtest still running")
        else:
            raise HTTPException(status_code=404, detail="Backtest not found")

    return completed_backtests[backtest_id]

@app.get("/backtest/{backtest_id}/metrics")
async def get_backtest_metrics(backtest_id: str):
    """Get performance metrics only"""
    if backtest_id not in completed_backtests:
        raise HTTPException(status_code=404, detail="Backtest not found or not completed")

    results = completed_backtests[backtest_id]
    return {
        "backtest_id": backtest_id,
        "metrics": results.get("metrics", {}),
        "benchmark_metrics": results.get("benchmark_metrics", {}),
        "risk_metrics": results.get("risk_metrics", {})
    }

@app.get("/backtest/{backtest_id}/trades")
async def get_backtest_trades(backtest_id: str):
    """Get trade history"""
    if backtest_id not in completed_backtests:
        raise HTTPException(status_code=404, detail="Backtest not found or not completed")

    results = completed_backtests[backtest_id]
    return {
        "backtest_id": backtest_id,
        "trades": results.get("trades", []),
        "trade_summary": results.get("trade_summary", {})
    }

@app.get("/backtests/running")
async def list_running_backtests():
    """List all running backtests"""
    return {
        "running_backtests": list(running_backtests.values()),
        "count": len(running_backtests)
    }

@app.post("/backtest/compare")
async def compare_backtests(backtest_ids: List[str]):
    """Compare multiple completed backtests"""
    comparison_data = []

    for backtest_id in backtest_ids:
        if backtest_id in completed_backtests:
            results = completed_backtests[backtest_id]
            comparison_data.append({
                "backtest_id": backtest_id,
                "strategy_name": results.get("strategy_name"),
                "metrics": results.get("metrics", {}),
                "benchmark_metrics": results.get("benchmark_metrics", {})
            })
        else:
            comparison_data.append({
                "backtest_id": backtest_id,
                "error": "Backtest not found or not completed"
            })

    return {
        "comparison": comparison_data,
        "generated_at": datetime.now().isoformat()
    }

async def run_backtest(backtest_id: str, request: BacktestRequest):
    """Execute the backtest in background - placeholder implementation"""
    try:
        # Update status
        running_backtests[backtest_id]["status"] = "running"
        running_backtests[backtest_id]["progress"] = 50.0

        # Simulate backtest execution (will be replaced with actual engine)
        await asyncio.sleep(2)  # Simulate processing time

        # Mock results for now
        results = {
            "metrics": {
                "total_return": 0.15,
                "annualized_return": 0.12,
                "sharpe_ratio": 1.2,
                "max_drawdown": -0.08
            },
            "trades": [],
            "daily_values": []
        }

        running_backtests[backtest_id]["progress"] = 100.0

        # Store results
        completed_backtests[backtest_id] = {
            "backtest_id": backtest_id,
            "strategy_name": request.strategy_name,
            "completed_at": datetime.now().isoformat(),
            "request": request.dict(),
            **results
        }

        # Remove from running
        del running_backtests[backtest_id]

    except Exception as e:
        # Handle error
        running_backtests[backtest_id]["status"] = "error"
        running_backtests[backtest_id]["error_message"] = str(e)
        print(f"Backtest {backtest_id} failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)