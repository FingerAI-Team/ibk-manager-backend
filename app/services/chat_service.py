from sqlalchemy.orm import Session
from sqlalchemy import func, and_, cast, Date, or_, exists, select, literal, case
from datetime import datetime
from typing import Optional, Dict, Any, List
from app.models.conversation import ConvLog, StockCls

class ChatService:
    def __init__(self, db: Session):
        self.db = db

    def get_chats(
        self,
        start_date: str,
        end_date: str,
        is_stock: str = "all",
        user_id: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 0,
        page_size: int = 10
    ) -> Dict[str, Any]:
        try:
            # 날짜 검증
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if end < start:
                raise ValueError("End date must be greater than or equal to start date")

            # 기본 쿼리 구성
            base_query = self.db.query(
                ConvLog.conv_id.label('id'),
                ConvLog.date.label('timestamp'),
                ConvLog.user_id.label('userId'),
                ConvLog.content.label('question')
            ).filter(
                and_(
                    cast(ConvLog.date, Date) >= start.date(),
                    cast(ConvLog.date, Date) <= end.date(),
                    ConvLog.qa == 'Q'  # 질문만 조회
                )
            )

            # 종목 여부에 따른 쿼리 분기
            if is_stock == "stock":
                query = base_query.add_columns(
                    literal(True).label('isStock')
                ).filter(exists().where(
                    and_(
                        StockCls.conv_id == ConvLog.conv_id,
                        StockCls.ensemble == 'o'
                    )
                ))
            elif is_stock == "non-stock":
                query = base_query.add_columns(
                    literal(False).label('isStock')
                ).filter(exists().where(
                    and_(
                        StockCls.conv_id == ConvLog.conv_id,
                        StockCls.ensemble == 'x'
                    )
                ))
            else:  # is_stock 파라미터가 없는 경우
                stock_exists = exists(
                    select(StockCls.conv_id).where(
                        and_(
                            StockCls.conv_id == ConvLog.conv_id,
                            StockCls.ensemble == 'o'
                        )
                    )
                )
                query = base_query.add_columns(
                    case(
                        (stock_exists, True),
                        else_=False
                    ).label('isStock')
                )

            # 사용자 ID 검색
            if user_id:
                query = query.filter(ConvLog.user_id.ilike(f"%{user_id}%"))

            # 키워드 검색
            if keyword:
                query = query.filter(ConvLog.content.ilike(f"%{keyword}%"))

            # 전체 데이터 수 조회
            total = query.count()

            # 페이지네이션 적용
            items = query.order_by(
                ConvLog.date.desc()
            ).offset(
                page * page_size
            ).limit(page_size).all()

            # 결과 포맷팅
            result = {
                "items": [
                    {
                        "id": item.id,
                        "timestamp": item.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "userId": item.userId,
                        "question": item.question,
                        "isStock": bool(item.isStock)
                    }
                    for item in items
                ],
                "total": total
            }

            return result

        except ValueError as e:
            raise e
        except Exception as e:
            print(f"Error in get_chats: {str(e)}")
            raise Exception("Failed to fetch chat data") 