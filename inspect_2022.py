import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')

qs = json.load(open(r'C:\Users\jb733\OneDrive\바탕 화면\quiz\quiz_random\sanup_questions.json', encoding='utf-8'))

# 2022년 문제만
qs22 = [q for q in qs if '2022' in q.get('source','')]
print(f'2022년 문제: {len(qs22)}개')

# 샘플 확인 (빈 보기 있는 것)
bad = [q for q in qs22 if any(len(c.strip())<2 for c in q.get('choices',[]))]
print(f'빈/짧은 보기: {len(bad)}개')
for q in bad[:8]:
    print(f'  q: {q["q"][:70]}')
    print(f'  choices: {q["choices"]}')
    print(f'  answer: {q.get("answer")}')
    print()

# 정답 없는 것
no_ans_22 = [q for q in qs22 if q.get('answer',-1)==-1]
print(f'정답 없는 2022년 문제: {len(no_ans_22)}개')
