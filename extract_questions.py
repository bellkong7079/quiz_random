import fitz, sys, re, json, os, base64
sys.stdout.reconfigure(encoding='utf-8')

# ──────────────────────────────────────────────
# 보기 문자 정규화
# ──────────────────────────────────────────────
def get_question_region_image(doc, page_texts, q_text):
    """문제 텍스트와 첫 보기(①) 사이 영역을 렌더링해서 이미지로 반환"""
    snippet = q_text[:20]
    for page_num, page_text in enumerate(page_texts):
        if snippet not in page_text:
            continue
        page = doc[page_num]
        blocks = page.get_text("blocks")
        page_width = page.rect.width

        # 문제 텍스트 블록 위치 파악 (x좌표 포함)
        q_block = None
        for b in blocks:
            if snippet in b[4].replace('\n', ' '):
                q_block = b
                break
        if q_block is None:
            continue
        q_x0, q_y1 = q_block[0], q_block[3]

        # 2단 레이아웃 대응: 문제 블록의 실제 x 범위를 기준으로 컬럼 한정
        q_x1 = q_block[2]
        margin = 30
        col_x0 = max(0, q_x0 - margin)
        col_x1 = min(page_width, q_x1 + margin)

        # 같은 컬럼 내에서만 ① 블록 찾기
        ch_y0 = None
        for b in sorted(blocks, key=lambda x: x[1]):
            if b[1] >= q_y1 and '①' in b[4] and b[0] >= col_x0 and b[2] <= col_x1:
                ch_y0 = b[1]
                break
        if ch_y0 is None or ch_y0 - q_y1 < 60:
            return ''

        drawings_in = [d for d in page.get_drawings()
                       if d['rect'].y0 >= q_y1 and d['rect'].y1 <= ch_y0
                       and d['rect'].x0 >= col_x0 and d['rect'].x1 <= col_x1]
        text_in = [b for b in blocks
                   if b[6] == 0 and b[1] >= q_y1 and b[3] <= ch_y0
                   and b[0] >= col_x0 and b[2] <= col_x1]

        # 트리/순서도: 선이 5개 이상이고 텍스트보다 그림이 많아야 진짜 다이어그램
        if len(drawings_in) < 5 or len(text_in) > len(drawings_in):
            return ''

        # 해당 컬럼 영역만 렌더링
        rect = fitz.Rect(col_x0, q_y1, col_x1, ch_y0)
        pix = page.get_pixmap(clip=rect, dpi=150, colorspace=fitz.csRGB)
        return f'data:image/png;base64,{base64.b64encode(pix.tobytes("png")).decode()}'
    return ''

def norm(c):
    if c in '①': return 0
    if c in '②': return 1
    if c in '③': return 2
    if c in '④': return 3
    return -1

# ──────────────────────────────────────────────
# 선택지 텍스트 정리 (줄바꿈 의도적인 것 보존)
# ──────────────────────────────────────────────
def clean_choice(raw):
    text = raw.strip()
    # 각 줄을 정리 (앞뒤 공백 제거)
    lines = [l.strip() for l in text.split('\n')]
    # 빈 줄 제거
    lines = [l for l in lines if l]
    if len(lines) <= 1:
        return text.replace('\n', ' ')[:200]
    # 줄이 여러 개면 줄바꿈 의미 있음 (예: Hello\nWorld 출력 결과)
    # 단, 각 줄이 너무 짧으면 그냥 이어붙이기 (PDF 추출 아티팩트)
    total_len = sum(len(l) for l in lines)
    if total_len < 30 or any(len(l) < 3 for l in lines):
        # 줄 길이 짧으면 의미 있는 줄바꿈 — 보존
        return '\n'.join(lines)[:200]
    # 줄이 길면 합치기 (긴 설명문)
    return ' '.join(lines)[:200]

