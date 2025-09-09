#!/bin/bash

# 가상환경 생성
python3 -m venv linux_venv

# 가상환경 활성화 (Linux/Mac)
if [[ "$OSTYPE" == "linux-gnu"* || "$OSTYPE" == "darwin"* ]]; then
  . linux_venv/bin/activate
# 가상환경 활성화 (Windows)
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  venv\Scripts\activate
fi

# 필요한 패키지 설치
pip install -r requirements.txt

echo "설치가 완료되었습니다. 다음 명령어로 서버를 실행하세요:"
echo "uvicorn app.main:app --port 3005 --reload" 
