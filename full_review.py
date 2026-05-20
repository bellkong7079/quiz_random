import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')

def check_file(path, label):
    qs = json.load(open(path, encoding='utf-8'))
    print(f'\n{"="*60}')
    print(f'{label}: {len(qs)}문제')
    print('='*60)

    issues = []

    for i, q in enumerate(qs):
        q_text = q.get('q', '')
        code = q.get('code', '')
        choices = q.get('choices', [])
        ans = q.get('answer', -1)
        exp = q.get('explanation', '')

        # 문제 텍스트가 너무 길면 다른 문제 내용이 섞인 것
        if len(q_text) > 200:
            issues.append(f'[{i+1}] 문제텍스트 너무 김({len(q_text)}자): {q_text[:80]}...')

        # 문제 텍스트에 번호 패턴 있으면 (52. 53. 등) 다른 문제 섞임
        if re.search(r'\n?\d{2,3}\.\s+[가-힣]', q_text):
            issues.append(f'[{i+1}] 문제텍스트에 다른 문제번호 포함: {q_text[:80]}')

        # 보기가 4개 미만
        if len(choices) < 4:
            issues.append(f'[{i+1}] 보기 부족({len(choices)}개): {q_text[:50]}')

        # 보기 텍스트가 너무 짧거나 이상
        for ci, c in enumerate(choices[:4]):
            if len(c.strip()) < 2:
                issues.append(f'[{i+1}] 보기{ci+1} 너무 짧음: "{c}"')

        # 정답 범위 체크
        if ans not in [-1, 0, 1, 2, 3]:
            issues.append(f'[{i+1}] 정답 이상: {ans}')

        # 코드에 한글이 많으면 잘못 추출
        if code:
            kr = len(re.findall(r'[가-힣]', code))
            if kr > 5:
                issues.append(f'[{i+1}] 코드에 한글 포함({kr}자): {code[:60]}')

        # 코드가 있는데 언어 없음
        if code and not q.get('lang'):
            issues.append(f'[{i+1}] 코드있는데 lang 없음: {code[:40]}')

    print(f'발견된 이슈: {len(issues)}개')
    for iss in issues[:30]:
        print(f'  {iss}')

    # 통계
    with_img = sum(1 for q in qs if q.get('image'))
    with_code = sum(1 for q in qs if q.get('code'))
    with_exp = sum(1 for q in qs if q.get('explanation'))
    print(f'\n통계: 이미지={with_img} 코드={with_code} 해설={with_exp}')

check_file(r'C:\Users\jb733\OneDrive\바탕 화면\quiz\quiz_random\questions.json', '프로그래밍기능사')
check_file(r'C:\Users\jb733\OneDrive\바탕 화면\quiz\quiz_random\sanup_questions.json', '정보처리산업기사')
