from app.api.database import get_db, detection_results
from app.api.models import DetectionResults
from databases import Database
from sqlalchemy import insert

class DBManager:
    def __init__(self, session: get_db):
        self.session = session

async def write_detection_result_to_db(db: Database, rs: DetectionResults) -> str:
    stmt = insert(detection_results).values(rs)
    try:
        await db.execute(stmt)
        return "Success: Data written to database."
    except Exception as e:
        # Log or handle the exception as needed
        print(f"Error writing to database: {e}")
        return f"Error: {e}"