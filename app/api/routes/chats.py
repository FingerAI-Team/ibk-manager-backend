from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Literal
from app.core.database import get_db
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api")

@router.get("/chats")
async def get_chats(
    startDate: str = Query(..., description="조회 시작일 (YYYY-MM-DD)"),
    endDate: str = Query(..., description="조회 종료일 (YYYY-MM-DD)"),
    isStock: Optional[Literal["stock", "non-stock", "all"]] = Query("all", description="종목 여부 필터"),
    userId: Optional[str] = Query(None, description="사용자 ID 검색"),
    keyword: Optional[str] = Query(None, description="질문 내용 키워드 검색"),
    page: int = Query(0, ge=0, description="페이지 번호 (0부터 시작)"),
    pageSize: int = Query(10, ge=1, le=100, description="페이지당 항목 수"),
    db: Session = Depends(get_db)
):
    try:
        service = ChatService(db)
        return service.get_chats(
            start_date=startDate,
            end_date=endDate,
            is_stock=isStock,
            user_id=userId,
            keyword=keyword,
            page=page,
            page_size=pageSize
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") 