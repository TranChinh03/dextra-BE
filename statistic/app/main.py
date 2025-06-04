from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.database import metadata, database, engine
from app.api.statistic import statistic
import asyncio
from app.api.database import engine, Base
import time
from dotenv import load_dotenv

app = FastAPI(openapi_url="/api/v1/statistic/openapi.json", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# Khởi động scheduler khi ứng dụng khởi chạy
@app.on_event("startup")
async def start_scheduler():
    load_dotenv()
    await database.connect()
    
@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
    
app.include_router(statistic, tags=['statistic'])