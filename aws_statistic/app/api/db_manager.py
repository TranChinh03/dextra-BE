from app.api.database import get_db, detection_results
from databases import Database
from sqlalchemy import insert, or_, select, update, and_, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException
import httpx
from typing import List, Dict, Optional
from collections import defaultdict
from sqlalchemy import text
from typing import List, Tuple
from datetime import datetime, date, time, timedelta

CAMERA_API_URL = "https://api.notis.vn/v4/cameras/bybbox?lat1=11.160767&lng1=106.554166&lat2=9.45&lng2=128.99999"

class DBManager:
    def __init__(self, session: get_db):
        self.session = session

async def get_partition_table_names(db) -> List[str]:
    """
    Lấy tất cả các tên bảng partition bắt đầu bằng 'detections_' từ hệ thống.
    """
    query = text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name LIKE 'detections_%'
    """)
    rows = await db.fetch_all(query)
    return [row["table_name"] for row in rows]

async def get_timestamp(db) -> List[Tuple[str, str]]:
    """
    Lấy tất cả (date, time) từ mọi bảng partition dạng detections_YYYYMMDD.
    """
    results = []
    tables = await get_partition_table_names(db)

    for table_name in tables:
        query = text(f"""
            SELECT DISTINCT date, time
            FROM {table_name}
        """)
        try:
            rows = await db.fetch_all(query)
            results.extend(rows)
        except Exception as e:
            print(f"Warning: Cannot access {table_name}. Error: {e}")
            continue

    # Dùng set để loại trùng
    unique_results = { (r["date"], r["time"]) for r in results }

    # Trả về đúng định dạng yêu cầu
    formatted_results = [
        { "date": str(d), "time": str(t) } for d, t in sorted(unique_results)
    ]

    return formatted_results

async def get_date(db) -> List[Dict[str, str]]:
    all_dates = set()
    tables = await get_partition_table_names(db)

    for table_name in tables:
        query = text(f"SELECT DISTINCT date FROM {table_name}")
        try:
            rows = await db.fetch_all(query)
            for row in rows:
                all_dates.add(str(row["date"]))
        except Exception as e:
            print(f"Warning: Cannot query {table_name}. Error: {e}")
            continue

    sorted_dates = sorted(all_dates)

    return [{ "date": d } for d in sorted_dates]

async def get_detection_results_by_date(date: str, db: Database) -> Optional[Dict]:
    """
    Truy vấn dữ liệu từ bảng partition detections_YYYYMMDD tương ứng với ngày truyền vào.
    Không cần WHERE date = :date vì bảng đã chia theo ngày.
    """
    table_name = f"detections_{date.replace('-', '')}"

    query = text(f"""
        SELECT
            date,
            time,
            numberofbicycle,
            numberofmotorcycle,
            numberofcar,
            numberofvan,
            numberoftruck,
            numberofbus,
            numberoffiretruck,
            numberofcontainer
        FROM {table_name}
    """)

    try:
        rows = await db.fetch_all(query)
    except Exception as e:
        print(f"Error querying {table_name}: {e}")
        return None

    if not rows:
        return None

    # Gộp theo (date, time)
    details_dict = {}
    for row in rows:
        key = (row["date"], row["time"])
        if key not in details_dict:
            details_dict[key] = {
                "date": str(row["date"]),
                "time": str(row["time"]),
                "numberOfBicycle": 0,
                "numberOfMotorcycle": 0,
                "numberOfCar": 0,
                "numberOfVan": 0,
                "numberOfTruck": 0,
                "numberOfBus": 0,
                "numberOfFireTruck": 0,
                "numberOfContainer": 0,
            }
        details_dict[key]["numberOfBicycle"] += row["numberofbicycle"]
        details_dict[key]["numberOfMotorcycle"] += row["numberofmotorcycle"]
        details_dict[key]["numberOfCar"] += row["numberofcar"]
        details_dict[key]["numberOfVan"] += row["numberofvan"]
        details_dict[key]["numberOfTruck"] += row["numberoftruck"]
        details_dict[key]["numberOfBus"] += row["numberofbus"]
        details_dict[key]["numberOfFireTruck"] += row["numberoffiretruck"]
        details_dict[key]["numberOfContainer"] += row["numberofcontainer"]

    details = list(details_dict.values())

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

def convert_str_to_time(time_str: str) -> time:
    """
    Chuyển đổi chuỗi thời gian định dạng 'HH:MM:SS' thành đối tượng time.
    """
    try:
        return datetime.strptime(time_str, "%H:%M:%S").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM:SS.")

async def get_custom_detection_results(db: Database, date: str, timeFrom: str, timeTo: str) -> Optional[Dict]:
    """
    Truy vấn dữ liệu từ bảng partition detections_YYYYMMDD tương ứng với ngày truyền vào và khoảng thời gian.
    Trả về kết quả theo định dạng CustomDetectionResults.
    """
    table_name = f"detections_{date.replace('-', '')}"
    time_from = convert_str_to_time(timeFrom)
    time_to = convert_str_to_time(timeTo)
    query = text(f"""
        SELECT
            date,
            time,
            numberofbicycle,
            numberofmotorcycle,
            numberofcar,
            numberofvan,
            numberoftruck,
            numberofbus,
            numberoffiretruck,
            numberofcontainer
        FROM {table_name}
        WHERE time >= :time_from AND time <= :time_to
    """).params(time_from=time_from, time_to=time_to)

    try:
        rows = await db.fetch_all(query)
    except Exception as e:
        print(f"Error querying {table_name}: {e}")
        return None

    if not rows:
        return None

    # Gộp dữ liệu theo (date, time)
    details_dict = {}
    for row in rows:
        key = (row["date"], row["time"])
        if key not in details_dict:
            details_dict[key] = {
                "date": str(row["date"]),
                "time": str(row["time"]),
                "numberOfBicycle": 0,
                "numberOfMotorcycle": 0,
                "numberOfCar": 0,
                "numberOfVan": 0,
                "numberOfTruck": 0,
                "numberOfBus": 0,
                "numberOfFireTruck": 0,
                "numberOfContainer": 0,
            }
        details_dict[key]["numberOfBicycle"] += row["numberofbicycle"]
        details_dict[key]["numberOfMotorcycle"] += row["numberofmotorcycle"]
        details_dict[key]["numberOfCar"] += row["numberofcar"]
        details_dict[key]["numberOfVan"] += row["numberofvan"]
        details_dict[key]["numberOfTruck"] += row["numberoftruck"]
        details_dict[key]["numberOfBus"] += row["numberofbus"]
        details_dict[key]["numberOfFireTruck"] += row["numberoffiretruck"]
        details_dict[key]["numberOfContainer"] += row["numberofcontainer"]

    details = list(details_dict.values())
    # Sort details by date, then by time
    details.sort(key=lambda x: (x['date'], x['time']))

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


async def get_custom_detection_results_by_district(
    db: Database,
    district: str,
    date: str,
    timeFrom: str,
    timeTo: str,
    cameraList: List[Dict]
) -> Optional[Dict]:
    """
    Get detection results for a specific district, date, and time range.
    Query data from the correct partition table and filter by camera IDs.
    """
    table_name = f"detections_{date.replace('-', '')}"
    camera_ids = [cam["_id"] for cam in cameraList]
    
    time_from = convert_str_to_time(timeFrom)
    time_to = convert_str_to_time(timeTo)

    # SQL thủ công vì table_name được nhúng trực tiếp
    query = text(f"""
        SELECT
            date,
            time,
            numberofbicycle,
            numberofmotorcycle,
            numberofcar,
            numberofvan,
            numberoftruck,
            numberofbus,
            numberoffiretruck,
            numberofcontainer
        FROM {table_name}
        WHERE time >= :time_from AND time <= :time_to
          AND cameraid = ANY(:camera_ids)
    """).params(time_from=time_from, time_to=time_to, camera_ids=camera_ids)

    try:
        rows = await db.fetch_all(query)
    except Exception as e:
        print(f"Error querying table {table_name}: {e}")
        return None

    if not rows:
        return None

    # Gộp dữ liệu theo (date, time)
    details_dict = {}
    for row in rows:
        key = (row["date"], row["time"])
        if key not in details_dict:
            details_dict[key] = {
                "date": str(row["date"]),
                "time": str(row["time"]),
                "numberOfBicycle": 0,
                "numberOfMotorcycle": 0,
                "numberOfCar": 0,
                "numberOfVan": 0,
                "numberOfTruck": 0,
                "numberOfBus": 0,
                "numberOfFireTruck": 0,
                "numberOfContainer": 0,
            }
        details_dict[key]["numberOfBicycle"] += row["numberofbicycle"]
        details_dict[key]["numberOfMotorcycle"] += row["numberofmotorcycle"]
        details_dict[key]["numberOfCar"] += row["numberofcar"]
        details_dict[key]["numberOfVan"] += row["numberofvan"]
        details_dict[key]["numberOfTruck"] += row["numberoftruck"]
        details_dict[key]["numberOfBus"] += row["numberofbus"]
        details_dict[key]["numberOfFireTruck"] += row["numberoffiretruck"]
        details_dict[key]["numberOfContainer"] += row["numberofcontainer"]

    details = list(details_dict.values())
    # Sort details by date, then by time
    details.sort(key=lambda x: (x['date'], x['time']))

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


async def get_custom_detection_results_by_camera(
    db: Database,
    camera: str
) -> Optional[Dict]:
    """
    Get detection statistics for a specific camera from all available daily partition tables.
    Returns vehicle counts by date and overall total.
    """

    # 1. Tìm các bảng dạng 'detections_YYYYMMDD'
    table_names = await get_partition_table_names(db)

    details_dict = {}

    for table_name in table_names:
        query = text(f"""
            SELECT
                date,
                numberofbicycle,
                numberofmotorcycle,
                numberofcar,
                numberofvan,
                numberoftruck,
                numberofbus,
                numberoffiretruck,
                numberofcontainer
            FROM {table_name}
            WHERE cameraid = :camera
        """).params(camera=camera)

        try:
            rows = await db.fetch_all(query)
        except Exception as e:
            print(f"[Skip] {table_name}: {e}")
            continue

        for row in rows:
            key = row["date"]
            if key not in details_dict:
                details_dict[key] = {
                    "date": str(row["date"]),
                    "numberOfBicycle": 0,
                    "numberOfMotorcycle": 0,
                    "numberOfCar": 0,
                    "numberOfVan": 0,
                    "numberOfTruck": 0,
                    "numberOfBus": 0,
                    "numberOfFireTruck": 0,
                    "numberOfContainer": 0,
                }

            details_dict[key]["numberOfBicycle"] += row["numberofbicycle"]
            details_dict[key]["numberOfMotorcycle"] += row["numberofmotorcycle"]
            details_dict[key]["numberOfCar"] += row["numberofcar"]
            details_dict[key]["numberOfVan"] += row["numberofvan"]
            details_dict[key]["numberOfTruck"] += row["numberoftruck"]
            details_dict[key]["numberOfBus"] += row["numberofbus"]
            details_dict[key]["numberOfFireTruck"] += row["numberoffiretruck"]
            details_dict[key]["numberOfContainer"] += row["numberofcontainer"]

    details = list(details_dict.values())
    # Sort details by date
    details.sort(key=lambda x: x['date'])

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

    return result if details else None

async def get_traffic_tracking_by_camera_in_date(
    db: Database,
    date: str,
    camera: str,
    timeFrom: Optional[str] = None,
    timeTo: Optional[str] = None
) -> Optional[Dict]:
    """
    Truy vấn dữ liệu từ bảng partition theo ngày (ví dụ: detections_20250616)
    cho một camera và (nếu có) khoảng thời gian trong ngày.
    Trả về tổng lượt xe và chi tiết theo từng khung giờ.
    """
    # Xác định tên bảng partition tương ứng với ngày
    table_name = f"detections_{date.replace('-', '')}"

    # Xây dựng truy vấn SQL động
    base_query = f"""
        SELECT
            date,
            time,
            numberofbicycle,
            numberofmotorcycle,
            numberofcar,
            numberofvan,
            numberoftruck,
            numberofbus,
            numberoffiretruck,
            numberofcontainer
        FROM {table_name}
        WHERE cameraid = :camera
    """

    # Bổ sung điều kiện thời gian nếu có
    if timeFrom and timeTo:
        base_query += " AND time >= :time_from AND time <= :time_to"
        time_from = convert_str_to_time(timeFrom)
        time_to = convert_str_to_time(timeTo)

    query = text(base_query).bindparams(
        camera=camera,
        time_from=time_from if timeFrom else None,
        time_to=time_to if timeTo else None
    )

    try:
        rows = await db.fetch_all(query)
    except Exception as e:
        print(f"[ERROR] Failed to query {table_name}: {e}")
        return None

    if not rows:
        return None

    # Khởi tạo kết quả
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

    for row in rows:
        result["numberOfBicycle"] += row["numberofbicycle"]
        result["numberOfMotorcycle"] += row["numberofmotorcycle"]
        result["numberOfCar"] += row["numberofcar"]
        result["numberOfVan"] += row["numberofvan"]
        result["numberOfTruck"] += row["numberoftruck"]
        result["numberOfBus"] += row["numberofbus"]
        result["numberOfFireTruck"] += row["numberoffiretruck"]
        result["numberOfContainer"] += row["numberofcontainer"]

        result["details"].append({
            "date": str(row["date"]),
            "time": str(row["time"]),
            "numberOfBicycle": row["numberofbicycle"],
            "numberOfMotorcycle": row["numberofmotorcycle"],
            "numberOfCar": row["numberofcar"],
            "numberOfVan": row["numberofvan"],
            "numberOfTruck": row["numberoftruck"],
            "numberOfBus": row["numberofbus"],
            "numberOfFireTruck": row["numberoffiretruck"],
            "numberOfContainer": row["numberofcontainer"]
        })

    return result

def extract_date_from_table(table_name: str) -> Optional[str]:
    """
    Từ 'detections_YYYYMMDD' => 'YYYY-MM-DD'
    """
    try:
        raw = table_name.split("_")[1]
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    except Exception:
        return None

async def get_traffic_tracking_by_date(
    db: Database, 
    dateFrom: Optional[str] = None, 
    dateTo: Optional[str] = None
) -> Optional[List[Dict]]:
    """
    Truy vấn các bảng partition và tổng hợp kết quả theo ngày.
    Nếu không truyền dateFrom/dateTo => lấy toàn bộ bảng.
    """
    # Lấy danh sách bảng partition
    table_names = await get_partition_table_names(db)

    # Lọc bảng theo khoảng ngày nếu có
    if dateFrom or dateTo:
        filtered_tables = []
        for tbl in table_names:
            table_date = extract_date_from_table(tbl)
            if table_date:
                if dateFrom and table_date < dateFrom:
                    continue
                if dateTo and table_date > dateTo:
                    continue
                filtered_tables.append(tbl)
        table_names = filtered_tables

    results_dict = {}

    for table_name in table_names:
        query = text(f"""
            SELECT
                date,
                numberofbicycle,
                numberofmotorcycle,
                numberofcar,
                numberofvan,
                numberoftruck,
                numberofbus,
                numberoffiretruck,
                numberofcontainer
            FROM {table_name}
        """)

        try:
            rows = await db.fetch_all(query)
        except Exception as e:
            print(f"[Skip] {table_name}: {e}")
            continue

        for row in rows:
            key = row["date"]
            if key not in results_dict:
                results_dict[key] = {
                    "date": str(key),
                    "numberOfBicycle": 0,
                    "numberOfMotorcycle": 0,
                    "numberOfCar": 0,
                    "numberOfVan": 0,
                    "numberOfTruck": 0,
                    "numberOfBus": 0,
                    "numberOfFireTruck": 0,
                    "numberOfContainer": 0,
                }

            results_dict[key]["numberOfBicycle"] += row["numberofbicycle"]
            results_dict[key]["numberOfMotorcycle"] += row["numberofmotorcycle"]
            results_dict[key]["numberOfCar"] += row["numberofcar"]
            results_dict[key]["numberOfVan"] += row["numberofvan"]
            results_dict[key]["numberOfTruck"] += row["numberoftruck"]
            results_dict[key]["numberOfBus"] += row["numberofbus"]
            results_dict[key]["numberOfFireTruck"] += row["numberoffiretruck"]
            results_dict[key]["numberOfContainer"] += row["numberofcontainer"]

    if not results_dict:
        return None

    return sorted(results_dict.values(), key=lambda x: x["date"])


async def fetch_cameras_from_api() -> List[Dict]:
    async with httpx.AsyncClient() as client:
        response = await client.get(CAMERA_API_URL)
        response.raise_for_status()
        data = response.json()
        rs = [{"camera_id": x["_id"], "loc": x["loc"]} for x in data]
        return rs
    
async def get_heatmap(
    db: Database,
    date: str,
    timeFrom: Optional[str] = None,
    timeTo: Optional[str] = None
) -> Optional[Dict]:
    """
    Get heatmap data for a specific date and optional time range using partitioned table.
    """

    # Gọi API để lấy danh sách camera và toạ độ
    cameraList = await fetch_cameras_from_api()
    camera_lookup = {x["camera_id"]: x["loc"] for x in cameraList}

    # Xác định bảng partition cho ngày đó
    table_name = f"detections_{date.replace('-', '')}"

    # Câu query với SQL thuần (text) vì không thể sử dụng SQLAlchemy ORM khi bảng động
    query = f"""
        SELECT
            cameraid,
            date,
            time,
            numberofbicycle,
            numberofmotorcycle,
            numberofcar,
            numberofvan,
            numberoftruck,
            numberofbus,
            numberoffiretruck,
            numberofcontainer
        FROM {table_name}
        WHERE 1=1
    """
    params = {}

    if timeFrom and timeTo:
        query += " AND time >= :timeFrom AND time <= :timeTo"
        params["timeFrom"] = convert_str_to_time(timeFrom)
        params["timeTo"] = convert_str_to_time(timeTo)

    try:
        rows = await db.fetch_all(text(query).bindparams(**params))
    except Exception as e:
        print(f"[get_heatmap] Error querying table {table_name}: {e}")
        return None

    if not rows:
        return None

    # Tổng hợp theo camera
    details_dict = {}
    for row in rows:
        camera_id = row["cameraid"]
        if camera_id not in camera_lookup:
            continue  # bỏ qua camera không có toạ độ

        if camera_id not in details_dict:
            details_dict[camera_id] = {
                "camera": camera_id,
                "loc": camera_lookup[camera_id],
                "numberOfBicycle": 0,
                "numberOfMotorcycle": 0,
                "numberOfCar": 0,
                "numberOfVan": 0,
                "numberOfTruck": 0,
                "numberOfBus": 0,
                "numberOfFireTruck": 0,
                "numberOfContainer": 0
            }

        details_dict[camera_id]["numberOfBicycle"] += row["numberofbicycle"]
        details_dict[camera_id]["numberOfMotorcycle"] += row["numberofmotorcycle"]
        details_dict[camera_id]["numberOfCar"] += row["numberofcar"]
        details_dict[camera_id]["numberOfVan"] += row["numberofvan"]
        details_dict[camera_id]["numberOfTruck"] += row["numberoftruck"]
        details_dict[camera_id]["numberOfBus"] += row["numberofbus"]
        details_dict[camera_id]["numberOfFireTruck"] += row["numberoffiretruck"]
        details_dict[camera_id]["numberOfContainer"] += row["numberofcontainer"]

    details = list(details_dict.values())

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

    # Tổng hợp toàn bộ số lượng
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

async def get_heatmap_in_a_day(
    db: Database,
    date: str,
    timeFrom: Optional[str] = None,
    timeTo: Optional[str] = None
) -> Optional[Dict]:
    """
    Get heatmap data for a specific date, grouped by hour (using partitioned table).
    Returns a dict matching HeatmapInADay model.
    """
    cameraList = await fetch_cameras_from_api()
    camera_lookup = {x["camera_id"]: x["loc"] for x in cameraList}

    table_name = f"detections_{date.replace('-', '')}"

    query = f"""
        SELECT
            cameraid,
            time,
            numberofbicycle,
            numberofmotorcycle,
            numberofcar,
            numberofvan,
            numberoftruck,
            numberofbus,
            numberoffiretruck,
            numberofcontainer
        FROM {table_name}
        WHERE 1=1
    """

    params = {}
    if timeFrom and timeTo:
        query += " AND time >= :timeFrom AND time <= :timeTo"
        params["timeFrom"] = convert_str_to_time(timeFrom)
        params["timeTo"] = convert_str_to_time(timeTo)

    try:
        rows = await db.fetch_all(text(query).bindparams(**params))
    except Exception as e:
        print(f"[get_heatmap_in_a_day] Error querying table {table_name}: {e}")
        return None

    if not rows:
        return None

    # Grouping by hour and camera
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
        hour = str(row["time"])
        cam_id = row["cameraid"]
        if cam_id not in camera_lookup:
            continue

        cam_data = hour_camera_dict[hour][cam_id]
        cam_data["camera"] = cam_id
        cam_data["loc"] = camera_lookup[cam_id]
        cam_data["numberOfBicycle"] += row["numberofbicycle"]
        cam_data["numberOfMotorcycle"] += row["numberofmotorcycle"]
        cam_data["numberOfCar"] += row["numberofcar"]
        cam_data["numberOfVan"] += row["numberofvan"]
        cam_data["numberOfTruck"] += row["numberoftruck"]
        cam_data["numberOfBus"] += row["numberofbus"]
        cam_data["numberOfFireTruck"] += row["numberoffiretruck"]
        cam_data["numberOfContainer"] += row["numberofcontainer"]

        total["numberOfBicycle"] += row["numberofbicycle"]
        total["numberOfMotorcycle"] += row["numberofmotorcycle"]
        total["numberOfCar"] += row["numberofcar"]
        total["numberOfVan"] += row["numberofvan"]
        total["numberOfTruck"] += row["numberoftruck"]
        total["numberOfBus"] += row["numberofbus"]
        total["numberOfFireTruck"] += row["numberoffiretruck"]
        total["numberOfContainer"] += row["numberofcontainer"]

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
