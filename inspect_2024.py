import fitz, sys, re
sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r'C:\Users\jb733\OneDrive\바탕 화면\quiz\quiz_random\정보처리산업기사 필기 기출문제 (1)\1. 2024년1회_정보처리산업기사필기 기출문제.pdf'
doc = fitz.open(pdf_path)
print(f'페이지 수: {doc.page_count}')
last = doc[doc.page_count-1].get_text()
print('=== 마지막 페이지 ===')
print(last[:2000])
