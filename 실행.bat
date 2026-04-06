@echo off
chcp 65001 >nul
python -m pip install pymupdf -q
echo 문제 추출 중...
python extract_questions.py
echo 퀴즈 HTML 생성 중...
python make_quiz.py
start quiz_random.html
pause
