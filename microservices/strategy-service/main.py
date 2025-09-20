from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import sys
import subprocess
import threading
import asyncio
from typing import Dict, Any
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    #TODO: change to whitlist URLS to configure internal APIs only.
    allow_credentials=True,
    allow_methods=["*"],    #TODO: Change the method to secure.
    allow_headers=["*"],
)

# Store running strategy instances
running_strategies = {}

@app.get("/")
async def root():
    return {
        "Message": "Running strategy-service",
        "Endpoints": [
            "1. GET /strategies - List available strategies",
            "2. POST /strategies/{strategy_name}/run - Run a strategy backtest",
            "3. GET /strategies/{strategy_name}/status - Get strategy status",
            "4. GET /strategies/running - List running strategies"
        ]
    }

@app.get("/strategies")
async def list_strategies():
    """List all available strategies"""
    strategies_dir = "strategies"
    if not os.path.exists(strategies_dir):
        return {"strategies": []}

    strategies = []
    for item in os.listdir(strategies_dir):
        strategy_path = os.path.join(strategies_dir, item)
        if os.path.isdir(strategy_path):
            # Look for strategy files
            test_file = os.path.join(strategy_path, "test_strategy.py")
            config_file = os.path.join(strategy_path, "config.yaml")

            if os.path.exists(test_file) or os.path.exists(config_file):
                strategies.append({
                    "name": item,
                    "has_test": os.path.exists(test_file),
                    "has_config": os.path.exists(config_file),
                    "path": strategy_path
                })

    return {"strategies": strategies}

@app.post("/strategies/{strategy_name}/run")
async def run_strategy(strategy_name: str):
    """Run a strategy backtest"""
    strategy_path = os.path.join("strategies", strategy_name)
    test_file = os.path.join(strategy_path, "test_strategy.py")

    if not os.path.exists(strategy_path):
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")

    if not os.path.exists(test_file):
        raise HTTPException(status_code=404, detail=f"Test file not found for strategy '{strategy_name}'")

    # Check if strategy is already running
    if strategy_name in running_strategies:
        return JSONResponse(
            status_code=409,
            content={"error": f"Strategy '{strategy_name}' is already running", "strategy_id": running_strategies[strategy_name]["id"]}
        )

    try:
        # Start strategy in background
        strategy_id = f"{strategy_name}_{len(running_strategies)}"

        def run_strategy_subprocess():
            try:
                # Activate virtual environment and run strategy
                venv_path = os.path.join(os.getcwd(), ".venv", "bin", "activate")
                cmd = f"cd {strategy_path} && source {venv_path} && python3 test_strategy.py"

                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=strategy_path
                )

                # Store results
                running_strategies[strategy_name]["status"] = "completed"
                running_strategies[strategy_name]["output"] = result.stdout
                running_strategies[strategy_name]["error"] = result.stderr
                running_strategies[strategy_name]["return_code"] = result.returncode

            except Exception as e:
                running_strategies[strategy_name]["status"] = "error"
                running_strategies[strategy_name]["error"] = str(e)

        # Store strategy info
        running_strategies[strategy_name] = {
            "id": strategy_id,
            "status": "running",
            "output": "",
            "error": "",
            "return_code": None
        }

        # Start background thread
        thread = threading.Thread(target=run_strategy_subprocess)
        thread.daemon = True
        thread.start()

        return {
            "message": f"Strategy '{strategy_name}' started successfully",
            "strategy_id": strategy_id,
            "status": "running"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start strategy: {str(e)}")

@app.get("/strategies/{strategy_name}/status")
async def get_strategy_status(strategy_name: str):
    """Get the status of a running strategy"""
    if strategy_name not in running_strategies:
        raise HTTPException(status_code=404, detail=f"No running strategy found for '{strategy_name}'")

    strategy_info = running_strategies[strategy_name]

    return {
        "strategy_name": strategy_name,
        "strategy_id": strategy_info["id"],
        "status": strategy_info["status"],
        "output": strategy_info["output"][-2000:] if strategy_info["output"] else "",  # Last 2000 chars
        "error": strategy_info["error"][-1000:] if strategy_info["error"] else "",     # Last 1000 chars
        "return_code": strategy_info["return_code"]
    }

@app.get("/strategies/running")
async def list_running_strategies():
    """List all currently running strategies"""
    return {
        "running_strategies": [
            {
                "name": name,
                "id": info["id"],
                "status": info["status"]
            }
            for name, info in running_strategies.items()
        ]
    }

@app.delete("/strategies/{strategy_name}")
async def stop_strategy(strategy_name: str):
    """Stop a running strategy"""
    if strategy_name not in running_strategies:
        raise HTTPException(status_code=404, detail=f"No running strategy found for '{strategy_name}'")

    # Remove from running strategies (simple implementation)
    del running_strategies[strategy_name]

    return {"message": f"Strategy '{strategy_name}' stopped successfully"}