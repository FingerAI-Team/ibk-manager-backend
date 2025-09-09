from sqlalchemy.orm import Session
from sqlalchemy import func, and_, cast, Date, distinct, text
from datetime import datetime, timedelta
from app.models.conversation import ConvLog, ClickedLog, StockCls

class DailyStatsService:
    def __init__(self, db: Session):
        self.db = db

    def is_business_day(self, date: datetime) -> bool:
        # 주말 체크 (0 = 월요일, 6 = 일요일)
        if date.weekday() >= 5:
            return False
        # 여기에 공휴일 체크 로직을 추가할 수 있습니다
        return True

    def get_previous_business_day(self, date: datetime) -> datetime:
        previous_date = date - timedelta(days=1)
        while not self.is_business_day(previous_date):
            previous_date -= timedelta(days=1)
        return previous_date

    def _get_date_stats(self, date: datetime) -> dict:
        try:
            print(f"\n=== Date: {date.date()} ===")
            
            # 1. 전체 대화 로그 확인
            conv_logs = self.db.query(
                ConvLog.conv_id, 
                ConvLog.qa, 
                ConvLog.date
            ).filter(
                cast(ConvLog.date, Date) == date.date()
            ).all()
            print(f"Total conversations for the day: {len(conv_logs)}")
            print(f"Conversation IDs: {[log.conv_id for log in conv_logs]}")

            # 2. 클릭 로그 확인
            click_logs = self.db.query(
                ClickedLog.conv_id, 
                ClickedLog.clicked
            ).join(
                ConvLog, 
                ClickedLog.conv_id == ConvLog.conv_id
            ).filter(
                cast(ConvLog.date, Date) == date.date(),
                ClickedLog.clicked == 'o'
            ).all()
            print(f"Click logs: {[log.conv_id for log in click_logs]}")
            print(f"Unique clicked conv_ids: {len(set([log.conv_id for log in click_logs]))}")

            # 3. 예측 결과 확인
            stock_logs = self.db.query(
                StockCls.conv_id, 
                StockCls.ensemble
            ).join(
                ConvLog, 
                StockCls.conv_id == ConvLog.conv_id
            ).filter(
                cast(ConvLog.date, Date) == date.date()
            ).all()
            print(f"Stock classification logs: {[(log.conv_id, log.ensemble) for log in stock_logs]}")

            # 기존 통계 계산
            base_stats = self.db.query(
                func.count(distinct(ConvLog.conv_id)).filter(ConvLog.qa == 'Q').label('chat_count'),
                func.count(distinct(ConvLog.user_id)).label('user_count')
            ).filter(
                cast(ConvLog.date, Date) == date.date()
            ).first()

            click_subquery = self.db.query(
                ClickedLog.conv_id
            ).distinct(
                ClickedLog.conv_id
            ).join(
                ConvLog, 
                ClickedLog.conv_id == ConvLog.conv_id
            ).filter(
                cast(ConvLog.date, Date) == date.date(),
                ClickedLog.clicked == 'o'
            ).subquery()

            click_count = self.db.query(
                func.count()
            ).select_from(click_subquery).scalar()

            correct_subquery = self.db.query(
                StockCls.conv_id
            ).distinct(
                StockCls.conv_id
            ).join(
                ConvLog, 
                StockCls.conv_id == ConvLog.conv_id
            ).filter(
                cast(ConvLog.date, Date) == date.date(),
                StockCls.ensemble == 'o'
            ).subquery()

            incorrect_subquery = self.db.query(
                StockCls.conv_id
            ).distinct(
                StockCls.conv_id
            ).join(
                ConvLog, 
                StockCls.conv_id == ConvLog.conv_id
            ).filter(
                cast(ConvLog.date, Date) == date.date(),
                StockCls.ensemble == 'x'
            ).subquery()

            correct_count = self.db.query(func.count()).select_from(correct_subquery).scalar()
            incorrect_count = self.db.query(func.count()).select_from(incorrect_subquery).scalar()

            result = {
                'chat_count': base_stats.chat_count if base_stats else 0,
                'user_count': base_stats.user_count if base_stats else 0,
                'click_count': click_count if click_count is not None else 0,
                'correct_predictions': correct_count if correct_count is not None else 0,
                'incorrect_predictions': incorrect_count if incorrect_count is not None else 0
            }
            print(f"Final results: {result}")
            return result

        except Exception as e:
            print(f"Error in _get_date_stats: {str(e)}")
            return {
                'chat_count': 0,
                'user_count': 0,
                'click_count': 0,
                'correct_predictions': 0,
                'incorrect_predictions': 0
            }

    def get_daily_stats(self, target_date: datetime):
        try:
            # 미래 날짜 체크를 현재 시간과 비교
            if target_date.date() > datetime.now().date():
                return {"success": False, "error": "Future date is not allowed"}
            
            # 영업일 체크 (필요 없어짐)
            # if not self.is_business_day(target_date):
            #     return {"success": False, "error": "Not a business day"}

            # 현재 날짜 통계
            current_stats = self._get_date_stats(target_date)
            
            # 이전 영업일 통계 (영업일 기준 필요 없어짐)
            # prev_date = self.get_previous_business_day(target_date)
            prev_date = target_date - timedelta(days=1)
            prev_stats = self._get_date_stats(prev_date)

            # 증감률 계산
            chat_count_diff = round(((current_stats['chat_count'] - prev_stats['chat_count']) / prev_stats['chat_count'] * 100), 1) if prev_stats['chat_count'] > 0 else 0
            user_count_diff = round(((current_stats['user_count'] - prev_stats['user_count']) / prev_stats['user_count'] * 100), 1) if prev_stats['user_count'] > 0 else 0

            return {
                "success": True,
                "data": {
                    "chatCount": current_stats['chat_count'],
                    "chatCountDiff": chat_count_diff,
                    "userCount": current_stats['user_count'],
                    "userCountDiff": user_count_diff,
                    "clickRatio": {
                        "click": {
                            "count": current_stats['click_count'],
                            "ratio": round(current_stats['click_count'] / current_stats['chat_count'] * 100, 1) if current_stats['chat_count'] > 0 else 0
                        },
                        "nonClick": {
                            "count": current_stats['chat_count'] - current_stats['click_count'],
                            "ratio": round((current_stats['chat_count'] - current_stats['click_count']) / current_stats['chat_count'] * 100, 1) if current_stats['chat_count'] > 0 else 0
                        }
                    },
                    "predictionStats": {
                        "correct": current_stats['correct_predictions'],
                        "incorrect": current_stats['incorrect_predictions'],
                        "accuracy": round(current_stats['correct_predictions'] / (current_stats['correct_predictions'] + current_stats['incorrect_predictions']) * 100, 1) if (current_stats['correct_predictions'] + current_stats['incorrect_predictions']) > 0 else 0
                    }
                }
            }

        except Exception as e:
            return {"success": False, "error": str(e)} 