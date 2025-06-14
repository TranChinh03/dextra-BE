from app.api.database import get_db, detection_results
from app.api.models import DetectionResults
from databases import Database
from sqlalchemy import insert, or_, select, update, and_, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException
import httpx
from typing import List, Dict, Optional
from collections import defaultdict

CAMERA_SERVICE_URL = "http://nginx:8080"
CAMERA_API_URL = "https://api.notis.vn/v4/cameras/bybbox?lat1=11.160767&lng1=106.554166&lat2=9.45&lng2=128.99999"

class DBManager:
    def __init__(self, session: get_db):
        self.session = session

async def get_timestamp(db: Database) -> object:
    query = select(detection_results.c.date, detection_results.c.time).distinct().order_by(
        detection_results.c.date, detection_results.c.time
    )
    result = await db.fetch_all(query)
    return result

async def get_date(db: Database) -> object:
    query = select(detection_results.c.date).distinct().order_by(detection_results.c.date)
    result = await db.fetch_all(query)
    return result

async def get_detection_results_by_date(date: str, db: Database) -> dict:
    """
    Get summed detection results for a specific date.
    Returns a dict matching DetectionResultsByDate model, including details for each timestamp.
    """
    query = select(
        detection_results.c.date,
        detection_results.c.time,
        detection_results.c.numberOfBicycle,
        detection_results.c.numberOfMotorcycle,
        detection_results.c.numberOfCar,
        detection_results.c.numberOfVan,
        detection_results.c.numberOfTruck,
        detection_results.c.numberOfBus,
        detection_results.c.numberOfFireTruck,
        detection_results.c.numberOfContainer,
    ).where(detection_results.c.date == date)
    rows = await db.fetch_all(query)
    if not rows:
        return None

    # Aggregate by (date, time)
    details_dict = {}
    for row in rows:
        key = (row["date"], row["time"])
        if key not in details_dict:
            details_dict[key] = {
                "date": row["date"],
                "time": row["time"],
                "numberOfBicycle": 0,
                "numberOfMotorcycle": 0,
                "numberOfCar": 0,
                "numberOfVan": 0,
                "numberOfTruck": 0,
                "numberOfBus": 0,
                "numberOfFireTruck": 0,
                "numberOfContainer": 0,
            }
        details_dict[key]["numberOfBicycle"] += row["numberOfBicycle"]
        details_dict[key]["numberOfMotorcycle"] += row["numberOfMotorcycle"]
        details_dict[key]["numberOfCar"] += row["numberOfCar"]
        details_dict[key]["numberOfVan"] += row["numberOfVan"]
        details_dict[key]["numberOfTruck"] += row["numberOfTruck"]
        details_dict[key]["numberOfBus"] += row["numberOfBus"]
        details_dict[key]["numberOfFireTruck"] += row["numberOfFireTruck"]
        details_dict[key]["numberOfContainer"] += row["numberOfContainer"]

    details = list(details_dict.values())

    # Sum up all vehicle counts for the date
    result = {
        "date": date,
        "numberOfBicycle": 0,
        "numberOfMotorcycle": 0,
        "numberOfCar": 0,
        "numberOfVan": 0,
        "numberOfTruck": 0,
        "numberOfBus": 0,
        "numberOfFireTruck": 0,
        "numberOfContainer": 0,
        "details": details
    }
    for d in details:
        result["numberOfBicycle"] += d["numberOfBicycle"]
        result["numberOfMotorcycle"] += d["numberOfMotorcycle"]
        result["numberOfCar"] += d["numberOfCar"]
        result["numberOfVan"] += d["numberOfVan"]
        result["numberOfTruck"] += d["numberOfTruck"]
        result["numberOfBus"] += d["numberOfBus"]
        result["numberOfFireTruck"] += d["numberOfFireTruck"]
        result["numberOfContainer"] += d["numberOfContainer"]
    return result

