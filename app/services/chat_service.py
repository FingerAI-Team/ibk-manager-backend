from sqlalchemy.orm import Session
from sqlalchemy import func, and_, cast, Date, or_, exists, select, literal, case, Integer
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

            # 기본 쿼리 구성 (질문만 조회)
            base_query = self.db.query(
                ConvLog.conv_id.label('id'),
                ConvLog.date.label('timestamp'),
                ConvLog.user_id.label('userId'),
                ConvLog.content.label('question'),
                ConvLog.hash_value.label('hashValue')
            ).filter(
                and_(
                    cast(ConvLog.date, Date) >= start.date(),
                    cast(ConvLog.date, Date) <= end.date(),
                    ConvLog.qa == 'Q'  # 질문만 조회
                )
            )

            # 종목 여부에 따른 쿼리 분기 (enc_res 컬럼 기준)
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
            else:  # is_stock 파라미터가 "all"인 경우
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

            # 답변을 Python에서 찾기 (새로운 hash 기반 + 기존 방식)
            def get_answer_for_question(question_conv_id, user_id, question_date, question_hash_value):
                """질문에 대한 답변을 찾는 로직 (hash 기반 + 기존 방식)"""
                try:
                    # 2025-09-17 이후 데이터: hash 기반 매칭
                    if question_hash_value:
                        answer = self.db.query(ConvLog.content).filter(
                            and_(
                                ConvLog.hash_ref == question_hash_value,
                                ConvLog.qa == 'A',
                                ConvLog.user_id == user_id
                            )
                        ).first()
                        if answer:
                            return answer.content
                    
                    # 2025-09-17 이전 데이터: 기존 방식 (conv_id 기반)
                    # 1단계: 정확한 매칭 (conv_id - 1, 같은 사용자, qa='A')
                    parts = question_conv_id.split('_')
                    if len(parts) == 2:
                        date_part = parts[0]
                        num_part = int(parts[1])
                        answer_conv_id = f"{date_part}_{num_part - 1:05d}"
                        answer = self.db.query(ConvLog.content).filter(
                            and_(
                                ConvLog.conv_id == answer_conv_id,
                                ConvLog.user_id == user_id,
                                ConvLog.qa == 'A'
                            )
                        ).first()
                        if answer:
                            return answer.content
                    
                    # 2단계: 같은 사용자의 질문 이후 가장 가까운 답변 찾기
                    answer = self.db.query(ConvLog.content).filter(
                        and_(
                            ConvLog.user_id == user_id,
                            ConvLog.qa == 'A',
                            ConvLog.date > question_date
                        )
                    ).order_by(ConvLog.date.asc()).first()
                    if answer:
                        return answer.content
                except Exception as e:
                    print(f"Error finding answer for {question_conv_id}: {e}")
                return None

            # 페이지네이션 정보 계산
            total_pages = (total + page_size - 1) // page_size  # 올림 계산
            has_next = page < total_pages - 1
            has_prev = page > 0
            
            # 결과 포맷팅 (이전 백엔드 형태로 맞춤)
            result = {
                "success": True,
                "data": {
                    "items": [
                        {
                            "id": item.id,
                            "timestamp": item.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                            "userId": item.userId,
                            "question": item.question,
                            "answer": get_answer_for_question(item.id, item.userId, item.timestamp, item.hashValue),
                            "isStock": bool(item.isStock)
                        }
                        for item in items
                    ],
                    "total": total,
                    "page": page,
                    "pageSize": page_size,
                    "totalPages": total_pages
                }
            }
            return result
        except ValueError as e:
            raise e
        except Exception as e:
            print(f"Error in get_chats: {str(e)}")
            raise Exception("Failed to fetch chat data") 