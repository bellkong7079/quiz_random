import fitz, re, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

CIRCLE = '①②③④'

def parse_answers(last_page):
    answers = {}
    m = re.search(r'정답(?:\s*및\s*해설)?\s*(.+)', last_page, re.DOTALL)
    text = m.group(1) if m else last_page
    for m in re.finditer(r'(\d+)\s*\.\s*([①②③④])', text):
        answers[int(m.group(1))] = CIRCLE.index(m.group(2))
    return answers

def clean(s):
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\n+', ' ', s)
    return s.strip()

def clean_q(s):
    """Remove embedded question number and clean."""
    s = clean(s)
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

def parse_pdf(path):
    source = Path(path).stem
    doc = fitz.open(path)
    pages = [doc[i].get_text() for i in range(len(doc))]

    answers = parse_answers(pages[-1])
    body = '\n'.join(pages[:-1])

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

    # Pattern: [q_text?] [c1①] [c2②] [c3③] [c4④]
    q_pat = re.compile(
        r'(.+?\?)'   # question text ending with ?
        r'(.*?)①'    # choice 1 (before ①)
        r'(.*?)②'    # choice 2
        r'(.*?)③'    # choice 3
        r'(.*?)④',   # choice 4 (up to ④)
        re.DOTALL
    )

    all_matches = list(q_pat.finditer(body))
    questions = []
    seen_qno = set()

    for i, m in enumerate(all_matches):
        q_raw   = m.group(1)   # ends with '?'
        c1_raw  = m.group(2)
        c2_raw  = m.group(3)
        c3_raw  = m.group(4)
        c4_raw  = m.group(5)

        # c4 continuation: text from end of this match until first sentence-end
        if i + 1 < len(all_matches):
            gap = body[m.end():all_matches[i+1].start()]
        else:
            gap = body[m.end():]
        cont_m = re.match(r'^([^①②③④?]*?[。.！!\)])', gap.lstrip('\n '))
        c4_cont = cont_m.group(1) if cont_m else ''

        # Clean q_raw (remove trailing ?)
        q_content = q_raw[:-1]
        q_text = clean_q(q_content) + '?'
        if not q_text or q_text == '?':
            continue

        # Extract question number from q_raw
        # Prefer number right before '?' (e.g., "것은\n1. \n?")
        qno_m = re.search(r'(\d{1,3})\.\s*$', q_content.rstrip())
        if not qno_m:
            # Fallback: first standalone "N." in q_raw
            qno_m = re.search(r'(?:^|\n)\s*(\d{1,3})\.\s*(?:\n|$)', q_content)
        if not qno_m:
            qno_m = re.search(r'\b(\d{1,3})\.\s', q_content)
        if not qno_m:
            continue
        qno = int(qno_m.group(1))
        if qno < 1 or qno > 100:
            continue
        if qno in seen_qno:
            continue
        seen_qno.add(qno)

        choices = [
            clean(c1_raw),
            clean(c2_raw),
            clean(c3_raw),
            clean(c4_raw + ' ' + c4_cont),
        ]

        questions.append({
            'source': source,
            'qno': qno,
            'q': q_text,
            'code': '',
            'lang': '',
            'choices': choices,
            'answer': answers.get(qno, -1),
            'explanation': ''
        })

    # Sort by qno
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
