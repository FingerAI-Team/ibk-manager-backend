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

            # 전체 Q&A 데이터를 한 번에 조회
            all_data = self.db.query(
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
                    cast(ConvLog.date, Date) <= end.date()
                )
            ).order_by(ConvLog.date.desc()).all()

            # Q와 A를 분리
            questions = [item for item in all_data if item.qa == 'Q']
            answers = [item for item in all_data if item.qa == 'A']
            
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

            # 필터링 적용
            filtered_questions = self._apply_filters(questions_with_answers, is_stock, user_id, keyword)
            
            # 전체 데이터 수
            total = len(filtered_questions)
            
            # 페이지네이션 적용
            start_idx = page * page_size
            end_idx = start_idx + page_size
            paginated_questions = filtered_questions[start_idx:end_idx]

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
                    for item in paginated_questions
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

    def _apply_filters(self, questions_with_answers: List, is_stock: str, user_id: Optional[str], keyword: Optional[str]) -> List:
        """필터링 적용"""
        filtered = questions_with_answers
        
        # 사용자 ID 필터
        if user_id:
            filtered = [item for item in filtered if user_id.lower() in item['question'].userId.lower()]
        
        # 키워드 필터
        if keyword:
            filtered = [item for item in filtered if keyword.lower() in item['question'].content.lower()]
        
        # 종목 여부 필터
        if is_stock != "all":
            filtered = [item for item in filtered if self._check_is_stock(item['question'].id) == (is_stock == "stock")]
        
        return filtered

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
