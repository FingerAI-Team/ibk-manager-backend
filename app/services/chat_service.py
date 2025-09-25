from sqlalchemy.orm import Session
from sqlalchemy import func, and_, cast, Date, or_, exists, select, literal, case, Integer
from datetime import datetime, timedelta
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

            # 질문만 먼저 조회 (페이지네이션 적용)
            questions_query = self.db.query(
                ConvLog.conv_id.label('id'),
                ConvLog.date.label('timestamp'),
                ConvLog.user_id.label('userId'),
                ConvLog.content.label('content'),
                ConvLog.qa.label('qa'),
                ConvLog.hash_value.label('hashValue'),
                ConvLog.hash_ref.label('hashRef')
            ).filter(
                and_(
                    cast(ConvLog.date, Date) >= start.date(),
                    cast(ConvLog.date, Date) <= end.date(),
                    ConvLog.qa == 'Q'
                )
            ).order_by(ConvLog.date.desc())
            
            # 필터링 적용
            if user_id:
                questions_query = questions_query.filter(ConvLog.user_id.ilike(f"%{user_id}%"))
            if keyword:
                questions_query = questions_query.filter(ConvLog.content.ilike(f"%{keyword}%"))
            
            # 전체 질문 수 조회
            total_questions = questions_query.count()
            
            # 페이지네이션 적용
            questions = questions_query.offset(page * page_size).limit(page_size).all()
            
            # 해당 질문들의 답변만 조회
            question_ids = [q.id for q in questions]
            question_hash_values = [q.hashValue for q in questions if q.hashValue]
            
            # 답변 조회 (hash_ref 기반)
            answers = []
            if question_hash_values:
                answers = self.db.query(
                    ConvLog.conv_id.label('id'),
                    ConvLog.date.label('timestamp'),
                    ConvLog.user_id.label('userId'),
                    ConvLog.content.label('content'),
                    ConvLog.qa.label('qa'),
                    ConvLog.hash_value.label('hashValue'),
                    ConvLog.hash_ref.label('hashRef')
                ).filter(
                    and_(
                        cast(ConvLog.date, Date) >= start.date(),
                        cast(ConvLog.date, Date) <= end.date(),
                        ConvLog.qa == 'A',
                        ConvLog.hash_ref.in_(question_hash_values)
                    )
                ).all()

            # Q&A 매핑 (메모리에서 처리)
            qa_mapping = self._create_qa_mapping(questions, answers)
            
            # 질문에 답변 매핑
            questions_with_answers = []
            for q in questions:
                answer_content = qa_mapping.get(q.id)
                questions_with_answers.append({
                    'question': q,
                    'answer': answer_content
                })

            # 종목 여부 필터링
            if is_stock != "all":
                questions_with_answers = [item for item in questions_with_answers 
                                        if self._check_is_stock(item['question'].id) == (is_stock == "stock")]
            
            # 전체 데이터 수 (필터링 후)
            total = len(questions_with_answers)

            # 결과 포맷팅
            result = {
                "items": [
                    {
                        "id": item['question'].id,
                        "timestamp": item['question'].timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "userId": item['question'].userId,
                        "question": item['question'].content,
                        "answer": item['answer'],
                        "isStock": self._check_is_stock(item['question'].id)
                    }
                    for item in questions_with_answers
                ],
                "total": total
            }
            return result
            
        except ValueError as e:
            raise e
        except Exception as e:
            print(f"Error in get_chats: {str(e)}")
            raise Exception("Failed to fetch chat data")

    def _create_qa_mapping(self, questions: List, answers: List) -> Dict[str, str]:
        """Q&A 매핑을 메모리에서 처리"""
        qa_mapping = {}
        
        # 답변을 hash_ref로 인덱싱
        answer_by_hash_ref = {}
        for answer in answers:
            if answer.hashRef:
                answer_by_hash_ref[answer.hashRef] = answer.content
        
        # 질문의 hash_value로 답변 찾기
        for question in questions:
            if question.hashValue and question.hashValue in answer_by_hash_ref:
                qa_mapping[question.id] = answer_by_hash_ref[question.hashValue]
            else:
                # 2025-09-17 이전 데이터: conv_id 기반 매칭
                qa_mapping[question.id] = self._find_answer_by_conv_id(question, answers)
        
        return qa_mapping

    def _find_answer_by_conv_id(self, question, answers: List) -> Optional[str]:
        """conv_id 기반으로 답변 찾기 (2025-09-17 이전 데이터용)"""
        try:
            # 1단계: conv_id - 1 방식
            parts = question.id.split('_')
            if len(parts) == 2:
                date_part = parts[0]
                num_part = int(parts[1])
                answer_conv_id = f"{date_part}_{num_part - 1:05d}"
                
                for answer in answers:
                    if (answer.id == answer_conv_id and 
                        answer.userId == question.userId):
                        return answer.content
            
            # 2단계: 같은 사용자의 질문 이후 가장 가까운 답변 찾기
            question_date = question.timestamp
            next_day = question_date + timedelta(days=1)
            
            for answer in answers:
                if (answer.userId == question.userId and
                    answer.timestamp > question_date and
                    answer.timestamp <= next_day):
                    return answer.content
                    
        except Exception as e:
            print(f"Error finding answer for {question.id}: {e}")
        
        return None


    def _check_is_stock(self, conv_id: str) -> bool:
        """종목 관련 여부 확인"""
        try:
            stock_exists = self.db.query(StockCls).filter(
                and_(
                    StockCls.conv_id == conv_id,
                    StockCls.ensemble == 'o'
                )
            ).first()
            return stock_exists is not None
        except:
            return False
