import json, sys
sys.stdout.reconfigure(encoding='utf-8')

path = r'C:\Users\jb733\OneDrive\바탕 화면\quiz\quiz_random\sanup_questions.json'
qs = json.load(open(path, encoding='utf-8'))
print(f'원본: {len(qs)}문제', file=sys.stderr)

def is_valid(q):
    choices = q.get('choices', [])
    valid = sum(1 for c in choices if len(c.strip()) >= 2)
    return valid >= 4

filtered = [q for q in qs if is_valid(q)]
print(f'필터 후: {len(filtered)}문제 (제거: {len(qs)-len(filtered)}개)', file=sys.stderr)

with open(path, 'w', encoding='utf-8') as f:
    json.dump(filtered, f, ensure_ascii=False, indent=2)
print(f'저장 완료: {path}', file=sys.stderr)

# source별 통계
sources = {}
for q in filtered:
    s = q.get('source','?')[:40]
    sources[s] = sources.get(s, 0) + 1
for k, v in sorted(sources.items()):
    print(f'  {k}: {v}개')

no_ans = sum(1 for q in filtered if q.get('answer', -1) == -1)
print(f'\n정답 없는 문제: {no_ans}개')
