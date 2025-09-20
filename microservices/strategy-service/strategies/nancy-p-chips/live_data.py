import websocket
import json
import threading
import time
from datetime import datetime
import yaml

def load_config():
    """Load strategy configuration"""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except:
        return {
            'data_source': {'api_url': 'http://127.0.0.1:8000'}
        }

class LiveDataClient:
    def __init__(self, symbols=['SOXX', 'NVDA', 'AMD']):
        self.symbols = symbols
        self.latest_prices = {}
        self.config = load_config()

        # WebSocket URL - assuming data service has websocket endpoint
        api_url = self.config.get('data_source', {}).get('api_url', 'http://127.0.0.1:8000')
        ws_url = api_url.replace('http://', 'ws://').replace('https://', 'wss://')
        self.ws_url = f"{ws_url}/live-data"

        self.ws = None
        self.connected = False

    def on_message(self, ws, message):
        """Handle incoming websocket messages"""
        try:
            data = json.loads(message)

            if 'symbol' in data and 'price' in data:
                symbol = data['symbol']
                price = float(data['price'])
                timestamp = data.get('timestamp', time.time())

                self.latest_prices[symbol] = {
                    'price': price,
                    'timestamp': timestamp,
                    'datetime': datetime.fromtimestamp(timestamp)
                }

                print(f"📡 {symbol}: ${price:.2f} at {datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')}")

        except Exception as e:
            print(f"⚠️  Error processing live data: {e}")

    def on_error(self, ws, error):
        """Handle websocket errors"""
        print(f"❌ WebSocket error: {error}")
        self.connected = False

    def on_close(self, ws, close_status_code, close_msg):
        """Handle websocket close"""
        print("🔌 WebSocket connection closed")
        self.connected = False

    def on_open(self, ws):
        """Handle websocket open"""
        print("✅ WebSocket connected to live data stream")
        self.connected = True

        # Subscribe to symbols
        subscribe_msg = {
            "action": "subscribe",
            "symbols": self.symbols
        }
        ws.send(json.dumps(subscribe_msg))
        print(f"📡 Subscribed to: {', '.join(self.symbols)}")

    def connect(self):
        """Connect to live data websocket"""
        try:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )

            # Run in background thread
            def run_ws():
                self.ws.run_forever()

            ws_thread = threading.Thread(target=run_ws, daemon=True)
            ws_thread.start()

            return True

        except Exception as e:
            print(f"❌ Failed to connect to live data: {e}")
            return False

    def get_latest_price(self, symbol):
        """Get latest price for a symbol"""
        return self.latest_prices.get(symbol)

    def get_all_latest_prices(self):
        """Get all latest prices"""
        return self.latest_prices.copy()

    def disconnect(self):
        """Disconnect from websocket"""
        if self.ws:
            self.ws.close()
            self.connected = False

def test_live_data():
    """Simple test of live data functionality"""
    print("🚀 Testing Live Data WebSocket Connection")
    print("=" * 50)

    client = LiveDataClient(['SOXX', 'NVDA', 'AMD'])

    if client.connect():
        print("⏳ Waiting for live data... (Press Ctrl+C to stop)")

        try:
            # Monitor for 30 seconds
            for i in range(30):
                time.sleep(1)

                if client.connected and client.latest_prices:
                    print(f"\n📊 Live Prices ({datetime.now().strftime('%H:%M:%S')}):")
                    for symbol, data in client.latest_prices.items():
                        age = time.time() - data['timestamp']
                        print(f"   {symbol}: ${data['price']:.2f} ({age:.1f}s ago)")

        except KeyboardInterrupt:
            print("\n🛑 Stopping live data feed...")

        finally:
            client.disconnect()
            print("✅ Disconnected from live data")

    else:
        print("❌ Could not connect to live data service")
        print("💡 Make sure the data-service websocket endpoint is available")

if __name__ == "__main__":
    test_live_data()