async def get_custom_detection_results(db: Database, date: str, timeFrom: str, timeTo: str):
    """
    Get detection results for a specific date and time range.
    Returns a dict matching CustomDetectionResults model, including details for each timestamp.
    """
    query = select(
        detection_results.c.date,
        detection_results.c.time,
        detection_results.c.numberOfBicycle,
        detection_results.c.numberOfMotorcycle,
        detection_results.c.numberOfCar,
        detection_results.c.numberOfVan,
        detection_results.c.numberOfTruck,
        detection_results.c.numberOfBus,
        detection_results.c.numberOfFireTruck,
        detection_results.c.numberOfContainer,
    ).where(
        and_(
            detection_results.c.date == date,
            detection_results.c.time >= timeFrom,
            detection_results.c.time <= timeTo
        )
    )
    rows = await db.fetch_all(query)
    if not rows:
        return None

    # Aggregate by (date, time)
    details_dict = {}
    for row in rows:
        key = (row["date"], row["time"])
        if key not in details_dict:
            details_dict[key] = {
                "date": row["date"],
                "time": row["time"],
                "numberOfBicycle": 0,
                "numberOfMotorcycle": 0,
                "numberOfCar": 0,
                "numberOfVan": 0,
                "numberOfTruck": 0,
                "numberOfBus": 0,
                "numberOfFireTruck": 0,
                "numberOfContainer": 0,
            }
        details_dict[key]["numberOfBicycle"] += row["numberOfBicycle"]
        details_dict[key]["numberOfMotorcycle"] += row["numberOfMotorcycle"]
        details_dict[key]["numberOfCar"] += row["numberOfCar"]
        details_dict[key]["numberOfVan"] += row["numberOfVan"]
        details_dict[key]["numberOfTruck"] += row["numberOfTruck"]
        details_dict[key]["numberOfBus"] += row["numberOfBus"]
        details_dict[key]["numberOfFireTruck"] += row["numberOfFireTruck"]
        details_dict[key]["numberOfContainer"] += row["numberOfContainer"]

    details = list(details_dict.values())

    # Sum up all vehicle counts for the specified date and time range
    result = {
        "date": date,
        "timeFrom": timeFrom,
        "timeTo": timeTo,
        "numberOfBicycle": 0,
        "numberOfMotorcycle": 0,
        "numberOfCar": 0,
        "numberOfVan": 0,
        "numberOfTruck": 0,
        "numberOfBus": 0,
        "numberOfFireTruck": 0,
        "numberOfContainer": 0,
        "details": details
    }
    for d in details:
        result["numberOfBicycle"] += d["numberOfBicycle"]
        result["numberOfMotorcycle"] += d["numberOfMotorcycle"]
        result["numberOfCar"] += d["numberOfCar"]
        result["numberOfVan"] += d["numberOfVan"]
        result["numberOfTruck"] += d["numberOfTruck"]
        result["numberOfBus"] += d["numberOfBus"]
        result["numberOfFireTruck"] += d["numberOfFireTruck"]
        result["numberOfContainer"] += d["numberOfContainer"]
    return result

async def get_custom_detection_results_by_district(db: Database, district: str, date: str, timeFrom: str, timeTo: str, cameraList: list):
    """
    Get detection results for a specific district, date, and time range.
    Returns a dict matching DetectionResultsByDistrict model, with details summed by date & time.
    """
    query = select(
        detection_results.c.date,
        detection_results.c.time,
        detection_results.c.numberOfBicycle,
        detection_results.c.numberOfMotorcycle,
        detection_results.c.numberOfCar,
        detection_results.c.numberOfVan,
        detection_results.c.numberOfTruck,
        detection_results.c.numberOfBus,
        detection_results.c.numberOfFireTruck,
        detection_results.c.numberOfContainer,
    ).where(
        and_(
            detection_results.c.date == date,
            detection_results.c.time >= timeFrom,
            detection_results.c.time <= timeTo,
            detection_results.c.cameraId.in_([cam["_id"] for cam in cameraList])
        )
    )
    rows = await db.fetch_all(query)
    if not rows:
        return None

    # Aggregate by (date, time)
    details_dict = {}
    for row in rows:
        key = (row["date"], row["time"])
        if key not in details_dict:
            details_dict[key] = {
                "date": row["date"],
                "time": row["time"],
                "numberOfBicycle": 0,
                "numberOfMotorcycle": 0,
                "numberOfCar": 0,
                "numberOfVan": 0,
                "numberOfTruck": 0,
                "numberOfBus": 0,
                "numberOfFireTruck": 0,
                "numberOfContainer": 0,
            }
        details_dict[key]["numberOfBicycle"] += row["numberOfBicycle"]
        details_dict[key]["numberOfMotorcycle"] += row["numberOfMotorcycle"]
        details_dict[key]["numberOfCar"] += row["numberOfCar"]
        details_dict[key]["numberOfVan"] += row["numberOfVan"]
        details_dict[key]["numberOfTruck"] += row["numberOfTruck"]
        details_dict[key]["numberOfBus"] += row["numberOfBus"]
        details_dict[key]["numberOfFireTruck"] += row["numberOfFireTruck"]
        details_dict[key]["numberOfContainer"] += row["numberOfContainer"]

    details = list(details_dict.values())

    # Sum up all vehicle counts for the specified district, date, and time range
    result = {
        "district": district,
        "date": date,
        "timeFrom": timeFrom,
        "timeTo": timeTo,
        "numberOfBicycle": 0,
        "numberOfMotorcycle": 0,
        "numberOfCar": 0,
        "numberOfVan": 0,
        "numberOfTruck": 0,
        "numberOfBus": 0,
        "numberOfFireTruck": 0,
        "numberOfContainer": 0,
        "details": details
    }
    for d in details:
        result["numberOfBicycle"] += d["numberOfBicycle"]
        result["numberOfMotorcycle"] += d["numberOfMotorcycle"]
        result["numberOfCar"] += d["numberOfCar"]
        result["numberOfVan"] += d["numberOfVan"]
        result["numberOfTruck"] += d["numberOfTruck"]
        result["numberOfBus"] += d["numberOfBus"]
        result["numberOfFireTruck"] += d["numberOfFireTruck"]
        result["numberOfContainer"] += d["numberOfContainer"]
    return result

