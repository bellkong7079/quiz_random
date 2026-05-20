import fitz, re, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

CIRCLE = '①②③④'

def find_answer_table_pos(full_text):
    """정답 테이블 시작 위치 반환 (커버 타이틀 말고 실제 답안표)"""
    for m in re.finditer(r'정답[^\n①②③④]{0,20}\n', full_text):
        tail = full_text[m.start():m.start()+300]
        # "1.②" 또는 "1 ②" 형식 테이블이 바로 뒤에 오면 진짜 정답 섹션
        if re.search(r'(?:^|\n)\s*1\s*\.?\s*[①②③④]', tail):
            return m.start()
    return None

def parse_answers(full_text):
    answers = {}
    pos = find_answer_table_pos(full_text)
    if pos is not None:
        tail = full_text[pos:]
        for m in re.finditer(r'(\d{1,2})\s*\.?\s*([①②③④])', tail):
            n = int(m.group(1))
            if n not in answers:
                answers[n] = CIRCLE.index(m.group(2))
    # 패턴2: "정답 : 1.② 2.③ ..." (시나공 형식)
    for m in re.finditer(r'정답\s*:\s*((?:\d+\.[①②③④]\s*)+)', full_text):
        for am in re.finditer(r'(\d+)\.([①②③④])', m.group(1)):
            n = int(am.group(1))
            if n not in answers:
                answers[n] = CIRCLE.index(am.group(2))
    return answers

def clean(s):
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\n+', ' ', s)
    return s.strip()

def clean_q(s):
    """Remove embedded question number and clean."""
    s = clean(s)
    # Strip exam title / page header text appended to question
    s = re.sub(r'\s*정보처리산업기사\s*필기?\s*기출문제.*', '', s)
    s = re.sub(r'\s*기출문제\s*정답\s*및\s*해설.*', '', s)
    # Remove "N." at the very end (appears just before ?)
    s = re.sub(r'\s+\d{1,3}\.\s*$', '', s).strip()
    # Remove inline "N. " patterns
    s = re.sub(r'(?<!\d)\s+\d{1,3}\.\s+', ' ', s).strip()
    # Remove leading circle characters or standalone digits
    s = re.sub(r'^[①②③④\s]+', '', s).strip()
    s = re.sub(r'^\d\s+', '', s).strip()
    # Remove leading "N. " question number prefix
    s = re.sub(r'^\d{1,3}\.\s+', '', s).strip()
    # Remove leading sentence-final continuation from prev choice: "한다. " "이다. "
    s = re.sub(r'^[가-힣a-zA-Z\s]{0,3}다\.\s+(?=[가-힣])', '', s).strip()
    s = re.sub(r'^[가-힣a-zA-Z\s]{2,40}[다이]\.\s+(?=[가-힣])', '', s).strip()
    # Remove leading short pure-ASCII/symbol prefix before Korean (e.g. "+ ", "gets ", "DROP ")
    s = re.sub(r'^[a-zA-Z㉠-㉿\+\-\*\/\%&=,\.\s]{1,25}\s+(?=[가-힣])', '', s).strip()
    return s

def clean_choice(s):
    """Strip PDF artifacts from a choice string."""
    s = clean(s)
    # Strip page headers / exam title text appended to choice
    s = re.sub(r'\s*정보처리산업기사\s*필기?\s*기출문제.*', '', s)
    s = re.sub(r'\s*정보처리\s*산업기사.*기출문제.*', '', s)
    # Strip copyright / answer-sheet trailer (handles "기출문제 정답및해설" and "기출문제& 정답및해설")
    s = re.sub(r'\s*기출문제\s*[&\s]*정답\s*및?\s*해설.*', '', s)
    s = re.sub(r'\s*기출문제\s*&.*', '', s)
    s = re.sub(r'\s*이\s*자료는\s*시나공.*', '', s)
    s = re.sub(r'\s*저작권.*', '', s)
    # Strip trailing exam metadata like "& 년 회 ..."
    s = re.sub(r'\s*&\s*\d*\s*년\s*\d*\s*회.*', '', s)
    # Strip trailing page number artifacts like " 2023 이기적 ..." or " 2022 "
    s = re.sub(r'\s+20\d\d\s+[가-힣a-zA-Z].*', '', s)
    # Strip trailing standalone year/number that looks like page marker
    s = re.sub(r'\s+\d{4}\s*$', '', s)
    return s.strip()

