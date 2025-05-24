from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Depends
from app.api.models import Camera, FollowRequest, FollowCamera, CreateCamera
from app.api import db_manager
from app.api.db_manager import DBManager
from sqlalchemy.orm import Session
from app.api.db import get_db
from databases import Database
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, TemplateId, Substitution
from sqlalchemy import select
import httpx
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

cameras = APIRouter()
@cameras.get("/all-api-cameras-information", response_model=List[Camera])
async def list_all_cameras() -> List[Camera]:
    return await db_manager.get_all_cameras()

@cameras.post("/write-all-cameras", response_model=str)
async def write_all_cameras_to_db(db=Depends(get_db)) -> str:
    try:
        await db_manager.write_all_cameras_to_db(db)
        return "Cameras written to database successfully"
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@cameras.get("/cameras")
async def list_cameras(
    is_enabled: Optional[bool] = None,
    search: Optional[str] = None,
    db=Depends(get_db)
):
    cameras = await db_manager.get_camera_list(db, is_enabled, search)
    return cameras

# @cameras.get("/demo-cameras", response_model=List[Camera])
# async def list_demo_cameras(
#     db=Depends(get_db)
# ) -> List[Camera]:
#     return await db_manager.get_demo_cameras(db)

# @cameras.post("/demo-cameras", response_model=Camera)
# async def create_demo_camera(
#     camera: CreateCamera,
#     db=Depends(get_db)
# ) -> Camera:
#     return await db_manager.create_demo_camera(db, camera)


# @cameras.put("/demo-cameras/{camera_id}", response_model=Camera)
# async def update_demo_camera(
#     camera: Camera,
#     db=Depends(get_db)
# ) -> Camera:
#     return await db_manager.update_demo_camera(db,  camera)

# @cameras.delete("/demo-cameras/{camera_id}")
# async def delete_demo_camera(
#     camera_id: str,
#     db=Depends(get_db)
# ):
#     return await db_manager.delete_demo_camera(db, camera_id)

# @cameras.get("/follows", response_model=List[FollowRequest])
# async def list_follows(
#     db=Depends(get_db)
# ) -> List[FollowRequest]:
#     return await db_manager.get_follows(db)

# @cameras.get("/follow/{user_id}")
# async def get_follow_camera(userId: str, db=Depends(get_db)):
#     follow = await db_manager.get_follow_camera(db, userId)
#     if not follow:
#         raise HTTPException(status_code=404, detail="Follow camera not found")
#     return follow


@cameras.get("/cameras/{camera_id}")
async def read_camera(camera_id: str, db=Depends(get_db)):
    camera = await db_manager.get_camera_by_id(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera

@cameras.get("/cameras/detection/classes")
async def get_vehicles():
    vehicles = ['bicycle', 'motorcycle', 'car', 'van', 'truck', 'bus', 'fire truck', 'container']
    return vehicles

@cameras.get("/cameras/district/classes")
async def get_vehicles(db=Depends(get_db)):
    districts = await db_manager.get_districts(db)
    if not districts:
        raise HTTPException(status_code=404, detail="No districts found")
    return districts

@cameras.get("/cameras/image/{camera_id}")
async def read_camera_image(camera_id: str, db=Depends(get_db)):
    camera = await db_manager.get_camera_by_id(db, camera_id)
    if not camera or not camera.liveviewUrl:
        raise HTTPException(status_code=404, detail="Camera not found or liveviewUrl missing")
    async with httpx.AsyncClient() as client:   
        response = await client.get(camera.liveviewUrl, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch image from camera")
        content_type = response.headers.get("content-type", "image/jpeg")
        return StreamingResponse(response.aiter_bytes(), media_type=content_type)
    
@cameras.get("/cameras/district/{district}")
async def get_cameras_by_district(district: str, db=Depends(get_db)):
    cameras = await db_manager.get_cameras_by_district(db, district)
    if not cameras:
        raise HTTPException(status_code=404, detail="No cameras found in this district")
    return cameras

class CameraSearchRequest(BaseModel):
    camera_name: str
    district: str

@cameras.post("/cameras/search")
async def search_camera(request: CameraSearchRequest, db=Depends(get_db)):
    cameras = await db_manager.get_camera_by_name_and_district(db, request.camera_name, request.district)
    if not cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cameras

@cameras.put("/cameras/status")
async def modify_multiple_camera_status(
    camera_id_list: List[str],
    is_enabled: bool,
    db: Database = Depends(get_db)
):
    try:
        updated_cameras = await db_manager.update_camera_statuses(db, camera_id_list, is_enabled)

        if updated_cameras:
            return {"updated": len(updated_cameras), "status": "success"}
        else:
            raise HTTPException(
                status_code=404, detail="No cameras found or updated")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}")


@cameras.post("/cameras/follow")
async def follow_camera(
    requestInfo: FollowRequest,
    db: Database = Depends(get_db)
):
    try:
        new_follow = await db_manager.follow_camera_service(db, requestInfo)
        return new_follow
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@cameras.delete("/cameras/follow")
async def unfollow_camera(cameraId: str, userId: str, db=Depends(get_db)):
    deleted = await db_manager.unfollow_camera_service(db, cameraId, userId)
    if not deleted:
        raise HTTPException(
            status_code=404, detail="Follow camera not found")
    return {"message": "Follow camera deleted successfully"}


@cameras.post("/cameras/send-email/{_id}")
async def send_email(_id: str, db=Depends(get_db)):
    await db_manager.send_email(_id, db)
