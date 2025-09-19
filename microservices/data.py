from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import httpx
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

@app.get("/test-redis")
async def test_redis():

    r.set('Foo', 'Bar')
    response = r.get('Foo')

    return {
        "Message": f'{response}'
    }


## - POLYGON HISTORICAL REST - ##

@app.get("/historical-data")
async def fetch_historical_data(request: Request, symbol: str):
    polygon_key = request.state.POLYGON_API_KEY
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2023-09-01/2023-09-18?apiKey={polygon_key}"

    async with httpx.AsyncClient() as client:
        res = await client.get(url)

    if res.status_code != 200:
        return JSONResponse(
            status_code=res.status_code,
            content={"error": res.text}
        )

    data = res.json()
    return {"symbol": symbol, "data": data}


## - POLYGON LIVE WEBSOCKET - ##
@app.get("/live-data")
async def fetch_live_data():
    # TODO: Implement Live websocket data 

    response = "Live Websocket Data Enpoint - not yet implemented"

    return {
        "Message": f'{response}'
    }