def parse_pdf(path):
    source = Path(path).stem
    doc = fitz.open(path)
    pages = [doc[i].get_text() for i in range(len(doc))]

    full_text = '\n'.join(pages)
    answers = parse_answers(full_text)
    # 문제 본문: 정답 테이블 이전까지
    ans_pos = find_answer_table_pos(full_text)
    body = full_text[:ans_pos] if ans_pos is not None else full_text

    # Remove noise
    body = re.sub(r'제\s*\d*\s*과목[^\n]+', '', body)
    # Remove full instruction header including all ①②③④ symbols
    body = re.sub(r'다음 문제를 읽고[^①]*①[^②]*②[^③]*③[^④]*④', '', body, flags=re.DOTALL)
    body = re.sub(r'※[^\n]+', '', body)
    body = re.sub(r'-\s*\d+\s*-', ' ', body)
    body = re.sub(r'회\s*\n?\s*\d+\b', ' ', body)
    # Remove copyright / answer-sheet header lines
    body = re.sub(r'저작권[^\n]+', '', body)
    body = re.sub(r'기출문제 정답 및 해설.+?(?=\d{1,3}\.)', '', body, flags=re.DOTALL)
    # Remove standalone subject numbers like "\n1\n" or "\n2\n"
    body = re.sub(r'(?:^|\n)\s*[1-5]\s*\n', '\n', body)

    # 포맷 감지: ①뒤 텍스트(표준형) vs 텍스트뒤 ①(역순형)
    standard_count = len(re.findall(r'[①②③④]\s*\S{3,}', body))
    reversed_count = len(re.findall(r'[①②③④]\s*\n', body))
    is_reversed = reversed_count > standard_count

    CP = re.compile(r'([①②③④])\s*(.+?)(?=[①②③④]|$)', re.DOTALL)
    questions = []
    seen_qno = set()

    if is_reversed:
        # 역순형 파서: [질문?] [c1①] [c2②] [c3③] [c4④]
        q_pat = re.compile(
            r'(.+?\?)(.*?)①(.*?)②(.*?)③(.*?)④',
            re.DOTALL
        )
        all_matches = list(q_pat.finditer(body))
        for i, m in enumerate(all_matches):
            q_raw, c1_raw, c2_raw, c3_raw, c4_raw = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
            gap = body[m.end():all_matches[i+1].start()] if i+1 < len(all_matches) else body[m.end():]
            cont_m = re.match(r'^([^①②③④?]*?[。.！!\)])', gap.lstrip('\n '))
            c4_cont = cont_m.group(1) if cont_m else ''
            q_content = q_raw[:-1]
            q_text = clean_q(q_content) + '?'
            if not q_text or q_text == '?':
                continue
            qno_m = (re.search(r'(\d{1,3})\.\s*$', q_content.rstrip()) or
                     re.search(r'(?:^|\n)\s*(\d{1,3})\.\s*(?:\n|$)', q_content) or
                     re.search(r'\b(\d{1,3})\.\s', q_content))
            if not qno_m:
                continue
            qno = int(qno_m.group(1))
            if not (1 <= qno <= 100) or qno in seen_qno:
                continue
            seen_qno.add(qno)
            choices = [clean_choice(c1_raw), clean_choice(c2_raw), clean_choice(c3_raw), clean_choice(c4_raw + ' ' + c4_cont)]
            questions.append({'source': source, 'qno': qno, 'q': q_text,
                              'code': '', 'lang': '', 'choices': choices,
                              'answer': answers.get(qno, -1), 'explanation': ''})
    else:
        # 표준형 파서: ①텍스트 ②텍스트 ③텍스트 ④텍스트
        pat = re.compile(
            r'(?:^|\n)(\d{1,2})[\.\s]\s*(.+?)(?=\n\d{1,2}[\.\s]|\Z)',
            re.DOTALL)
        for m in pat.finditer(body):
            qno = int(m.group(1))
            if not (1 <= qno <= 60):
                continue
            raw = m.group(2).strip()
            found = CP.findall(raw)
            if len(found) < 4:
                continue
            choices = [clean_choice(c[1]) for c in found[:4]]
            valid = sum(1 for c in choices if len(c) >= 2)
            if valid < 2:
                continue
            qtxt = raw
            for ch in '①②③④':
                i = qtxt.find(ch)
                if i != -1: qtxt = qtxt[:i].strip(); break
            qtxt = re.sub(r'\s+', ' ', qtxt.replace('\n', ' ')).strip()
            if len(qtxt) < 5 or qno in seen_qno:
                continue
            seen_qno.add(qno)
            questions.append({'source': source, 'qno': qno, 'q': qtxt,
                              'code': '', 'lang': '', 'choices': choices,
                              'answer': answers.get(qno, -1), 'explanation': ''})

    questions.sort(key=lambda x: x['qno'])
    return questions, len(answers)

def main():
    base = Path(__file__).parent
    folders = [
        '20년_산업기사필기기출문제',
        '2021년_산업기사필기기출문제',
        '22년_정보처리산업기사_필기_기출문제',
        '2023 정보처리산업기사필기 기출문제',
        '정보처리산업기사 필기 기출문제 (1)',
        '2025년 정보처리산업기사 기출문제',
    ]

    all_q = []
    for folder in folders:
        fp = base / folder
        if not fp.exists():
            continue
        for pdf in sorted(fp.glob('*.pdf')):
            qs, n_ans = parse_pdf(str(pdf))
            print(f'  {pdf.name}: {len(qs)}문제 (정답 {n_ans}개)', file=sys.stderr)
            all_q.extend(qs)

    # Global dedup by (source, qno)
    seen = set()
    deduped = []
    for q in all_q:
        key = (q['source'], q['qno'])
        if key not in seen:
            seen.add(key)
            deduped.append(q)

    print(f'\n총 {len(deduped)}문제 추출 완료', file=sys.stderr)

    out = base / 'sanup_questions.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)
    print(f'저장 완료: {out}', file=sys.stderr)

if __name__ == '__main__':
    main()
