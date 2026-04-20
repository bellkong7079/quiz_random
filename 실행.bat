@echo off
chcp 65001 >nul
set PY=C:\Users\jb733\AppData\Local\Python\pythoncore-3.14-64\python.exe
%PY% -m pip install pymupdf -q
echo 문제 추출 중...
%PY% extract_questions.py
echo 퀴즈 HTML 생성 중...
%PY% make_quiz.py
start quiz_random.html
pause
