from datetime import datetime, timezone

from pydantic import BaseModel, Field

class DetectionResults(BaseModel):
    detectionId: str
    cameraId: str
    date: str = Field(default_factory=lambda: datetime.utcnow().strftime('%Y-%m-%d'))
    time: str = Field(default_factory=lambda: datetime.utcnow().strftime('%H:%M:%S'))
    numberOfBicycle: int = 0
    numberOfMotorcycle: int = 0
    numberOfCar: int = 0
    numberOfVan: int = 0
    numberOfTruck: int = 0
    numberOfBus: int = 0
    numberOfFireTruck: int = 0
    numberOfContainer: int = 0