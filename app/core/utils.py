from datetime import datetime, timedelta
from typing import Dict, Optional

class DateUtils:
    @staticmethod
    def get_date_range(
        date_type: str, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> Dict[datetime, datetime]:
        today = datetime.now().date()
        
        if date_type == 'today':
            return {'start': today, 'end': today}
        
        elif date_type == 'yesterday':
            yesterday = today - timedelta(days=1)
            return {'start': yesterday, 'end': yesterday}
        
        elif date_type == 'thisWeek':
            start = today - timedelta(days=today.weekday())
            return {'start': start, 'end': today}
        
        elif date_type == 'thisMonth':
            start = today.replace(day=1)
            return {'start': start, 'end': today}
        
        elif date_type == 'custom':
            if not start_date or not end_date:
                raise ValueError("Start date and end date are required for custom range")
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            if end < start:
                raise ValueError("End date must be greater than or equal to start date")
            return {'start': start, 'end': end}
        
        raise ValueError("Invalid date type")

    @staticmethod
    def get_period_range(period: str) -> Dict[datetime, datetime]:
        today = datetime.now().date()
        
        if period == 'daily':
            return {'start': today, 'end': today}
        
        elif period == 'weekly':
            start = today - timedelta(days=7)
            return {'start': start, 'end': today}
        
        elif period == 'monthly':
            start = today.replace(day=1)
            return {'start': start, 'end': today}
        
        raise ValueError("Invalid period") 