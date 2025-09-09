from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import home, chat_analytics, click_analytics, chats
import logging

# SQLAlchemy 로깅 설정
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

app = FastAPI()

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://ibkai.fingerservice.co.kr"
                   ],  # React 앱의 주소
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 HTTP 헤더 허용
)

app.include_router(home.router)
app.include_router(chat_analytics.router)
app.include_router(click_analytics.router)
app.include_router(chats.router)

# 서버 설정을 config.py로 이동
PORT = 3001

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True) 