from sqlalchemy.orm import Session
from sqlalchemy import func, and_, cast, Date, extract, desc, asc, distinct
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from app.models.conversation import ConvLog
from app.core.utils import DateUtils  # 날짜 관련 유틸리티 함수들을 모아둔 모듈

class ChatAnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_daily_stats(self, start_date: str, end_date: str) -> Dict[str, Any]:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

            if end < start:
                raise ValueError("End date must be greater than or equal to start date")

            results = self.db.query(
                cast(ConvLog.date, Date).label('date'),
                func.count(func.distinct(ConvLog.conv_id)).filter(ConvLog.qa == 'Q').label('chats'),
                func.count(func.distinct(ConvLog.user_id)).label('users')
            ).filter(
                and_(
                    cast(ConvLog.date, Date) >= start.date(),
                    cast(ConvLog.date, Date) <= end.date()
                )
            ).group_by(
                cast(ConvLog.date, Date)
            ).order_by(
                cast(ConvLog.date, Date)
            ).all()

            data = [
                {
                    "date": result.date.strftime("%Y-%m-%d"),
                    "chats": result.chats,
                    "users": result.users
                }
                for result in results
            ]

            return {"success": True, "data": {"data": data}}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_hourly_stats(
        self, 
        date_type: str, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            # 날짜 범위 계산
            date_range = DateUtils.get_date_range(date_type, start_date, end_date)
            if not date_range:
                raise ValueError("Invalid date range")

            # 시간별 통계 쿼리
            results = self.db.query(
                extract('hour', ConvLog.date).label('hour'),
                func.count(func.distinct(ConvLog.conv_id)).filter(ConvLog.qa == 'Q').label('chats')
            ).filter(
                and_(
                    cast(ConvLog.date, Date) >= date_range['start'],
                    cast(ConvLog.date, Date) <= date_range['end']
                )
            ).group_by(
                extract('hour', ConvLog.date)
            ).order_by(
                extract('hour', ConvLog.date)
            ).all()

            # 0-23시까지 모든 시간대에 대한 데이터 준비
            hourly_data = {str(hour).zfill(2): 0 for hour in range(24)}
            
            # 실제 데이터로 업데이트
            for result in results:
                hour = str(int(result.hour)).zfill(2)  # 시간을 2자리 문자열로 변환
                hourly_data[hour] = result.chats

            # 시간 순서대로 데이터 포맷팅
            data = [
                {
                    "hour": hour,
                    "chats": count
                }
                for hour, count in hourly_data.items()
            ]

            return {"success": True, "data": {"data": data}}

        except Exception as e:
            print(f"Error in get_hourly_stats: {str(e)}")  # 디버깅용 로그
            return {"success": False, "error": str(e)}

    def get_weekday_stats(self, year: int, month: int) -> Dict[str, Any]:
        try:
            # 디버깅을 위한 날짜-요일 매핑 확인
            debug_query = self.db.query(
                ConvLog.date,
                extract('isodow', ConvLog.date).label('weekday')
            ).filter(
                and_(
                    extract('year', ConvLog.date) == year,
                    extract('month', ConvLog.date) == month
                )
            ).order_by(ConvLog.date).limit(10)
            
            debug_results = debug_query.all()
            print(f"=== Debug Date-Weekday Mapping for {year}-{month:02d} ===")
            for result in debug_results:
                print(f"Date: {result.date}, Weekday: {result.weekday}")
            print("=================================")

            # 요일별 통계 쿼리
            results = self.db.query(
                extract('isodow', ConvLog.date).label('weekday'),
                func.count(func.distinct(ConvLog.conv_id)).filter(ConvLog.qa == 'Q').label('chats'),
                func.count(func.distinct(ConvLog.user_id)).label('users')
            ).filter(
                and_(
                    extract('year', ConvLog.date) == year,
                    extract('month', ConvLog.date) == month
                )
            ).group_by(
                extract('isodow', ConvLog.date)
            ).order_by(
                extract('isodow', ConvLog.date)
            ).all()

            weekdays = ['월', '화', '수', '목', '금', '토', '일']
            weekday_data = {day: {'chats': 0, 'users': 0} for day in weekdays}
            
            for result in results:
                weekday_idx = int(result.weekday) - 1
                weekday = weekdays[weekday_idx]
                weekday_data[weekday] = {
                    'chats': result.chats,
                    'users': result.users
                }

            data = [
                {
                    "day": day,
                    "chats": weekday_data[day]['chats'],
                    "users": weekday_data[day]['users']
                }
                for day in weekdays
            ]

            return {"success": True, "data": {"data": data}}

        except Exception as e:
            print(f"Error in get_weekday_stats: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_user_ranking(
        self, 
        period: str,
        limit: int,
        sort_order: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            # 기간 설정
            if period == 'custom':
                if not start_date or not end_date:
                    raise ValueError("Start date and end date are required for custom period")
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")
            else:
                today = datetime.now()
                if period == 'daily':
                    start = today.replace(hour=0, minute=0, second=0, microsecond=0)
                    end = today
                elif period == 'weekly':
                    start = today - timedelta(days=7)
                    end = today
                elif period == 'monthly':
                    start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    end = today
                else:
                    raise ValueError("Invalid period")

            # 사용자별 대화 수 쿼리
            results = self.db.query(
                ConvLog.user_id.label('user_id'),
                func.count(func.distinct(ConvLog.conv_id)).filter(ConvLog.qa == 'Q').label('chat_count')
            ).filter(
                and_(
                    cast(ConvLog.date, Date) >= start.date(),
                    cast(ConvLog.date, Date) <= end.date()
                )
            ).group_by(
                ConvLog.user_id
            ).order_by(
                desc('chat_count') if sort_order == 'desc' else asc('chat_count')
            ).limit(limit).all()

            # 결과 포맷팅
            data = [
                {
                    "userId": result.user_id,
                    "userName": result.user_id.split('@')[0] if '@' in result.user_id else result.user_id,  # 이메일에서 아이디 부분만 추출
                    "chats": result.chat_count
                }
                for result in results
            ]

            return {"success": True, "data": {"data": data}}

        except Exception as e:
            print(f"Error in get_user_ranking: {str(e)}")  # 디버깅용 로그
            return {"success": False, "error": str(e)} 