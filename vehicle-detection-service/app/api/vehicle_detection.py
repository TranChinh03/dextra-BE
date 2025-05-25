from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from ultralytics import YOLO
from PIL import Image, ImageDraw
import io
from datetime import datetime
from .models import Detection, DetectionResponse
import torch

detections = APIRouter()

model = YOLO("bestv10l.pt", task='detect').to("cuda")  # Load the YOLOv8 model
vehicle_classes = ['bicycle', 'motorcycle', 'car', 'van', 'truck', 'bus', 'fire truck', 'container']

@detections.post("/detect-vehicles", response_model=DetectionResponse)
async def detect_vehicles(file: UploadFile = File(...)):
    print(f"Model loaded on device: {torch.cuda.is_available()}")
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        results = model(image)
        detections_list = []
        counts = {cls: 0 for cls in vehicle_classes}
        for box in results[0].boxes:
            cls = int(box.cls[0])
            label = model.names[cls]
            if label in vehicle_classes:
                counts[label] += 1
                detections_list.append(Detection(
                    label=label,
                    confidence=float(box.conf[0]),
                    bbox=[float(x) for x in box.xyxy[0].tolist()]
                ))
        return DetectionResponse(
            detections=detections_list,
            detect_at=datetime.utcnow().isoformat(),
            numberOfBicycle=counts['bicycle'],
            numberOfMotorcycle=counts['motorcycle'],
            numberOfCar=counts['car'],
            numberOfVan=counts['van'],
            numberOfTruck=counts['truck'],
            numberOfBus=counts['bus'],
            numberOfFireTruck=counts['fire truck'],
            numberOfContainer=counts['container']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@detections.post("/detect/images")
async def detect_vehicles_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        results = model(image)
        draw = ImageDraw.Draw(image)
        for box in results[0].boxes:
            cls = int(box.cls[0])
            label = model.names[cls]
            if label in vehicle_classes:
                bbox = [float(x) for x in box.xyxy[0].tolist()]
                draw.rectangle(bbox, outline="red", width=3)
                draw.text((bbox[0], bbox[1] - 10), label, fill="red")
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)
        return StreamingResponse(img_byte_arr, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))