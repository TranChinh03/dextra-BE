from fastapi import FastAPI
from app.api.vehicle_detection import detections
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(openapi_url="/api/v1/vehicle_detection/openapi.json", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    print("starting up")

@app.on_event("shutdown")
async def shutdown():
    print("shutdown")

app.include_router(detections, tags=['detections'])