import httpx
import io
from PIL import Image
from app.api import db_manager
from databases import Database
from app.api.database import get_db
from uuid import uuid4
from datetime import datetime
import random
from datetime import timedelta

CAMERA_SERVICE_URL = "http://localhost:8002"


async def traffic_detection_task():
    # Lấy danh sách camera từ API
    cameraList = await get_cameras()
    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_time = now - timedelta(days=7)
    end_time = now

    current_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    while current_time <= end_time:
        print(f"Đang xử lý thời gian: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        # You may want to pass current_time to iterate_task if needed
        await iterate_task(cameraList, current_time)
        current_time += timedelta(hours=1)
    
async def iterate_task(cameraList: list, currentTime: datetime):
    db = await get_db()
    # Xử lý nhiệm vụ phát hiện phương tiện
    # print("Đang xử lý nhiệm vụ phát hiện phương tiện...")
    
    # Duyệt qua từng camera và ghi lại kết quả phát hiện vào cơ sở dữ liệu
    for camera in cameraList:
        await write_detection_results_to_db(db, camera, currentTime)
        

async def get_cameras():
    async with httpx.AsyncClient(base_url=CAMERA_SERVICE_URL) as client:
        response = await client.get("/cameras")
        response.raise_for_status()
        cameras = response.json()
        return cameras
    
def is_rush_hour(dt: datetime) -> bool:
    # Morning: 6:30–8:30, Evening: 16:30–18:30
    morning_start = dt.replace(hour=6, minute=30, second=0, microsecond=0)
    morning_end = dt.replace(hour=8, minute=30, second=0, microsecond=0)
    evening_start = dt.replace(hour=16, minute=30, second=0, microsecond=0)
    evening_end = dt.replace(hour=18, minute=30, second=0, microsecond=0)
    return (morning_start <= dt <= morning_end) or (evening_start <= dt <= evening_end)

async def write_detection_results_to_db(db: Database, camera_info: dict, current_time: datetime):
    """Write detection results to the database
    
    Args:
        db (Database): The database connection
        detection_results (dict): The detection results to write
    """
    if is_rush_hour(current_time):
        rs = db_manager.DetectionResults(
            detectionId=str(uuid4()),  # Generate a unique ID for the detection result
            cameraId=camera_info['_id'],
            date=current_time.strftime('%Y-%m-%d'),
            time=current_time.strftime('%H:%M:%S'),
            numberOfBicycle=random.randint(5, 20),
            numberOfMotorcycle=random.randint(30, 100),
            numberOfCar=random.randint(20, 40),
            numberOfVan=random.randint(1, 4),
            numberOfTruck=random.randint(1, 4),
            numberOfBus=random.randint(1, 4),
            numberOfFireTruck=random.randint(0, 2),
            numberOfContainer= random.randint(0, 2),
        )
    else:
        rs = db_manager.DetectionResults(
            detectionId=str(uuid4()),  # Generate a unique ID for the detection result
            cameraId=camera_info['_id'],
            date=current_time.strftime('%Y-%m-%d'),
            time=current_time.strftime('%H:%M:%S'),
            numberOfBicycle=random.randint(0, 10),
            numberOfMotorcycle=random.randint(10, 50),
            numberOfCar=random.randint(10, 20),
            numberOfVan=random.randint(0, 2),
            numberOfTruck=random.randint(0, 2),
            numberOfBus=random.randint(0, 2),
            numberOfFireTruck=random.randint(0, 2),
            numberOfContainer=random.randint(0, 2),
        )
    await db_manager.write_detection_result_to_db(db, rs.__dict__)