from pydantic import BaseModel
from typing import List

class Detection(BaseModel):
    label: str
    confidence: float
    bbox: list[float]

class DetectionResponse(BaseModel):
    detections: List[Detection]
    detect_at: str
    numberOfBicycle: int = 0
    numberOfMotorcycle: int = 0
    numberOfCar: int = 0
    numberOfVan: int = 0
    numberOfTruck: int = 0
    numberOfBus: int = 0
    numberOfFireTruck: int = 0
    numberOfContainer: int = 0