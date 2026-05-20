import fitz, sys, re
sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r'C:\Users\jb733\OneDrive\바탕 화면\quiz\quiz_random\22년_정보처리산업기사_필기_기출문제\2022년1회_산업기사 필기 기출문제.pdf'
doc = fitz.open(pdf_path)

print(f'전체 페이지수: {doc.page_count}')
print()

# 전체 텍스트에서 정답 부분 찾기
full = ''.join(doc[i].get_text() for i in range(doc.page_count))

# 정답 섹션 찾기
ans_idx = full.find('정답')
if ans_idx >= 0:
    print('=== 정답 섹션 ===')
    print(full[ans_idx:ans_idx+500])
print()

# 마지막 페이지
last = doc[doc.page_count-1]
print(f'=== 마지막 페이지 텍스트 ===')
print(last.get_text()[:2000])
