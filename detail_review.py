import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')

qs = json.load(open(r'C:\Users\jb733\OneDrive\바탕 화면\quiz\quiz_random\sanup_questions.json', encoding='utf-8'))

# 빈 보기 있는 문제
empty_choice = [q for q in qs if any(len(c.strip()) == 0 for c in q.get('choices', []))]
print(f'빈 보기 있는 문제: {len(empty_choice)}개')
for q in empty_choice[:5]:
    print(f'  q: {q["q"][:60]}')
    print(f'  choices: {q["choices"]}')
    print(f'  source: {q.get("source")}')
    print()

# 보기 4개 미만 문제
short = [q for q in qs if len([c for c in q.get('choices',[]) if c.strip()]) < 4]
print(f'\n유효 보기 4개 미만: {len(short)}개')

# 정답 없는 문제
no_ans = [q for q in qs if q.get('answer', -1) == -1]
print(f'\n정답 없는 문제: {len(no_ans)}개')

# source별 이슈 현황
sources = {}
for q in qs:
    s = q.get('source', '?')[:40]
    has_issue = any(len(c.strip()) < 2 for c in q.get('choices', []))
    if s not in sources:
        sources[s] = {'total': 0, 'issues': 0}
    sources[s]['total'] += 1
    if has_issue:
        sources[s]['issues'] += 1

print('\nsource별 보기 이슈:')
for k, v in sorted(sources.items()):
    pct = v['issues'] / v['total'] * 100
    print(f'  {k}: {v["issues"]}/{v["total"]} ({pct:.0f}%)')
