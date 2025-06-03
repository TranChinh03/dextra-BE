from datetime import datetime

from databases import Database
from sqlalchemy import (JSON, Boolean, Column, DateTime, Float, Integer,
                        MetaData, String, Table, create_engine)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = 'postgresql://neondb_owner:npg_mHXqxOQ6SR5y@ep-falling-smoke-a1ps92xb-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'

engine = create_engine(DATABASE_URL)
metadata = MetaData()

detection_results = Table(
    'results_table',
    metadata,
    Column('detectionId', String, primary_key=True),
    Column('cameraId', String, nullable=False),
    Column('date', String, nullable=False, default=datetime.utcnow().strftime('%Y-%m-%d')),
    Column('time', String, nullable=False, default=datetime.utcnow().strftime('%H:%M:%S')),
    Column('numberOfBicycle', Integer, default=0),
    Column('numberOfMotorcycle', Integer, default=0),
    Column('numberOfCar', Integer, default=0),
    Column('numberOfVan', Integer, default=0),
    Column('numberOfTruck', Integer, default=0),
    Column('numberOfBus', Integer, default=0),
    Column('numberOfFireTruck', Integer, default=0),
    Column('numberOfContainer', Integer, default=0),
)

database = Database(DATABASE_URL)

# Khởi tạo engine và sessionmaker
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency để lấy session
async def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
async def get_db():
    return database