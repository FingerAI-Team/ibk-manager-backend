from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, Literal
from app.core.database import get_db
from app.services.chat_analytics_service import ChatAnalyticsService

router = APIRouter(prefix="/api/chat-analytics")

@router.get("/daily")
async def get_daily_stats(
    startDate: str = Query(..., description="시작일 (YYYY-MM-DD)"),
    endDate: str = Query(..., description="종료일 (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    try:
        service = ChatAnalyticsService(db)
        return service.get_daily_stats(startDate, endDate)
    except ValueError as e:
        return {"success": False, "error": str(e)}

@router.get("/hourly")
async def get_hourly_stats(
    dateType: Literal['today', 'yesterday', 'thisWeek', 'thisMonth', 'custom'],
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        service = ChatAnalyticsService(db)
        return service.get_hourly_stats(dateType, startDate, endDate)
    except ValueError as e:
        return {"success": False, "error": str(e)}

@router.get("/weekday")
async def get_weekday_stats(
    year: int = Query(..., ge=2000, le=2100, description="연도 (YYYY)"),
    month: int = Query(..., ge=1, le=12, description="월 (1-12)"),
    db: Session = Depends(get_db)
):
    try:
        service = ChatAnalyticsService(db)
        return service.get_weekday_stats(year, month)
    except ValueError as e:
        return {"success": False, "error": str(e)}

@router.get("/ranking")
async def get_user_ranking(
    period: str = Query(..., description="조회 기간 (daily/weekly/monthly/custom)"),
    limit: int = Query(10, ge=5, le=50, description="조회할 사용자 수"),
    sortOrder: str = Query('desc', description="정렬 순서 (asc/desc)"),
    startDate: Optional[str] = Query(None, description="시작일 (YYYY-MM-DD)"),
    endDate: Optional[str] = Query(None, description="종료일 (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    try:
        # 파라미터 검증
        if period not in ['daily', 'weekly', 'monthly', 'custom']:
            raise ValueError("Invalid period. Must be one of: daily, weekly, monthly, custom")
        
        if sortOrder not in ['asc', 'desc']:
            raise ValueError("Invalid sortOrder. Must be either 'asc' or 'desc'")

        if period == 'custom' and (not startDate or not endDate):
            raise ValueError("startDate and endDate are required for custom period")

        service = ChatAnalyticsService(db)
        return service.get_user_ranking(period, limit, sortOrder, startDate, endDate)
    except ValueError as e:
        return {"success": False, "error": str(e)} 