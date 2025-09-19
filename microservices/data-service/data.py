from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
from utils import Timespan, calculate_dates
from dotenv import load_dotenv
import os

load_dotenv()


### --- R E D I S   C L I E N T --- ###

import redis

r = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=11515,
    decode_responses=True,
    username="default",
    password=os.getenv('REDIS_PASSWORD'),
)

app = FastAPI()

# CORS ------------ #

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or whitelist: ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


### --- A P I   E N D P O I N T S --- ###

## - REDIS - ##
@app.get("/test-redis")
async def test_redis():

    r.set('Foo', 'Bar')
    response = r.get('Foo')

    return {
        "Message": f'{response}'
    }


## - POLYGON - ##

POLYGON_KEY = os.getenv("POLYGON_API_KEY")


## - REST - HISTORICAL - ##
@app.get("/historical-data")
async def fetch_historical_data(
    symbol: str = Query(...),
    mul: int = Query(3),
    timespan: Timespan = Query("month")
):
    # calulate start and end dates
    start, end = calculate_dates(mul, timespan.value)

    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{mul}/"
        f"{timespan.value}/{start}/{end}"
        f"?adjusted=true&sort=asc&limit=50000&apiKey={POLYGON_KEY}"
    )

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    if response.status_code != 200:
        return {
            "error": f"Polygon API returned {response.status_code}",
            "details": response.text
        }

    return response.json()


## - WEBSOCKET - LIVE - ##
@app.get("/live-data")
async def fetch_live_data():



    response = "Live Websocket Data Enpoint - not yet implemented"

    return {
        "Message": f'{response}'
    }