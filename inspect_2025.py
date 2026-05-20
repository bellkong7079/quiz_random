import fitz, sys, re
sys.stdout.reconfigure(encoding='utf-8')

for pdf_path in [
    r'C:\Users\jb733\OneDrive\바탕 화면\quiz\quiz_random\2025년 정보처리산업기사 기출문제\2025년1회_정보처리산업기사필기 기출문제.pdf',
]:
    doc = fitz.open(pdf_path)
    full = ''.join(doc[i].get_text() for i in range(doc.page_count))

    # 정답 패턴 종류 찾기
    print(f'=== {pdf_path[-40:]} ===')
    for m in re.finditer(r'정답', full):
        print(f'  정답 at {m.start()}: ...{full[m.start()-5:m.start()+60]}...')

    # 문제 본문 첫 부분
    print()
    print('첫 500자:')
    print(full[:500])
    print()
