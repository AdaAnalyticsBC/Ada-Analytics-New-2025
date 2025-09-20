# Microservices Testing Guide

## Service Overview
- **Data Service**: `http://127.0.0.1:8000`
- **Backtesting Service**: `http://127.0.0.1:8001`
- **Strategy Service**: `http://127.0.0.1:8002`

## 1. Test Service Health

### Check if all services are running:
```bash
# Data Service
curl http://127.0.0.1:8000/

# Backtesting Service
curl http://127.0.0.1:8001/

# Strategy Service
curl http://127.0.0.1:8002/
```

## 2. Test Data Service

### Get historical data for a single ticker:
```bash
curl "http://127.0.0.1:8000/historical-data/SOXX?timeframe=5Y"
```

### Get strategy historical data (multiple tickers):
```bash
curl "http://127.0.0.1:8000/strategy/nancy-p-chips/historical-data?timeframe=1Y&tickers=SOXX,NVDA,AMD"
```

### Get strategy chart data:
```bash
curl "http://127.0.0.1:8000/strategy/nancy-p-chips/chart-data?timeframe=1Y&benchmark=SPY"
```

## 3. Test Backtesting Service

### Submit a backtest job:
```bash
curl -X POST "http://127.0.0.1:8001/backtest" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "nancy-p-chips",
    "initial_cash": 10000,
    "lookback": "5Y",
    "benchmark": "SPY",
    "risk_free_rate": 0.02
  }'
```

### Check backtest status (replace {backtest_id} with actual ID):
```bash
curl "http://127.0.0.1:8001/backtest/{backtest_id}/status"
```

### Get backtest results:
```bash
curl "http://127.0.0.1:8001/backtest/{backtest_id}"
```

### Get only metrics:
```bash
curl "http://127.0.0.1:8001/backtest/{backtest_id}/metrics"
```

### List running backtests:
```bash
curl "http://127.0.0.1:8001/backtests/running"
```

## 4. Test Strategy Service

### List available strategies:
```bash
curl "http://127.0.0.1:8002/strategies"
```

### Run a strategy backtest:
```bash
curl -X POST "http://127.0.0.1:8002/strategies/nancy-p-chips/run"
```

### Check strategy status:
```bash
curl "http://127.0.0.1:8002/strategies/nancy-p-chips/status"
```

## 5. Test Service Integration

### End-to-End Strategy Analysis Flow:

1. **Submit backtest via Strategy Service:**
```bash
RESPONSE=$(curl -s -X POST "http://127.0.0.1:8002/strategies/nancy-p-chips/run")
echo $RESPONSE
```

2. **Get strategy data with backtest integration:**
```bash
# Replace {backtest_id} with ID from step 1
curl "http://127.0.0.1:8000/strategy/nancy-p-chips/performance-data?backtest_id={backtest_id}&include_trades=true"
```

3. **Get chart data with backtest overlay:**
```bash
curl "http://127.0.0.1:8000/strategy/nancy-p-chips/chart-data?backtest_id={backtest_id}&timeframe=1Y"
```

## 6. Test WebSocket Live Data

### Test live data stream:
```bash
# Install websocat if you don't have it: brew install websocat
websocat ws://127.0.0.1:8000/live-data/SOXX
```

## 7. Browser Testing

Open these URLs in your browser to see the API docs:

- Data Service: http://127.0.0.1:8000/docs
- Backtesting Service: http://127.0.0.1:8001/docs
- Strategy Service: http://127.0.0.1:8002/docs

## 8. Python Testing Script

Create and run this test script:

```python
import requests
import json
import time

# Test script
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
```

## 9. Expected Responses

### Healthy Service Response:
```json
{
  "service": "Backtesting Service",
  "version": "1.0.0",
  "endpoints": [...]
}
```

### Strategy Data Response:
```json
{
  "strategy_name": "nancy-p-chips",
  "timeframe": "1Y",
  "tickers": ["SOXX", "NVDA", "AMD"],
  "data": {
    "SOXX": {"ticker": "SOXX", "data": [...]},
    "NVDA": {"ticker": "NVDA", "data": [...]},
    "AMD": {"ticker": "AMD", "data": [...]}
  }
}
```

### Backtest Submission Response:
```json
{
  "backtest_id": "abc123-def456-ghi789",
  "status": "submitted",
  "message": "Backtest for nancy-p-chips submitted successfully"
}
```

## 10. Troubleshooting

### Common Issues:

1. **Service not responding**: Check if service is running on correct port
2. **CORS errors**: Services have CORS enabled for development
3. **Missing data**: Check if data-service has valid API keys
4. **Backtest fails**: Check if strategy files exist in strategy-service

### Debug Commands:
```bash
# Check which services are running on which ports
lsof -i :8000
lsof -i :8001
lsof -i :8002

# View service logs (if running with output)
# Run each service in a separate terminal to see logs
```

Start with step 1 (service health) and work your way through the tests!