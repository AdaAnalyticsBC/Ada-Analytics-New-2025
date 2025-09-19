from fastapi import FastAPI
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

### --- M I D D L E W A R E --- ###

@app.middleware("http")
async def add_timeout(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Request timeout or internal error."})

@app.middleware("http")
async def add_allowed_origins(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.middleware("http")
async def add_polygon_key(request: Request, call_next):
    request.state.POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
    return await call_next(request)

@app.middleware("http")
async def add_quiver_key(request: Request, call_next):
    request.state.QUIVER_API_KEY = os.getenv("QUIVER_API_KEY")
    return await call_next(request)


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
async def fetch_historical_data(symbol):
    # TODO: Implement historical data fetching logic

    response = "Historical data endpoint - not yet implemented"
    
    return {
        "Message": f'{response}'
    }


## - POLYGON LIVE WEBSOCKET - ##
@app.get("/live-data")
async def fetch_live_data():
    # TODO: Implement Live websocket data 

    response = "Live Websocket Data Enpoint - not yet implemented"

    return {
        "Message": f'{response}'
    }