from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    #TODO: change to whitlist URLS to configure internal APIs only. 
    allow_credentials=True, 
    allow_methods=["*"],    #TODO: Change the method to secure.
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "Message": "Running strategy-service",
        "Endpoints": [
            "1. ",
            "2. "
        ]
    }