async def get_custom_detection_results_by_camera(db: Database, camera: str):
    """
    Get detection statistics for a specific camera, grouped by date.
    Returns a dict matching DetectionResultsByCamera model, including details for each date.
    """

    query = select(
        detection_results.c.date,
        detection_results.c.numberOfBicycle,
        detection_results.c.numberOfMotorcycle,
        detection_results.c.numberOfCar,
        detection_results.c.numberOfVan,
        detection_results.c.numberOfTruck,
        detection_results.c.numberOfBus,
        detection_results.c.numberOfFireTruck,
        detection_results.c.numberOfContainer,
    ).where(
        detection_results.c.cameraId == camera
    )
    rows = await db.fetch_all(query)
    if not rows:
        return None

    # Aggregate by date
    details_dict = {}
    for row in rows:
        key = row["date"]
        if key not in details_dict:
            details_dict[key] = {
                "date": row["date"],
                "numberOfBicycle": 0,
                "numberOfMotorcycle": 0,
                "numberOfCar": 0,
                "numberOfVan": 0,
                "numberOfTruck": 0,
                "numberOfBus": 0,
                "numberOfFireTruck": 0,
                "numberOfContainer": 0,
            }
        details_dict[key]["numberOfBicycle"] += row["numberOfBicycle"]
        details_dict[key]["numberOfMotorcycle"] += row["numberOfMotorcycle"]
        details_dict[key]["numberOfCar"] += row["numberOfCar"]
        details_dict[key]["numberOfVan"] += row["numberOfVan"]
        details_dict[key]["numberOfTruck"] += row["numberOfTruck"]
        details_dict[key]["numberOfBus"] += row["numberOfBus"]
        details_dict[key]["numberOfFireTruck"] += row["numberOfFireTruck"]
        details_dict[key]["numberOfContainer"] += row["numberOfContainer"]

    details = list(details_dict.values())

    # Sum up all vehicle counts for the camera
    result = {
        "camera": camera,
        "numberOfBicycle": 0,
        "numberOfMotorcycle": 0,
        "numberOfCar": 0,
        "numberOfVan": 0,
        "numberOfTruck": 0,
        "numberOfBus": 0,
        "numberOfFireTruck": 0,
        "numberOfContainer": 0,
        "details": details
    }
    for d in details:
        result["numberOfBicycle"] += d["numberOfBicycle"]
        result["numberOfMotorcycle"] += d["numberOfMotorcycle"]
        result["numberOfCar"] += d["numberOfCar"]
        result["numberOfVan"] += d["numberOfVan"]
        result["numberOfTruck"] += d["numberOfTruck"]
        result["numberOfBus"] += d["numberOfBus"]
        result["numberOfFireTruck"] += d["numberOfFireTruck"]
        result["numberOfContainer"] += d["numberOfContainer"]
    return result

