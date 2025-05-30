from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.database import metadata, database, engine
from app.api.vehicle_detection_task import traffic_detection_task
import asyncio
from app.api.database import engine, Base
import time

app = FastAPI()

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
    await database.connect()
    # metadata.create_all(engine)
    asyncio.create_task(timer_task())
    
async def timer_task():
    while True:
    # start_time = time.time()
    # print("Thực hiện nhiệm vụ.")
        await traffic_detection_task()
    # elapsed = time.time() - start_time
    # print(f"Xử lý xong. Thời gian thực hiện: {elapsed:.2f} giây.")
    
@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()