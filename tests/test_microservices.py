
import requests
import time
import json

def test_services():
    print("🧪 Testing Microservices...")

    # 1. Test service health
    services = {
        "Data": "http://127.0.0.1:8000",
        "Backtesting": "http://127.0.0.1:8001",
        "Strategy": "http://127.0.0.1:8002"
    }

    for name, url in services.items():
        try:
            response = requests.get(f"{url}/")
            print(f"✅ {name} Service: {response.status_code}")
        except Exception as e:
            print(f"❌ {name} Service: {e}")

    # 2. Test strategy data
    try:
        response = requests.get("http://127.0.0.1:8000/strategy/nancy-p-chips/historical-data?timeframe=1Y")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Strategy Data: {len(data.get('data', {}))} tickers fetched")
        else:
            print(f"❌ Strategy Data: {response.status_code}")
    except Exception as e:
        print(f"❌ Strategy Data: {e}")

    # 3. Test backtest submission
    try:
        backtest_request = {
            "strategy_name": "nancy-p-chips",
            "initial_cash": 10000,
            "lookback": "1Y"
        }
        response = requests.post("http://127.0.0.1:8001/backtest", json=backtest_request)
        if response.status_code == 200:
            result = response.json()
            backtest_id = result.get("backtest_id")
            print(f"✅ Backtest Submitted: {backtest_id}")

            # Check status
            time.sleep(1)
            status_response = requests.get(f"http://127.0.0.1:8001/backtest/{backtest_id}/status")
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"✅ Backtest Status: {status.get('status')}")
        else:
            print(f"❌ Backtest Submission: {response.status_code}")
    except Exception as e:
        print(f"❌ Backtest: {e}")

if __name__ == "__main__":
    test_services()