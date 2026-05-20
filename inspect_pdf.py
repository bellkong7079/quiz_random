import fitz, sys
sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r'C:\Users\jb733\OneDrive\바탕 화면\quiz\quiz_random\22년_정보처리산업기사_필기_기출문제\2022년1회_산업기사 필기 기출문제.pdf'
doc = fitz.open(pdf_path)
page = doc[0]
print(f'페이지 수: {doc.page_count}')
print(f'페이지 크기: {page.rect}')
print()
print('=== 첫 페이지 텍스트 ===')
print(page.get_text()[:2000])