async def get_traffic_tracking_by_camera_in_date(
    db: Database,
    date: str = None,
    camera: str = None,
    timeFrom: Optional[str] = None,
    timeTo: Optional[str] = None
): 
    """
    Get detection results for a specific camera on a specific date.
    Returns a dict matching CameraResultInADay model.
    """
    from sqlalchemy import and_
    query = select(
        detection_results.c.date,
        detection_results.c.time,
        detection_results.c.cameraId,
        detection_results.c.numberOfBicycle,
        detection_results.c.numberOfMotorcycle,
        detection_results.c.numberOfCar,
        detection_results.c.numberOfVan,
        detection_results.c.numberOfTruck,
        detection_results.c.numberOfBus,
        detection_results.c.numberOfFireTruck,
        detection_results.c.numberOfContainer,
    ).where(
        and_(
            detection_results.c.date == date,
            detection_results.c.cameraId == camera
        )
    )
    
    if timeFrom and timeTo:
        query = query.where(
            and_(
                detection_results.c.time >= timeFrom,
                detection_results.c.time <= timeTo
            )
        )
        
        
    rows = await db.fetch_all(query)
    if not rows:
        return None

    # Aggregate total vehicle counts for the day
    result = {
        "date": date,
        "cameraId": camera,
        "numberOfBicycle": 0,
        "numberOfMotorcycle": 0,
        "numberOfCar": 0,
        "numberOfVan": 0,
        "numberOfTruck": 0,
        "numberOfBus": 0,
        "numberOfFireTruck": 0,
        "numberOfContainer": 0,
        "details": []
    }
    details = []
    for row in rows:
        result["numberOfBicycle"] += row["numberOfBicycle"]
        result["numberOfMotorcycle"] += row["numberOfMotorcycle"]
        result["numberOfCar"] += row["numberOfCar"]
        result["numberOfVan"] += row["numberOfVan"]
        result["numberOfTruck"] += row["numberOfTruck"]
        result["numberOfBus"] += row["numberOfBus"]
        result["numberOfFireTruck"] += row["numberOfFireTruck"]
        result["numberOfContainer"] += row["numberOfContainer"]
        details.append({
            "date": row["date"],
            "time": row["time"],
            "numberOfBicycle": row["numberOfBicycle"],
            "numberOfMotorcycle": row["numberOfMotorcycle"],
            "numberOfCar": row["numberOfCar"],
            "numberOfVan": row["numberOfVan"],
            "numberOfTruck": row["numberOfTruck"],
            "numberOfBus": row["numberOfBus"],
            "numberOfFireTruck": row["numberOfFireTruck"],
            "numberOfContainer": row["numberOfContainer"]
        })
    result["details"] = details
    return result

async def get_traffic_tracking_by_date(
    db: Database, 
    dateFrom: Optional[str] = None, 
    dateTo: Optional[str] = None
):
    """
    Get detection results grouped by date.
    Optionally filter by dateFrom and dateTo.
    Returns a list of dicts, each matching DetectionResultsByCamera model for a date.
    """
    query = select(
        detection_results.c.date,
        detection_results.c.numberOfBicycle,
        detection_results.c.numberOfMotorcycle,
        detection_results.c.numberOfCar,
        detection_results.c.numberOfVan,
        detection_results.c.numberOfTruck,
        detection_results.c.numberOfBus,
        detection_results.c.numberOfFireTruck,
        detection_results.c.numberOfContainer,
    )
    if dateFrom and dateTo:
        if dateFrom.strip() and dateTo.strip():
            query = query.where(
                and_(
                    detection_results.c.date >= dateFrom,
                    detection_results.c.date <= dateTo
                )
            )
    elif dateFrom:
        if dateFrom.strip():
            query = query.where(detection_results.c.date >= dateFrom)
    elif dateTo:
        if dateTo.strip():
            query = query.where(detection_results.c.date <= dateTo)

    rows = await db.fetch_all(query)
    if not rows:
        return None

    # Aggregate by date
    details_dict = {}
    for row in rows:
        key = row["date"]
        if key not in details_dict:
            details_dict[key] = {
                "date": row["date"],
                "numberOfBicycle": 0,
                "numberOfMotorcycle": 0,
                "numberOfCar": 0,
                "numberOfVan": 0,
                "numberOfTruck": 0,
                "numberOfBus": 0,
                "numberOfFireTruck": 0,
                "numberOfContainer": 0,
            }
        details_dict[key]["numberOfBicycle"] += row["numberOfBicycle"]
        details_dict[key]["numberOfMotorcycle"] += row["numberOfMotorcycle"]
        details_dict[key]["numberOfCar"] += row["numberOfCar"]
        details_dict[key]["numberOfVan"] += row["numberOfVan"]
        details_dict[key]["numberOfTruck"] += row["numberOfTruck"]
        details_dict[key]["numberOfBus"] += row["numberOfBus"]
        details_dict[key]["numberOfFireTruck"] += row["numberOfFireTruck"]
        details_dict[key]["numberOfContainer"] += row["numberOfContainer"]

    details = list(details_dict.values())
    
    return details


