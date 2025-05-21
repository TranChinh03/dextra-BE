from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx
from app.api.db import cameras, get_db, follow_camera, demoCameras
from app.api.models import CAMERA_API_URL, Camera, FollowRequest, FollowCamera, CreateCamera
from databases import Database
from pydantic import ValidationError
from sqlalchemy import insert, or_, select, update, and_, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException
from uuid import uuid4
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To
import asyncio

camera_status = {}

def truncate_string(value: str, max_length: int = 50) -> str:
    if isinstance(value, str) and len(value) > max_length:
        return value[:max_length]
    return value

class DBManager:
    def __init__(self, session: get_db):
        self.session = session

async def fetch_cameras_from_api() -> List[Dict]:
    async with httpx.AsyncClient() as client:
        response = await client.get(CAMERA_API_URL)
        response.raise_for_status()
        data = response.json()
        return data
    
async def get_all_cameras() -> List[Camera]:
    camera_list = []
    api_data = await fetch_cameras_from_api()
    for camera in api_data:
        camera['isEnabled'] = True
        camera['liveviewUrl'] = f"http://giaothong.hochiminhcity.gov.vn/render/ImageHandler.ashx?id={camera['_id']}"

    for camera in api_data:
        try:
            camera_obj = Camera(**camera)
            camera_list.append(camera_obj)
        except ValidationError as e:
            print(f"Validation error for camera data: {camera}")
            print(e)
    return camera_list

async def delete_all_cameras(db: Database) -> str:
    stmt = delete(cameras)
    await db.execute(stmt)
    return "All cameras deleted successfully"

async def write_all_cameras_to_db(db: Database) -> str:
    api_data = await fetch_cameras_from_api()
    
    for camera in api_data:
        print(f"Processing camera: {camera.get('angle')}")
        
        # camera angle can be None -> set to 0
        if not(camera.get('angle')):
            camera['angle'] = 0
            
        new_camera_data = {
            '_id': camera['_id'],
            'id': camera['id'],
            'name': camera['name'],
            'loc': camera['loc'],
            'values': camera['values'],
            'dist': camera['dist'],
            'ptz': camera['ptz'],
            'angle': camera['angle'],
            'liveviewUrl': f"http://giaothong.hochiminhcity.gov.vn/render/ImageHandler.ashx?id={camera['_id']}",
            'isEnabled': True,
            'lastmodified': datetime.utcnow()
        }
        stmt = insert(cameras).values(new_camera_data)
        try: 
            await db.execute(stmt)
        except IntegrityError:
            print(f"Camera with id {camera.id} already exists in the database.")
            pass

async def get_camera_by_id(db: Database, camera_id: str) -> dict:
    query = select(cameras).where(cameras.c._id == camera_id)
    result = await db.fetch_one(query)
    return result

async def get_camera_by_name(db: Database, camera_name: str) -> dict:
    print(f"Searching for camera with name: {camera_name}")
    query = select(cameras).where(cameras.c.name.ilike(f"%{camera_name}%")) 
    result = await db.fetch_all(query)
    return result

async def get_demo_cameras(db: Database) -> List[Camera]:
    query = select([demoCameras])
    return await db.fetch_all(query)

async def create_demo_camera(db: Database, camera: CreateCamera) -> Camera:
    new_camera_data = {
        '_id': str(uuid4()),
        'id': camera.id,
        'name': camera.name,
        'loc': camera.loc.dict(),
        'values': camera.values,
        'dist': camera.dist,
        'ptz': camera.ptz,
        'angle': camera.angle,
        'liveviewUrl': camera.liveviewUrl,
        'isEnabled': camera.isEnabled,  
        'lastmodified': datetime.utcnow()
    }
    insert_query = demoCameras.insert().values(
            new_camera_data
        )
    print(f"insert_query: {insert_query}")

    await db.execute(insert_query)
    return new_camera_data

async def update_demo_camera(db: Database,  camera: Camera) -> dict:
    stmt = update(demoCameras).where(demoCameras.c._id == camera.camera_id).values(camera)
    try:
        await db.execute(stmt)
    except IntegrityError:
        return None
    return camera

async def delete_demo_camera(db: Database, camera_id: str) -> dict:
    query = delete(demoCameras).where(demoCameras.c._id == camera_id)
    result = await db.execute(query)
    if result == 0:
        return None
    return {'_id': camera_id}

async def update_camera_statuses(db: Database, camera_ids: List[str], is_enabled: bool) -> List[dict]:
    updated_cameras = []
    api_data = await get_camera_list(db)
    
    for camera in api_data:
        if camera.camera_id in camera_ids:
            updated_cameras.append(camera)
     
    for camera in updated_cameras:
        stmt = select([cameras]).where(cameras.c.id == camera.id)
        result = await db.fetch_one(stmt)
        if is_enabled:
            if result is None:
                new_camera_data = {
                    '_id': camera.camera_id,
                    'id': camera.id,
                    'name': truncate_string(camera.name),
                    'loc': camera.loc.dict(),
                    'values': camera.values,
                    'dist': truncate_string(camera.dist),
                    'ptz': camera.ptz,
                    'angle': camera.angle,
                    'liveviewUrl': 'http://giaothong.hochiminhcity.gov.vn/render/ImageHandler.ashx?id={camera.camera_id}',
                    'isEnabled': False,
                    'lastmodified':  datetime.utcnow()
                }
                stmt = insert(cameras).values(new_camera_data)
                try:
                    await db.execute(stmt)
                except IntegrityError:
                    pass
        elif result is not None:
            query = delete(cameras).where(
                and_(
                cameras.c._id == camera.camera_id,
                cameras.c.id == camera.id,
                )
            )
            await db.execute(query)

    return updated_cameras