# ──────────────────────────────────────────────
# 코드 포맷팅
# ──────────────────────────────────────────────
def reformat_java(code):
    out = []; indent = 0; i = 0; n = len(code)
    while i < n:
        c = code[i]
        if c == '{':
            out.append(' {'); indent += 1
            out.append('\n' + '    ' * indent)
            while i+1 < n and code[i+1] == ' ': i += 1
        elif c == '}':
            while out and out[-1] == ' ': out.pop()
            indent = max(0, indent - 1)
            out.append('\n' + '    ' * indent + '}')
        elif c == ';':
            out.append(';')
            j = i + 1
            while j < n and code[j] == ' ': j += 1
            if j < n and code[j] not in '}':
                out.append('\n' + '    ' * indent); i = j - 1
        else:
            out.append(c)
        i += 1
    return re.sub(r'\n{3,}', '\n\n', ''.join(out).strip())

def reformat_python(code):
    # PDF 추출 아티팩트: 열린 괄호 뒤 잘린 줄 합치기 (예: "print(\ntotal_\nsum)")
    raw_lines = [l.strip() for l in code.split('\n') if l.strip()]
    merged = []
    for line in raw_lines:
        if merged and merged[-1].count('(') > merged[-1].count(')'):
            merged[-1] += line
        else:
            merged.append(line)
    code = '\n'.join(merged)

    if '\n' in code and code.count('\n') > 2:
        return code
    for kw in ['def ', 'return ', 'for ', 'while ', 'if ', 'elif ',
                'else:', 'match ', 'case ', 'print(', 'result', 'total', 'hap', 'sum']:
        code = re.sub(r'(?<!\n)(?<!\A)(' + re.escape(kw) + r')', r'\n\1', code)
    lines = [l.strip() for l in code.split('\n') if l.strip()]
    out = []; indent = 0
    for l in lines:
        if re.match(r'(def |class |for |while |if |elif |else:)', l):
            out.append('    ' * indent + l)
            if l.endswith(':'): indent += 1
        else:
            out.append('    ' * indent + l)
    return '\n'.join(out)

def reformat_sql(code):
    for kw in ['SELECT','FROM','WHERE','ORDER BY','GROUP BY','HAVING',
               'INSERT INTO','VALUES','UPDATE','SET','DELETE FROM',
               'CREATE TABLE','DROP TABLE','ALTER TABLE']:
        code = re.sub(r'\s+(' + re.escape(kw) + r')\s+',
                      r'\n\1 ', code, flags=re.IGNORECASE)
    return code.strip()

# ──────────────────────────────────────────────
# 코드 블록 분리 (Java / Python / SQL 감지)
# ──────────────────────────────────────────────
def split_q_and_code(q_text):
    # Java: public class, class X {, public static void main, System.out
    java_m = re.search(
        r'(public\s+class\s+\w+|'         # public class Foo
        r'class\s+\w+\s*\{|'              # class Foo {
        r'class\s+\w+\s+extends\s+\w+|'  # class Sub extends Super
        r'public\s+static\s+void\s+main|'# main 메서드
        r'System\.out\.)',                 # System.out.print
        q_text)
    # Python
    py_m = re.search(
        r'(def\s+\w+\s*[\(\*]|'
        r'print\s*\(|'
        r'for\s+\w+\s+in\s+range|'
        r'for\s+\w+\s+in\s+\w+\s*:|'  # for i in my_list:
        r'list_data\s*=|fruits\s*=|numbers\s*=|sentence\s*=|hap\s*=|'
        r'match\s+\w+\s*:|'           # match x:
        r'\w+\s*=\s*range\(|'         # my_list = range(10)
        r'[a-z][a-z0-9_]+\s*=\s*\d+|' # total_sum = 0, count = 0
        r'\w+\s*=\s*\[|'              # data = [
        r'import\s+\w+|'              # import ...
        r'\w+\s*=\s*\{)',             # dict = {
        q_text)
    # SQL
    sql_m = re.search(
        r'(?i)(SELECT\s+[\w\*]|INSERT\s+INTO|UPDATE\s+\w+\s+SET'
        r'|DELETE\s+FROM|CREATE\s+TABLE|DROP\s+TABLE|ALTER\s+TABLE)',
        q_text)

    candidates = [(m, lang) for m, lang in [
        (java_m, 'java'), (py_m, 'python'), (sql_m, 'sql')
    ] if m]
    if not candidates:
        return q_text.strip(), '', ''

    best_m, lang = min(candidates, key=lambda x: x[0].start())
    desc = q_text[:best_m.start()].strip()
    raw_code = q_text[best_m.start():].strip()

    # 한글이 많으면 코드가 아님 (PDF 다단 추출 오류)
    korean_ratio = len(re.findall(r'[가-힣]', raw_code)) / max(len(raw_code), 1)
    if korean_ratio > 0.1:
        return q_text.strip(), '', ''

    if lang == 'java':   code = reformat_java(raw_code)
    elif lang == 'python': code = reformat_python(raw_code)
    else:                  code = reformat_sql(raw_code)

    return desc, code, lang

