from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import logging
from app.core.database import get_db
from app.services.daily_stats_service import DailyStatsService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/api/home/daily-stats")
def get_daily_stats(date: str, db: Session = Depends(get_db)):
    try:
        logger.info(f"Received request for date: {date}")
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        service = DailyStatsService(db)
        result = service.get_daily_stats(date_obj)
        logger.info(f"Result: {result}")
        if not result["success"]:
            logger.error(f"Error in get_daily_stats: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except ValueError as e:
        logger.error(f"ValueError in get_daily_stats: {str(e)}")
        return {"success": False, "error": "Invalid date format"}
    except Exception as e:
        logger.error(f"Unexpected error in get_daily_stats: {str(e)}")
        return {"success": False, "error": str(e)} 