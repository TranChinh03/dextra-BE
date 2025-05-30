from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Depends
from app.api.models import DetectionTime, DetectionDate, DetectionResultsByDate, CustomDetectionResultsInADay, DetectionResultsByDistrict
from app.api import db_manager
from app.api.db_manager import DBManager
from sqlalchemy.orm import Session
from app.api.database import get_db
from databases import Database
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, TemplateId, Substitution
from sqlalchemy import select
import httpx
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

statistic = APIRouter()

CAMERA_SERVICE_URL = "http://localhost:8002"

@statistic.get("/timestamp", response_model=List[DetectionTime])
async def get_timestamp(db: Database = Depends(get_db)) -> List[DetectionTime]:
    """Get the timestamp."""
    result = await db_manager.get_timestamp(db)
    if not result:
        raise HTTPException(status_code=404, detail="Timestamp not found")
    return result

@statistic.get("/date", response_model=List[DetectionDate])
async def get_timestamp(db: Database = Depends(get_db)) -> List[DetectionDate]:
    """Get the date."""
    result = await db_manager.get_date(db)
    if not result:
        raise HTTPException(status_code=404, detail="Date not found")
    return result

@statistic.get("/detection_results_by_date", response_model=DetectionResultsByDate)
async def get_detection_results_by_date(
    date: str, db: Database = Depends(get_db)
) -> DetectionResultsByDate:
    """Get detection results by date."""
    result = await db_manager.get_detection_results_by_date(date, db)
    if not result:
        raise HTTPException(status_code=404, detail="Detection results not found for the given date")
    return result

@statistic.get("/custom_detection_results", response_model=CustomDetectionResultsInADay)
async def get_custom_detection_results(
    date: str, time_from: str, time_to: str, db: Database = Depends(get_db)
) -> CustomDetectionResultsInADay:
    """Get custom detection results."""
    result = await db_manager.get_custom_detection_results(db, date, time_from, time_to)
    if not result:
        raise HTTPException(status_code=404, detail="Custom detection results not found")
    return result

@statistic.get("/custom_detection_results_by_district", response_model=DetectionResultsByDistrict)
async def get_custom_detection_results_by_district(
    district: str, date: str, time_from: str, time_to: str, db: Database = Depends(get_db)
) -> DetectionResultsByDistrict:
    """Get custom detection results by district."""
    cameraList = await get_cameras_by_district(district)
    result = await db_manager.get_custom_detection_results_by_district(
        db, district, date, time_from, time_to, cameraList
    )
    if not result:
        raise HTTPException(status_code=404, detail="Custom detection results not found for the given district")
    return result

async def get_cameras_by_district(district: str) -> List[Dict]:
    async with httpx.AsyncClient(base_url=CAMERA_SERVICE_URL) as client:
        response = await client.get(f"/cameras/district/{district}")
        response.raise_for_status()
        cameras = response.json()
        return cameras