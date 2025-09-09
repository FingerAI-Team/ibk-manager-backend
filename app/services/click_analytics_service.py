from sqlalchemy.orm import Session
from sqlalchemy import func, and_, cast, Date, distinct
from datetime import datetime
from typing import Dict, Any
from app.models.conversation import ConvLog, ClickedLog

class ClickAnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_click_ranking(self, start_date: str, end_date: str) -> Dict[str, Any]:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

            # 사용자별 클릭수와 대화수를 함께 조회
            results = self.db.query(
                ConvLog.user_id.label('user_id'),
                func.count(func.distinct(
                    ClickedLog.conv_id
                )).filter(ClickedLog.clicked == 'o').label('clicks'),
                func.count(func.distinct(
                    ConvLog.conv_id
                )).filter(ConvLog.qa == 'Q').label('chats')
            ).outerjoin(
                ClickedLog,
                ConvLog.conv_id == ClickedLog.conv_id
            ).filter(
                and_(
                    cast(ConvLog.date, Date) >= start.date(),
                    cast(ConvLog.date, Date) <= end.date()
                )
            ).group_by(
                ConvLog.user_id
            ).order_by(
                func.count(func.distinct(ClickedLog.conv_id)).desc()
            ).all()

            data = [
                {
                    "userId": result.user_id,
                    "userName": result.user_id.split('@')[0] if '@' in result.user_id else result.user_id,
                    "clicks": result.clicks,
                    "chats": result.chats
                }
                for result in results
            ]

            return {"success": True, "data": {"data": data}}

        except Exception as e:
            print(f"Error in get_user_click_ranking: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_click_ratio(self, start_date: str, end_date: str) -> Dict[str, Any]:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

            # 클릭한 대화와 사용자 수
            clicked_stats = self.db.query(
                func.count(func.distinct(ConvLog.conv_id)).filter(
                    ClickedLog.clicked == 'o'
                ).label('clicked_chats'),
                func.count(func.distinct(ConvLog.user_id)).filter(
                    ClickedLog.clicked == 'o'
                ).label('clicked_users')
            ).select_from(ConvLog).join(
                ClickedLog,
                ConvLog.conv_id == ClickedLog.conv_id,
                isouter=True
            ).filter(
                and_(
                    cast(ConvLog.date, Date) >= start.date(),
                    cast(ConvLog.date, Date) <= end.date()
                )
            ).first()

            # 전체 대화와 사용자 수
            total_stats = self.db.query(
                func.count(func.distinct(ConvLog.conv_id)).filter(
                    ConvLog.qa == 'Q'
                ).label('total_chats'),
                func.count(func.distinct(ConvLog.user_id)).label('total_users')
            ).filter(
                and_(
                    cast(ConvLog.date, Date) >= start.date(),
                    cast(ConvLog.date, Date) <= end.date()
                )
            ).first()

            # 클릭하지 않은 수 계산
            clicked_chats = clicked_stats.clicked_chats if clicked_stats.clicked_chats is not None else 0
            clicked_users = clicked_stats.clicked_users if clicked_stats.clicked_users is not None else 0
            total_chats = total_stats.total_chats if total_stats.total_chats is not None else 0
            total_users = total_stats.total_users if total_stats.total_users is not None else 0

            not_clicked_chats = total_chats - clicked_chats
            not_clicked_users = total_users - clicked_users

            data = {
                "clicked": {
                    "users": clicked_users,
                    "chats": clicked_chats
                },
                "notClicked": {
                    "users": not_clicked_users,
                    "chats": not_clicked_chats
                }
            }

            return {"success": True, "data": {"data": data}}

        except Exception as e:
            print(f"Error in get_click_ratio: {str(e)}")
            return {"success": False, "error": str(e)} 