# Vehicle Detection Service

This is a FastAPI-based microservice for vehicle detection, following the same structure and organization as the camera-service. It includes API routing, models, db_manager, and database setup.

## Features
- Vehicle detection API endpoints
- Database integration
- Modular code structure

## Getting Started

1. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```
2. **Run the service:**
   ```powershell
   uvicorn app.main:app --reload
   ```

## Project Structure
- `app/api/` - API routes
- `app/api/models.py` - Pydantic models
- `app/api/db_manager.py` - Database manager logic
- `app/api/db.py` - Database connection setup
- `app/main.py` - FastAPI app entry point

## Notes
- Update the database connection settings in `app/api/db.py` as needed.
- This project is scaffolded to match the camera-service for easy integration.