async def fetch_cameras_from_api() -> List[Dict]:
    async with httpx.AsyncClient() as client:
        response = await client.get(CAMERA_API_URL)
        response.raise_for_status()
        data = response.json()
        rs = [{"camera_id": x["_id"], "loc": x["loc"]} for x in data]
        return rs

async def get_heatmap(db: Database, date: str, timeFrom: Optional[str] = None, timeTo: Optional[str] = None) -> dict:
    """
    Get heatmap data for a specific date and optional time range.
    Returns a dict matching HeatmapResult model.
    """
    cameraList = await fetch_cameras_from_api()
    query = select(
        detection_results.c.date,
        detection_results.c.time,
        detection_results.c.cameraId,
        detection_results.c.numberOfBicycle,
        detection_results.c.numberOfMotorcycle,
        detection_results.c.numberOfCar,
        detection_results.c.numberOfVan,
        detection_results.c.numberOfTruck,
        detection_results.c.numberOfBus,
        detection_results.c.numberOfFireTruck,
        detection_results.c.numberOfContainer,
    ).where(detection_results.c.date == date)

    if timeFrom and timeTo:
        query = query.where(
            and_(
                detection_results.c.time >= timeFrom,
                detection_results.c.time <= timeTo
            )
        )

    rows = await db.fetch_all(query)
    if not rows:
        return None

    # Aggregate by (cameraId)
    details_dict = {}
    for row in rows:
        key = (row["cameraId"])
        if key not in details_dict:
            location = next((x["loc"] for x in cameraList if x["camera_id"] == key), None)
            if location is None:
                # Skip this camera if location is missing to avoid validation error
                continue
            details_dict[key] = {
                "date": row["date"],
                "camera": key,
                "loc": location,
                "numberOfBicycle": 0,
                "numberOfMotorcycle": 0,
                "numberOfCar": 0,
                "numberOfVan": 0,
                "numberOfTruck": 0,
                "numberOfBus": 0,
                "numberOfFireTruck": 0,
                "numberOfContainer": 0,
            }
        details_dict[key]["numberOfBicycle"] += row["numberOfBicycle"]
        details_dict[key]["numberOfMotorcycle"] += row["numberOfMotorcycle"]
        details_dict[key]["numberOfCar"] += row["numberOfCar"]
        details_dict[key]["numberOfVan"] += row["numberOfVan"]
        details_dict[key]["numberOfTruck"] += row["numberOfTruck"]
        details_dict[key]["numberOfBus"] += row["numberOfBus"]
        details_dict[key]["numberOfFireTruck"] += row["numberOfFireTruck"]
        details_dict[key]["numberOfContainer"] += row["numberOfContainer"]

    details = list(details_dict.values())

    # Sum up all vehicle counts for the specified date and time range
    result = {
        "date": date,
        "timeFrom": timeFrom or "",
        "timeTo": timeTo or "",
        "numberOfBicycle": 0,
        "numberOfMotorcycle": 0,
        "numberOfCar": 0,
        "numberOfVan": 0,
        "numberOfTruck": 0,
        "numberOfBus": 0,
        "numberOfFireTruck": 0,
        "numberOfContainer": 0,
        "details": details
    }
    
    for d in details:
        result["numberOfBicycle"] += d["numberOfBicycle"]
        result["numberOfMotorcycle"] += d["numberOfMotorcycle"]
        result["numberOfCar"] += d["numberOfCar"]
        result["numberOfVan"] += d["numberOfVan"]
        result["numberOfTruck"] += d["numberOfTruck"]
        result["numberOfBus"] += d["numberOfBus"]
        result["numberOfFireTruck"] += d["numberOfFireTruck"]
        result["numberOfContainer"] += d["numberOfContainer"]
        
    return result

