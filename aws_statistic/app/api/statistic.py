from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Depends
from app.api.models import DetectionTime, DetectionDate, DetectionResultsByDate, CustomDetectionResultsInADay, DetectionResultsByDistrict, DetectionResultsByCamera, ResultDetailByDay, HeatmapResult, CameraResultInADay, HeatmapInADay, scheduleInfo
from app.api import db_manager
from app.api.database import get_db
from databases import Database
import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.api.email_builder import build_stats_email_html, generate_chart_image
from fastapi import Body
import os
from uuid import uuid4

statistic = APIRouter()

# CAMERA_SERVICE_URL = "http://localhost:8002"
CAMERA_SERVICE_URL = "http://nginx:8080"

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
    
@statistic.get("/custom_detection_results_by_camera", response_model=DetectionResultsByCamera)
async def get_custom_detection_results_by_camera(
    camera: str, db: Database = Depends(get_db)
) -> DetectionResultsByCamera:
    """Get custom detection results by camera."""
    result = await db_manager.get_custom_detection_results_by_camera(
        db, camera
    )
    if not result:
        raise HTTPException(status_code=404, detail="Custom detection results not found for the given district")
    return result

@statistic.get("/traffic_tracking_by_date", response_model=List[ResultDetailByDay])
async def get_traffic_tracking_by_date(
    db: Database = Depends(get_db)
) -> List[ResultDetailByDay]:
    """Get custom detection results by date."""
    result = await db_manager.get_traffic_tracking_by_date(
        db
    )
    if not result:
        raise HTTPException(status_code=404, detail="Custom detection results not found for the given district")
    return result

@statistic.get("/heatmap", response_model=HeatmapResult)
async def get_heatmap(
    date: str,
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
    db: Database = Depends(get_db)
) -> HeatmapResult:
    """Get heatmap data."""
    if time_from is None:
        time_from = "00:00:00"
    if time_to is None:
        time_to = "23:59:59"
    result = await db_manager.get_heatmap(db, date, time_from, time_to)
    if not result:
        raise HTTPException(status_code=404, detail="Heatmap data not found for the given date and time range")
    return result

@statistic.get("/traffic_tracking_by_camera_in_date", response_model=CameraResultInADay)
async def get_traffic_tracking_by_camera_in_date(
    db: Database = Depends(get_db),
    date: str = None,
    camera: str = None,
    timeFrom: Optional[str] = None,
    timeTo: Optional[str] = None,
) -> CameraResultInADay:
    """Get custom detection results by camera."""
    
    result = await db_manager.get_traffic_tracking_by_camera_in_date(
        db, date, camera, timeFrom, timeTo
    )
    if not result:
        raise HTTPException(status_code=404, detail="Custom detection results not found for the given district")
    return result

@statistic.get("/heatmap_in_a_day", response_model=HeatmapInADay)
async def get_heatmap_in_a_day(
    db: Database = Depends(get_db),
    date: str = None,
    timeFrom: Optional[str] = None,
    timeTo: Optional[str] = None,
) -> HeatmapInADay:
    """Get custom detection heatmap results by camera."""
    result = await db_manager.get_heatmap_in_a_day(
        db, date, timeFrom, timeTo
    )
    if not result:
        raise HTTPException(status_code=404, detail="Custom detection results not found for the given district")
    return result

@statistic.get("/get_scheduled_info", response_model=List[scheduleInfo])
async def get_scheduled_info(
    email: Optional[str] = None,
    db: Database = Depends(get_db)
):
    schedule = await db_manager.get_scheduled_info(db, email)
    if not schedule:
        raise HTTPException(status_code=404, detail="Scheduled information not found")
    return schedule

@statistic.post("/add_new_schedule")
async def add_new_schedule(
    email: str = Body(..., embed=True),
    dateFrom: Optional[str] = Body(None, embed=True),
    dateTo: Optional[str] = Body(None, embed=True),
    db: Database = Depends(get_db)
):
    """
    Add a new schedule for sending detection statistics via email.
    """
    if not email or not dateFrom or not dateTo:
        raise HTTPException(status_code=400, detail="Missing required fields")

    try:
        await db_manager.add_new_schedule(db, email, dateFrom, dateTo)
        return {"message": "Schedule added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add schedule: {str(e)}")

@statistic.post("/cancel_schedule")
async def cancel_schedule(
    scheduleId: str = Body(..., embed=True),
    db: Database = Depends(get_db)
):
    """
    Cancel a scheduled email for detection statistics.
    """
    if not scheduleId:
        raise HTTPException(status_code=400, detail="Missing schedule ID")

    try:
        await db_manager.update_schedule_status(db, scheduleId, "cancelled")
        return {"message": "Schedule cancelled successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel schedule: {str(e)}")

from datetime import datetime, date
from fastapi.responses import JSONResponse

@statistic.post("/send_email_by_date")
async def send_email(
    email: str = Body(..., embed=True),
    dateFrom: Optional[str] = Body(None, embed=True),
    dateTo: Optional[str] = Body(None, embed=True),
    db: Database = Depends(get_db)
):
    """
    Send detection statistics via email for a given date range using SMTP.
    """
    scheduleId = str(uuid4())
    
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

    if not SMTP_USERNAME or not SMTP_PASSWORD:
        raise HTTPException(status_code=500, detail="SMTP credentials not configured")
    
    # Add schedule information to the database
    try:
        await db_manager.add_new_schedule(db, email, dateFrom, dateTo, scheduleId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add schedule: {str(e)}")

    # Parse and validate dateTo
    try:
        date_to_obj = datetime.strptime(dateTo, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid dateTo format. Expected YYYY-MM-DD")

    today = date.today()

    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_USERNAME
    msg["To"] = email

    if date_to_obj >= today:
        # Notify email for future date
        msg["Subject"] = f"📅 Notification: Scheduled Statistics Report"
        body = f"This is a notification that a statistics report is scheduled for the future date: {dateTo}."
        msg.attach(MIMEText(body, "plain"))
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(SMTP_USERNAME, [email], msg.as_string())
            return JSONResponse(status_code=201, content={"message": "Notification email sent for future date"})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to send notification email: {str(e)}")
    else:
        # Normal statistics email
        stats = await db_manager.get_traffic_tracking_by_date(db, dateFrom, dateTo)
        if not stats:
            raise HTTPException(status_code=404, detail="No statistics found for the given date range")

        html_content = build_stats_email_html(stats, dateFrom, dateTo)
        msg["Subject"] = f"🚦 Detection Statistics from {dateFrom} to {dateTo}"

        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText("Your email client does not support HTML.", "plain"))
        alt_part.attach(MIMEText(html_content, "html"))
        msg.attach(alt_part)

        # Attach chart image
        image = generate_chart_image(stats)
        msg.attach(image)

        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(SMTP_USERNAME, [email], msg.as_string())
            # Update schedule status to "sent"
            await db_manager.update_schedule_status(db, scheduleId, "sent")
            return {"message": "Statistics email sent successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
