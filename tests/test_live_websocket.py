#!/usr/bin/env python3
"""
Test our live data websocket endpoint
"""
import asyncio
import json
import websockets

async def test_live_data_websocket():
    """Test our live data websocket endpoint"""
    try:
        uri = "ws://localhost:8001/live-data/SPY"
        print(f"🔌 Connecting to {uri}")

        async with websockets.connect(uri) as websocket:
            print("✅ Connected to our live data websocket!")

            # Listen for messages for 30 seconds
            print("👂 Listening for messages (30 seconds)...")
            message_count = 0

            try:
                while message_count < 10:  # Get up to 10 messages
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    message_count += 1

                    print(f"📩 Message {message_count}:")
                    print(f"   Status: {data.get('connection_status', 'N/A')}")
                    print(f"   Market Open: {data.get('market_open', 'N/A')}")
                    print(f"   Message: {data.get('message', 'N/A')}")
                    print(f"   Data Source: {data.get('data_source', 'N/A')}")
                    if data.get('trade'):
                        print(f"   Trade Price: ${data['trade']['price']}")
                    if data.get('quote'):
                        print(f"   Bid/Ask: ${data['quote']['bid']}/${data['quote']['ask']}")
                    print()

            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for message")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_live_data_websocket())