# ──────────────────────────────────────────────
# 시나공 해설 파서
# ──────────────────────────────────────────────
def parse_sinagong_explanations(full_text):
    exp_map = {}
    parts = re.split(r'(\d)회 최종점검 모의고사 해설', full_text)
    for pi in range(1, len(parts), 2):
        round_no = int(parts[pi])
        block = parts[pi+1] if pi+1 < len(parts) else ''
        exp_pat = re.compile(
            r'(?:^|\n)(\d{1,2})[ \t]{2,}(.+?)(?=\n\d{1,2}[ \t]{2,}|\n\d{3}\n|\Z)',
            re.DOTALL)
        for m in exp_pat.finditer(block):
            qno = int(m.group(1))
            if not (1 <= qno <= 60): continue
            raw = m.group(2).strip()
            raw = raw.replace('\x07', '').replace('\t', ' ')
            raw = re.sub(r'\s+', ' ', raw).strip()
            raw = re.sub(r'•\s*', '\n• ', raw)
            raw = re.sub(r'[❶❷❸❹❺❻❼❽]', '', raw).strip()
            if len(raw) > 10:
                exp_map[(round_no, qno)] = raw
    return exp_map

# ──────────────────────────────────────────────
# 시나공 문제 파서
# ──────────────────────────────────────────────
def parse_sinagong(path):
    doc = fitz.open(path)
    page_texts = [doc[i].get_text() for i in range(doc.page_count)]
    full = ''.join(page_texts)
    questions = []

    exp_map = parse_sinagong_explanations(full)
    print(f'  시나공 해설 추출: {len(exp_map)}개', file=sys.stderr)

    cp = re.compile(r'([①②③④])\s*(.+?)(?=[①②③④]|$)', re.DOTALL)
    rounds = re.split(r'(\d)회 최종점검 모의고사', full)

    for ri in range(1, len(rounds), 2):
        round_no = int(rounds[ri])
        block = rounds[ri+1] if ri+1 < len(rounds) else ''

        amap = {}
        for m in re.finditer(r'정답\s*:\s*((?:\d+\.[①②③④]\s*)+)', block):
            for am in re.finditer(r'(\d+)\.([①②③④])', m.group(1)):
                amap[int(am.group(1))] = norm(am.group(2))

        pat = re.compile(
            r'(?<!\d)(\d{1,2})\.\s+(.+?)(?=\n\d{1,2}\.\s|\n정답|$)',
            re.DOTALL)

        for m in pat.finditer(block):
            qno = int(m.group(1))
            if not (1 <= qno <= 60): continue
            raw = m.group(2).strip()
            found = cp.findall(raw)
            if len(found) < 4: continue

            choices = [clean_choice(c[1]) for c in found[:4]]

            qtxt = raw
            for ch in '①②③④':
                i = qtxt.find(ch)
                if i != -1: qtxt = qtxt[:i].strip(); break
            qtxt = qtxt.replace('\n', ' ').strip()
            if len(qtxt) < 5: continue

            ans = amap.get(qno, -1)
            if ans == -1: continue

            desc, code, lang = split_q_and_code(qtxt)
            exp = exp_map.get((round_no, qno), '')
            img = get_question_region_image(doc, page_texts, qtxt) if not code else ''
            questions.append({
                'source': f'시나공 {round_no}회',
                'q': desc, 'code': code, 'lang': lang,
                'choices': choices, 'answer': ans,
                'explanation': exp, 'image': img
            })

    print(f'  시나공 문제 추출: {len(questions)}개', file=sys.stderr)
    return questions

