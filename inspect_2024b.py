import fitz, sys, re
sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r'C:\Users\jb733\OneDrive\바탕 화면\quiz\quiz_random\정보처리산업기사 필기 기출문제 (1)\1. 2024년1회_정보처리산업기사필기 기출문제.pdf'
doc = fitz.open(pdf_path)
full = ''.join(doc[i].get_text() for i in range(doc.page_count))

# 정답 패턴 찾기
print('=== 정답 패턴 검색 ===')
for pattern in [r'정답', r'\d+\.[①②③④]', r'\d+\s+[①②③④]', r'정\s*답']:
    matches = list(re.finditer(pattern, full))
    print(f'"{pattern}": {len(matches)}개')
    for m in matches[:3]:
        print(f'  ...{full[max(0,m.start()-10):m.end()+30]}...')

print()
print('=== 5~6 페이지 텍스트 ===')
for pn in [4, 5]:
    print(f'--- 페이지 {pn+1} ---')
    print(doc[pn].get_text()[:800])
    print()