async def get_camera_list(
    db: Database,
    is_enabled: Optional[bool] = None,
    search: Optional[str] = None
) -> List[Camera]:
    api_data = await fetch_cameras_from_api()

    stmt = select(cameras)
    db_cameras = await db.fetch_all(stmt)
    
    camera_ids_from_db = {camera['_id'] for camera in db_cameras}

    for camera in api_data:
        if camera['_id'] in camera_ids_from_db:
            camera['isEnabled'] = True
            camera['liveviewUrl'] = f"http://giaothong.hochiminhcity.gov.vn/render/ImageHandler.ashx?id={camera['_id']}"
        else:
            camera['isEnabled'] = False

    if is_enabled is not None:
        api_data = [camera for camera in api_data if camera['isEnabled'] == is_enabled]
    if search:
        search_pattern = f"%{search}%"
        api_data = [
            camera for camera in api_data
            if search_pattern in camera['name']
            or search_pattern in camera['id']
            or search_pattern in camera['dist']]
    return [Camera(**camera) for camera in api_data]

async def get_follow_camera(
    db: Database,
    user_id: str
) -> List[str]:  # Return type is now a list of strings (cameraIds)
    query = select([follow_camera.c.cameraId]).where(
        follow_camera.c.userId == user_id)  # Select only cameraId
    results = await db.fetch_all(query)

    return [result["cameraId"] for result in results]

async def get_follows(db: Database):
    query = follow_camera.select()
    return await db.fetch_all(query=query)

async def follow_camera_service(db: Database, request: FollowRequest):
    camera_query = await db.fetch_one(
        select([cameras]).where(cameras.c._id == request.cameraId)
    )

    if camera_query is None:
            query = select([demoCameras]).where(demoCameras.c._id == request.cameraId)
            camera_query = await db.fetch_one(query)
        
    if camera_query is None:
        raise HTTPException(status_code=404, detail="Camera does not exist")

    follow_query = await db.fetch_one(
        select([follow_camera]).where(
            and_(
                follow_camera.c.cameraId == request.cameraId,
                follow_camera.c.userId == request.userId
            )
        )
    )
    if follow_query is not None:
        raise HTTPException(
            status_code=400, detail="User already following this camera"
        )

    follow_entry = {
        '_id': str(uuid4()),
        'cameraId': request.cameraId,
        'userId': request.userId,
        'userEmail': request.userEmail,
    }
    insert_query = insert(follow_camera).values(follow_entry)
    await db.execute(insert_query)

    return follow_entry

async def unfollow_camera_service(db: Database, cameraId: str, userId: str):
    query = delete(follow_camera).where(
        and_(
            follow_camera.c.cameraId == cameraId,
            follow_camera.c.userId == userId
        )
    )

    result = await db.execute(query)

    if result == 0:
        raise HTTPException(
            status_code=404, detail="Follow camera not found"
        )

    return {"message": "Follow camera deleted successfully"}

# async def send_email(camera_id: str, db: Database):
    try:
        # Fetch all camera follow entries for the given camera_id
        camera_queries = await db.fetch_all(
            select([follow_camera]).where(follow_camera.c.cameraId == camera_id)
        )

        if not camera_queries:
            raise HTTPException(
                status_code=404, detail="No matching rows found for the given camera ID"
            )

        # Extract unique user emails
        user_emails = list({query.get("userEmail") for query in camera_queries if query.get("userEmail")})
        
        if not user_emails:
            raise HTTPException(
                status_code=400, detail="No userEmail addresses found for the given camera ID"
            )

        # Fetch camera details from the primary cameras table
        camera_detail_query = await db.fetch_one(
            select([cameras]).where(cameras.c._id == camera_id)
        )

        # If not found in primary, fetch from demoCameras
        if camera_detail_query is None:
            camera_detail_query = await db.fetch_one(
                select([demoCameras]).where(demoCameras.c._id == camera_id)
            )

        if not camera_detail_query:
            raise HTTPException(
                status_code=404, detail="No camera details found for the given camera ID"
            )

        # Convert datetime fields to string if they exist
        camera_details = dict(camera_detail_query)
        if isinstance(camera_details.get('lastmodified'), datetime):
            camera_details['lastmodified'] = camera_details['lastmodified'].strftime(
                '%Y-%m-%d %H:%M:%S'
            )


        async def send_single_email(user_email: str):
            try:
                message = Mail(
                    from_email=From('y.levan@ncc.asia', 'Safe Move Support'),
                    to_emails=To(user_email),
                )
                message.template_id = 'd-764126dba9db453da61ce904a3afb5b6'

                # Dynamic template data for the email
                message.dynamic_template_data = {
                    "username": next(
                        (query.get("userName", "User") for query in camera_queries if query.get("userEmail") == user_email),
                        "User"
                    ),
                    **camera_details,
                }

                # Send the email
                response = sg.send(message)
                
                if response.status_code >= 400:
                    print(f"Failed to send email to {user_email}: {response.status_code}")
                else:
                    print(f"Email sent successfully to {user_email}")
            except Exception as e:
                print(f"An error occurred while sending email to {user_email}: {str(e)}")
                # Optionally, handle individual email sending failures without stopping the entire process

        # Create a list of coroutine tasks for sending emails
        email_tasks: List[asyncio.Task] = [
            asyncio.create_task(send_single_email(email)) for email in user_emails
        ]

        # Await all email sending tasks
        await asyncio.gather(*email_tasks)

        return {
            "message": "Emails sent successfully",
            "emails": user_emails,
        }

    except HTTPException as http_exc:
        # Re-raise HTTP exceptions to be handled by FastAPI
        raise http_exc
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send the emails")