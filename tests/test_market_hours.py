#!/usr/bin/env python3
"""
Test script to run during market hours to verify websocket functionality
"""
import asyncio
import json
import websockets
from datetime import datetime

async def test_during_market_hours():
    """Test websocket during active market hours"""

    # Check current time
    now = datetime.now()
    print(f"🕒 Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    # Market hours check (simplified)
    is_weekday = now.weekday() < 5  # Monday = 0, Friday = 4
    market_open_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
    is_market_hours = market_open_time <= now <= market_close_time

    print(f"📅 Is weekday: {is_weekday}")
    print(f"🕘 Market hours (9:30-16:00): {is_market_hours}")

    if not (is_weekday and is_market_hours):
        print("⚠️  Market is currently closed. This test is most effective during market hours.")
        print("   You can still run it to test the connection and REST fallback.")

    try:
        uri = "ws://localhost:8001/live-data/SPY"
        print(f"\n🔌 Connecting to {uri}")

        async with websockets.connect(uri) as websocket:
            print("✅ Connected to live data websocket!")

            # Listen for messages
            print("👂 Listening for messages (will show up to 20 messages)...")
            message_count = 0

            while message_count < 20:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    message_count += 1

                    print(f"\n📩 Message {message_count}:")
                    print(f"   ⏰ Timestamp: {data.get('timestamp', 'N/A')}")
                    print(f"   📊 Status: {data.get('connection_status', 'N/A')}")
                    print(f"   🏪 Market Open: {data.get('market_open', 'N/A')}")
                    print(f"   💬 Message: {data.get('message', 'N/A')}")
                    print(f"   🔗 Source: {data.get('data_source', 'N/A')}")

                    if data.get('trade'):
                        trade = data['trade']
                        print(f"   📈 Trade: ${trade.get('price', 'N/A')} (size: {trade.get('size', 'N/A')})")

                    if data.get('quote'):
                        quote = data['quote']
                        print(f"   💱 Quote: Bid=${quote.get('bid', 'N/A')} Ask=${quote.get('ask', 'N/A')}")

                    # If we get real data, that's great!
                    if data.get('trade') or data.get('quote'):
                        print("   🎉 LIVE DATA RECEIVED!")

                except asyncio.TimeoutError:
                    print(f"\n⏰ Timeout after 10 seconds waiting for message {message_count + 1}")
                    break

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("💡 Make sure the server is running: uvicorn main:app --reload --port 8001")

if __name__ == "__main__":
    print("🧪 Market Hours WebSocket Test")
    print("=" * 50)
    asyncio.run(test_during_market_hours())