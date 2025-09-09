#!/usr/bin/env python3
"""
PostgreSQL 데이터베이스 직접 확인 스크립트
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# 데이터베이스 연결 정보
DB_CONFIG = {
    'host': 'postgres_postgresql-master_1',
    'database': 'ibk_db',
    'user': 'ibk-manager',
    'password': 'fingerai2024!',
    'port': 5432
}

def check_database():
    try:
        # 데이터베이스 연결
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("=== PostgreSQL 데이터베이스 연결 성공 ===")
        
        # 1. 테이블 목록 확인
        print("\n1. 테이블 목록:")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        for table in tables:
            print(f"  - {table['table_name']}")
        
        # 2. ConvLog 테이블 샘플 데이터
        print("\n2. ConvLog 테이블 샘플 데이터 (최근 5개):")
        cursor.execute("""
            SELECT conv_id, date, qa, user_id, LEFT(content, 50) as content_preview
            FROM ibk_convlog 
            ORDER BY date DESC 
            LIMIT 5
        """)
        conv_logs = cursor.fetchall()
        for log in conv_logs:
            print(f"  {log['conv_id']} | {log['date']} | {log['qa']} | {log['user_id'][:20]}... | {log['content_preview']}")
        
        # 3. StockCls 테이블 샘플 데이터
        print("\n3. StockCls 테이블 샘플 데이터 (최근 5개):")
        cursor.execute("""
            SELECT conv_id, ensemble, gpt_res, enc_res
            FROM ibk_stock_cls 
            ORDER BY conv_id DESC
            LIMIT 5
        """)
        stock_cls = cursor.fetchall()
        for stock in stock_cls:
            print(f"  {stock['conv_id']} | {stock['ensemble']} | {stock['gpt_res']} | {stock['enc_res']}")
        
        # 4. 질문-답변-종목 연결 테스트
        print("\n4. 질문-답변-종목 연결 테스트 (최근 3개):")
        cursor.execute("""
            SELECT 
                q.conv_id as question_id,
                q.date as question_date,
                q.user_id,
                LEFT(q.content, 30) as question,
                LEFT(a.content, 30) as answer,
                s.ensemble as is_stock
            FROM ibk_convlog q
            LEFT JOIN ibk_convlog a ON (
                q.user_id = a.user_id AND 
                a.date > q.date AND 
                a.qa = 'A'
            )
            LEFT JOIN ibk_stock_cls s ON q.conv_id = s.conv_id
            WHERE q.qa = 'Q'
            ORDER BY q.date DESC
            LIMIT 3
        """)
        connections = cursor.fetchall()
        for conn_data in connections:
            print(f"  Q: {conn_data['question_id']} | {conn_data['question']}")
            print(f"  A: {conn_data['answer']}")
            print(f"  Stock: {conn_data['is_stock']}")
            print("  ---")
        
        # 5. ensemble 값 분포
        print("\n5. StockCls ensemble 값 분포:")
        cursor.execute("""
            SELECT ensemble, COUNT(*) as count
            FROM ibk_stock_cls 
            GROUP BY ensemble
        """)
        ensemble_dist = cursor.fetchall()
        for dist in ensemble_dist:
            print(f"  {dist['ensemble']}: {dist['count']}개")
        
        # 6. 실제 API 쿼리 테스트
        print("\n6. 실제 API 쿼리 테스트:")
        cursor.execute("""
            SELECT 
                q.conv_id as id,
                q.date as timestamp,
                q.user_id as userId,
                q.content as question,
                MIN(a.content) as answer,
                CASE 
                    WHEN EXISTS(
                        SELECT 1 FROM ibk_stock_cls s 
                        WHERE s.conv_id = q.conv_id AND s.ensemble = 'o'
                    ) THEN true 
                    ELSE false 
                END as isStock
            FROM ibk_convlog q
            LEFT JOIN ibk_convlog a ON (
                q.user_id = a.user_id AND 
                a.date > q.date AND 
                a.qa = 'A'
            )
            WHERE q.qa = 'Q'
            AND q.date >= '2024-01-01'
            GROUP BY q.conv_id, q.date, q.user_id, q.content
            ORDER BY q.date DESC
            LIMIT 3
        """)
        api_test = cursor.fetchall()
        for test in api_test:
            print(f"  ID: {test['id']}")
            print(f"  Question: {test['question'][:50]}...")
            print(f"  Answer: {test['answer'][:50] if test['answer'] else 'None'}...")
            print(f"  isStock: {test['isstock']}")
            print("  ---")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    check_database()
