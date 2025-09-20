#!/usr/bin/env python3
"""
Test script to verify Polygon WebSocket connection
"""
import asyncio
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_polygon_websocket():
    """Test connecting to Polygon WebSocket feed"""
    try:
        import websockets

        # Get API key from environment
        api_key = os.getenv("POLYGON_API_KEY")
        if not api_key:
            print("❌ No POLYGON_API_KEY found in environment")
            return

        print(f"🔑 Using API key: {api_key[:8]}...")

        # Connect to delayed feed
        uri = "wss://delayed.polygon.io/stocks"
        print(f"🔌 Connecting to {uri}")

        async with websockets.connect(uri) as websocket:
            print("✅ Connected to Polygon WebSocket!")

            # Authenticate
            auth_msg = {
                "action": "auth",
                "params": api_key
            }
            await websocket.send(json.dumps(auth_msg))
            print("🔐 Sent authentication message")

            # Wait for auth response
            auth_response = await websocket.recv()
            print(f"📨 Auth response: {auth_response}")

            # Subscribe to SPY trades and quotes
            subscribe_msg = {
                "action": "subscribe",
                "params": "T.SPY,Q.SPY"  # Trades and Quotes for SPY
            }
            await websocket.send(json.dumps(subscribe_msg))
            print("📡 Subscribed to SPY trades and quotes")

            # Listen for messages for 30 seconds
            print("👂 Listening for messages (30 seconds)...")
            try:
                for i in range(30):
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    print(f"📩 Message {i+1}: {data}")

            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for message")

    except ImportError:
        print("❌ websockets library not found. Install with: pip install websockets")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_polygon_websocket())