async def get_heatmap_in_a_day(db: Database, date: str, timeFrom: Optional[str] = None, timeTo: Optional[str] = None):  
    """
    Get heatmap data for a specific date, grouped by hour.
    Returns a dict matching HeatmapInADay model.
    """
    cameraList = await fetch_cameras_from_api()
    # Fetch all detection results for the date
    query = select(
        detection_results.c.date,
        detection_results.c.time,
        detection_results.c.cameraId,
        detection_results.c.numberOfBicycle,
        detection_results.c.numberOfMotorcycle,
        detection_results.c.numberOfCar,
        detection_results.c.numberOfVan,
        detection_results.c.numberOfTruck,
        detection_results.c.numberOfBus,
        detection_results.c.numberOfFireTruck,
        detection_results.c.numberOfContainer,
    ).where(detection_results.c.date == date)
    
    print(f"Fetching heatmap for date: {date}, timeFrom: {timeFrom}, timeTo: {timeTo}")
    
    if timeFrom and timeTo:
        query = query.where(
            and_(
                detection_results.c.time >= timeFrom,
                detection_results.c.time <= timeTo
            )
        )
    
    rows = await db.fetch_all(query)
    if not rows:
        return None

    # {hour: {cameraId: {...}}}
    hour_camera_dict = defaultdict(lambda: defaultdict(lambda: {
        "camera": None,
        "loc": None,
        "numberOfBicycle": 0,
        "numberOfMotorcycle": 0,
        "numberOfCar": 0,
        "numberOfVan": 0,
        "numberOfTruck": 0,
        "numberOfBus": 0,
        "numberOfFireTruck": 0,
        "numberOfContainer": 0,
    }))

    # For total sum
    total = {
        "numberOfBicycle": 0,
        "numberOfMotorcycle": 0,
        "numberOfCar": 0,
        "numberOfVan": 0,
        "numberOfTruck": 0,
        "numberOfBus": 0,
        "numberOfFireTruck": 0,
        "numberOfContainer": 0,
    }

    for row in rows:
        # Group by hour (HH:00:00)
        hour = row["time"][:2] + ":00:00"
        cam_id = row["cameraId"]
        location = next((x["loc"] for x in cameraList if x["camera_id"] == cam_id), None)
        cam_data = hour_camera_dict[hour][cam_id]
        cam_data["camera"] = cam_id
        cam_data["loc"] = location
        cam_data["numberOfBicycle"] += row["numberOfBicycle"]
        cam_data["numberOfMotorcycle"] += row["numberOfMotorcycle"]
        cam_data["numberOfCar"] += row["numberOfCar"]
        cam_data["numberOfVan"] += row["numberOfVan"]
        cam_data["numberOfTruck"] += row["numberOfTruck"]
        cam_data["numberOfBus"] += row["numberOfBus"]
        cam_data["numberOfFireTruck"] += row["numberOfFireTruck"]
        cam_data["numberOfContainer"] += row["numberOfContainer"]

        # Sum for the whole day
        total["numberOfBicycle"] += row["numberOfBicycle"]
        total["numberOfMotorcycle"] += row["numberOfMotorcycle"]
        total["numberOfCar"] += row["numberOfCar"]
        total["numberOfVan"] += row["numberOfVan"]
        total["numberOfTruck"] += row["numberOfTruck"]
        total["numberOfBus"] += row["numberOfBus"]
        total["numberOfFireTruck"] += row["numberOfFireTruck"]
        total["numberOfContainer"] += row["numberOfContainer"]

    # Build details: list of HeatInTime (one per hour)
    details = []
    for hour in sorted(hour_camera_dict.keys()):
        data = list(hour_camera_dict[hour].values())
        details.append({
            "time": hour,
            "data": data
        })

    result = {
        "date": date,
        "timeFrom": timeFrom or "00:00:00",
        "timeTo": timeTo or "23:59:59",
        **total,
        "details": details
    }
    return result