# ──────────────────────────────────────────────
# 이기적 파서
# ──────────────────────────────────────────────
def parse_ikjeok(path):
    doc = fitz.open(path)
    page_texts = [doc[i].get_text() for i in range(doc.page_count)]
    full = ''.join(page_texts)
    questions = []
    cp = re.compile(r'([①②③④])\s*(.+?)(?=[①②③④]|$)', re.DOTALL)

    def extract_answers(text):
        amap = {}
        for m in re.finditer(r'정답\s+((?:\d{2}\s+[①②③④]\s*){1,20})', text):
            for am in re.finditer(r'(\d{2})\s+([①②③④])', m.group(1)):
                amap[int(am.group(1))] = norm(am.group(2))
        return amap

    parts = re.split(r'합격을 다지는\n?예상문제', full)
    for pi, part in enumerate(parts[1:], 1):
        amap = extract_answers(part)
        pat = re.compile(
            r'(?:^|\n)(\d{2})\s+(.+?)(?=\n\d{2}\s|\n정답|$)',
            re.DOTALL)
        for m in pat.finditer(part):
            qno = int(m.group(1))
            if not (1 <= qno <= 20): continue
            raw = m.group(2).strip()
            found = cp.findall(raw)
            if len(found) < 4: continue

            choices = [clean_choice(c[1]) for c in found[:4]]

            qtxt = raw
            for ch in '①②③④':
                i = qtxt.find(ch)
                if i != -1: qtxt = qtxt[:i].strip(); break
            qtxt = qtxt.replace('\n', ' ').strip()
            if len(qtxt) < 5: continue

            ans = amap.get(qno, -1)
            if ans == -1: continue
            desc, code, lang = split_q_and_code(qtxt)
            img = get_question_region_image(doc, page_texts, qtxt) if not code else ''
            questions.append({
                'source': f'이기적_예상{pi}',
                'q': desc, 'code': code, 'lang': lang,
                'choices': choices, 'answer': ans,
                'explanation': '', 'image': img
            })

    print(f'  이기적 문제 추출: {len(questions)}개', file=sys.stderr)
    return questions

# ──────────────────────────────────────────────
# 중복 제거
# ──────────────────────────────────────────────
def dedup(qs):
    seen, out = set(), []
    for q in qs:
        k = q['q'][:30]
        if k not in seen:
            seen.add(k); out.append(q)
    return out

# ──────────────────────────────────────────────
# 실행
# ──────────────────────────────────────────────
if __name__ == '__main__':
    base = os.path.dirname(os.path.abspath(__file__)) + '/'
    print('추출 중...', file=sys.stderr)
    qs1 = parse_sinagong(base + '2026시나공_프로그래밍기능사필기_최종점검모의고사.pdf')
    qs2 = parse_ikjeok(base + '2026 이기적 프로그래밍기능사 필기 기본서(기출분석자료).pdf')
    all_qs = dedup(qs1 + qs2)
    has_exp = sum(1 for q in all_qs if q.get('explanation'))
    print(f'총 {len(all_qs)}문제 (해설 있음: {has_exp}개)', file=sys.stderr)
    out_path = base + 'questions.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_qs, f, ensure_ascii=False, indent=2)
    print(f'저장 완료: {out_path}')
