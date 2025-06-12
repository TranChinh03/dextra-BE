from datetime import datetime

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
    
class DetectionTime(BaseModel):
    date: str
    time: str
    
class DetectionDate(BaseModel):
    date: str
    
class DetectionResultsByDate(BaseModel):
    date: str
    numberOfBicycle: int
    numberOfMotorcycle: int
    numberOfCar: int
    numberOfVan: int
    numberOfTruck: int
    numberOfBus: int
    numberOfFireTruck: int
    numberOfContainer: int
    details: list['ResultDetail'] = Field(default_factory=list)
    
class CustomDetectionResultsInADay(BaseModel):
    date: str
    timeFrom: str
    timeTo: str
    numberOfBicycle: int = 0
    numberOfMotorcycle: int = 0
    numberOfCar: int = 0
    numberOfVan: int = 0
    numberOfTruck: int = 0
    numberOfBus: int = 0
    numberOfFireTruck: int = 0
    numberOfContainer: int = 0
    details: list['ResultDetail'] = Field(default_factory=list)
    
class DetectionResultsByDistrict(BaseModel):
    district: str
    date: str
    timeFrom: str
    timeTo: str
    numberOfBicycle: int = 0
    numberOfMotorcycle: int = 0
    numberOfCar: int = 0
    numberOfVan: int = 0
    numberOfTruck: int = 0
    numberOfBus: int = 0
    numberOfFireTruck: int = 0
    numberOfContainer: int = 0
    details: list['ResultDetail'] = Field(default_factory=list)
    
class DetectionResultsByCamera(BaseModel):
    camera: str
    numberOfBicycle: int = 0
    numberOfMotorcycle: int = 0
    numberOfCar: int = 0
    numberOfVan: int = 0
    numberOfTruck: int = 0
    numberOfBus: int = 0
    numberOfFireTruck: int = 0
    numberOfContainer: int = 0
    details: list['ResultDetailByDay'] = Field(default_factory=list)
    
class ResultDetail(BaseModel):
    date: str
    time: str
    numberOfBicycle: int = 0
    numberOfMotorcycle: int = 0
    numberOfCar: int = 0
    numberOfVan: int = 0
    numberOfTruck: int = 0
    numberOfBus: int = 0
    numberOfFireTruck: int = 0
    numberOfContainer: int = 0
    
class ResultDetailByDay(BaseModel):
    date: str
    numberOfBicycle: int = 0
    numberOfMotorcycle: int = 0
    numberOfCar: int = 0
    numberOfVan: int = 0
    numberOfTruck: int = 0
    numberOfBus: int = 0
    numberOfFireTruck: int = 0
    numberOfContainer: int = 0
    
class CameraResultInADay(BaseModel):
    date: str
    cameraId: str
    numberOfBicycle: int = 0
    numberOfMotorcycle: int = 0
    numberOfCar: int = 0
    numberOfVan: int = 0
    numberOfTruck: int = 0
    numberOfBus: int = 0
    numberOfFireTruck: int = 0
    numberOfContainer: int = 0
    details: list['ResultDetail'] = Field(default_factory=list)
    
class HeatmapResult(BaseModel):
    date: str
    timeFrom: str
    timeTo: str
    numberOfBicycle: int = 0
    numberOfMotorcycle: int = 0
    numberOfCar: int = 0
    numberOfVan: int = 0
    numberOfTruck: int = 0
    numberOfBus: int = 0
    numberOfFireTruck: int = 0
    numberOfContainer: int = 0
    details: list['HeatmapDetail'] = Field(default_factory=list)
    
class HeatmapInADay(BaseModel):
    date: str
    timeFrom: str
    timeTo: str
    numberOfBicycle: int = 0
    numberOfMotorcycle: int = 0
    numberOfCar: int = 0
    numberOfVan: int = 0
    numberOfTruck: int = 0
    numberOfBus: int = 0
    numberOfFireTruck: int = 0
    numberOfContainer: int = 0
    details: list['HeatInTime'] = Field(default_factory=list)
    
class HeatInTime(BaseModel):
    time: str
    data: list['HeatmapDetail'] = Field(default_factory=list)

class Location(BaseModel):
    type: str
    coordinates: list[float] = Field(..., description="Coordinates in [longitude, latitude] format")
class HeatmapDetail(BaseModel):
    camera: str
    loc: Location
    numberOfBicycle: int = 0
    numberOfMotorcycle: int = 0
    numberOfCar: int = 0
    numberOfVan: int = 0
    numberOfTruck: int = 0
    numberOfBus: int = 0
    numberOfFireTruck: int = 0
    numberOfContainer: int = 0