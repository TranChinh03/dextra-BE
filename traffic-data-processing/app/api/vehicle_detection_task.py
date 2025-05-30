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
    now = datetime.now().replace(hour=23, minute=0, second=0, microsecond=0)
    start_time = now - timedelta(days=7)
    end_time = now

    current_time = start_time.replace(hour=23, minute=0, second=0, microsecond=0)
    while current_time <= end_time:
        print(f"Đang xử lý thời gian: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        # You may want to pass current_time to iterate_task if needed
        await iterate_task(cameraList, current_time)
        current_time += timedelta(minutes=30)
    
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
    
async def write_detection_results_to_db(db: Database, camera_info: dict, current_time: datetime):
    """Write detection results to the database
    
    Args:
        db (Database): The database connection
        detection_results (dict): The detection results to write
    """
    rs = db_manager.DetectionResults(
        detectionId=str(uuid4()),  # Generate a unique ID for the detection result
        cameraId=camera_info['_id'],
        date=current_time.strftime('%Y-%m-%d'),
        time=current_time.strftime('%H:%M:%S'),
        numberOfBicycle=random.randint(0, 10),
        numberOfMotorcycle=random.randint(10, 50),
        numberOfCar=random.randint(10, 20),
        numberOfVan=random.randint(0, 5),
        numberOfTruck=random.randint(0, 5),
        numberOfBus=random.randint(0, 5),
        numberOfFireTruck=random.randint(0, 2),
        numberOfContainer= random.randint(0, 2),
    )
    await db_manager.write_detection_result_to_db(db, rs.__dict__)