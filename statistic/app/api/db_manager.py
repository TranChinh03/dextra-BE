from app.api.database import get_db, detection_results
from app.api.models import DetectionResults
from databases import Database
from sqlalchemy import insert, or_, select, update, and_, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException

class DBManager:
    def __init__(self, session: get_db):
        self.session = session

async def get_timestamp(db: Database) -> object:
    query = select(detection_results.c.date, detection_results.c.time).distinct()
    result = await db.fetch_all(query)
    return result

async def get_date(db: Database) -> object:
    query = select(detection_results.c.date).distinct()
    result = await db.fetch_all(query)
    return result

async def get_detection_results_by_date(date: str, db: Database) -> dict:
    """
    Get summed detection results for a specific date.
    Returns a dict matching DetectionResultsByDate model.
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
    ).where(detection_results.c.date == date)
    rows = await db.fetch_all(query)
    if not rows:
        return None
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
    }
    for row in rows:
        result["numberOfBicycle"] += row["numberOfBicycle"]
        result["numberOfMotorcycle"] += row["numberOfMotorcycle"]
        result["numberOfCar"] += row["numberOfCar"]
        result["numberOfVan"] += row["numberOfVan"]
        result["numberOfTruck"] += row["numberOfTruck"]
        result["numberOfBus"] += row["numberOfBus"]
        result["numberOfFireTruck"] += row["numberOfFireTruck"]
        result["numberOfContainer"] += row["numberOfContainer"]
    return result

async def get_custom_detection_results(db: Database, date: str, timeFrom: str, timeTo: str):
    """
    Get detection results for a specific date and time range.
    Returns a dict matching CustomDetectionResults model.
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
            or_(
                (detection_results.c.time >= timeFrom),
                (detection_results.c.time <= timeTo)
            )
        )
    )
    rows = await db.fetch_all(query)
    if not rows:
        return None
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
    }
    for row in rows:
        result["numberOfBicycle"] += row["numberOfBicycle"]
        result["numberOfMotorcycle"] += row["numberOfMotorcycle"]
        result["numberOfCar"] += row["numberOfCar"]
        result["numberOfVan"] += row["numberOfVan"]
        result["numberOfTruck"] += row["numberOfTruck"]
        result["numberOfBus"] += row["numberOfBus"]
        result["numberOfFireTruck"] += row["numberOfFireTruck"]
        result["numberOfContainer"] += row["numberOfContainer"]
    return result

async def get_custom_detection_results_by_district(db: Database, district: str, date: str, timeFrom: str, timeTo: str, cameraList: list):
    """
    Get detection results for a specific district, date, and time range.
    Returns a list of dicts matching DetectionResultsByDistrict model.
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
            or_(
                (detection_results.c.time >= timeFrom),
                (detection_results.c.time <= timeTo)
            ),
            detection_results.c.cameraId.in_([cam["_id"] for cam in cameraList])
        )
    )
    rows = await db.fetch_all(query)
    if not rows:
        return None
    # Sum up all vehicle counts for the specified district, date, and time range
    result = []
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
    }
    for row in rows:
        result["numberOfBicycle"] += row["numberOfBicycle"]
        result["numberOfMotorcycle"] += row["numberOfMotorcycle"]
        result["numberOfCar"] += row["numberOfCar"]
        result["numberOfVan"] += row["numberOfVan"]
        result["numberOfTruck"] += row["numberOfTruck"]
        result["numberOfBus"] += row["numberOfBus"]
        result["numberOfFireTruck"] += row["numberOfFireTruck"]
        result["numberOfContainer"] += row["numberOfContainer"]
    return result