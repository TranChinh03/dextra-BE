import httpx
import io
from PIL import Image
from app.api import db_manager
from databases import Database
from app.api.database import get_db
from uuid import uuid4
from datetime import datetime

CAMERA_SERVICE_URL = "http://localhost:8002"
DETECTION_SERVICE_URL = "http://localhost:8003"

async def traffic_detection_task():
    db = await get_db()
    # Xử lý nhiệm vụ phát hiện phương tiện
    # print("Đang xử lý nhiệm vụ phát hiện phương tiện...")
    
    # Lấy danh sách camera từ API
    cameraList = await get_cameras()
    currentTime = datetime.now()
    
    # Duyệt qua từng camera và in ra thông tin
    for camera in cameraList:
        # print(f"Camera ID: {camera['_id']}, Name: {camera['name']}, liveviewUrl: {camera['liveviewUrl']}")
        if not camera['liveviewUrl'].startswith('http'):
            print(f"Skipping camera {camera['_id']} due to invalid liveviewUrl: {camera['liveviewUrl']}")
            continue
        # Lấy hình ảnh từ URL liveviewUrl
        image = await get_image(camera['liveviewUrl'])
        detection_results = await detect_vehicles(image)
        # Write detection results to database
        await write_detection_results_to_db(db, detection_results, camera, currentTime)
        # break
        
    # print("Nhiệm vụ phát hiện phương tiện đã hoàn thành.")
    
async def get_cameras():
    async with httpx.AsyncClient(base_url=CAMERA_SERVICE_URL) as client:
        response = await client.get("/cameras")
        response.raise_for_status()
        cameras = response.json()
        return cameras
    
async def get_image(liveviewUrl: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(liveviewUrl, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
        response.raise_for_status()
        image_data = response.content
        return image_data

async def detect_vehicles(image: bytes):
    """Detect vehicles in the image using detection service
    
    Args:
        image (Image): The input image in PIL RGB format
    
    Returns:
        dict: Detection results
    """
    async with httpx.AsyncClient(base_url=DETECTION_SERVICE_URL) as client:
        files = {'file': ('image.jpg', image, 'image/jpeg')}
        response = await client.post("/detect-vehicles", files=files)
        response.raise_for_status()
        detection_results = response.json()
        return detection_results
    
async def write_detection_results_to_db(db: Database, detection_results: dict, camera_info: dict, current_time: datetime):
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
        numberOfBicycle=detection_results.get('numberOfBicycle', 0),
        numberOfMotorcycle=detection_results.get('numberOfMotorcycle', 0),
        numberOfCar=detection_results.get('numberOfCar', 0),
        numberOfVan=detection_results.get('numberOfVan', 0),
        numberOfTruck=detection_results.get('numberOfTruck', 0),
        numberOfBus=detection_results.get('numberOfBus', 0),
        numberOfFireTruck=detection_results.get('numberOfFireTruck', 0),
        numberOfContainer=detection_results.get('numberOfContainer', 0),
    )
    await db_manager.write_detection_result_to_db(db, rs.__dict__)
    
def get_image_from_bytes(binary_image: bytes) -> Image:
    """Convert image from bytes to PIL RGB format
    
    Args:
        binary_image (bytes): The binary representation of the image
    
    Returns:
        PIL.Image: The image in PIL RGB format
    """
    input_image = Image.open(io.BytesIO(binary_image)).convert("RGB")
    return input_image