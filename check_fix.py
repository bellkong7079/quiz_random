import json, sys
sys.stdout.reconfigure(encoding='utf-8')
qs = json.load(open(r'C:\Users\jb733\OneDrive\바탕 화면\quiz\quiz_random\questions.json', encoding='utf-8'))
print(f'총 {len(qs)}문제')

for q in qs:
    if '화이트박스' in q.get('q', ''):
        img = q.get('image', '')
        print(f'화이트박스 image: {"있음 길이=" + str(len(img)) if img else "없음 (수정됨)"}')
        break

for q in qs:
    if 'total_sum' in q.get('q', '') or 'total_sum' in q.get('code', ''):
        print(f'total_sum q: {q["q"][:60]}')
        print(f'total_sum code: {repr(q.get("code", ""))[:80]}')
        break

# 이미지 있는 문제들
with_img = [q for q in qs if q.get('image')]
print(f'\n이미지 있는 문제: {len(with_img)}개')
for q in with_img:
    print(f'  - {q["q"][:50]} | {q.get("source")}')

# 코드 있는 문제 샘플
with_code = [q for q in qs if q.get('code')]
print(f'\n코드 있는 문제: {len(with_code)}개')
for q in with_code[:5]:
    print(f'  q: {q["q"][:50]}')
    print(f'  code: {repr(q["code"][:60])}')
