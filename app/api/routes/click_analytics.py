from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.services.click_analytics_service import ClickAnalyticsService

router = APIRouter(prefix="/api/click-analytics")

@router.get("/user-ranking")
async def get_user_click_ranking(
    startDate: str = Query(..., description="시작일 (YYYY-MM-DD)"),
    endDate: str = Query(..., description="종료일 (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    try:
        service = ClickAnalyticsService(db)
        return service.get_user_click_ranking(startDate, endDate)
    except ValueError as e:
        return {"success": False, "error": str(e)}

@router.get("/ratio")
async def get_click_ratio(
    startDate: str = Query(..., description="시작일 (YYYY-MM-DD)"),
    endDate: str = Query(..., description="종료일 (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    try:
        service = ClickAnalyticsService(db)
        return service.get_click_ratio(startDate, endDate)
    except ValueError as e:
        return {"success": False, "error": str(e)} 