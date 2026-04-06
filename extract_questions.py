import fitz, sys, re, json
sys.stdout.reconfigure(encoding='utf-8')

# ──────────────────────────────────────────────
# 보기 문자 정규화
# ──────────────────────────────────────────────
def norm(c):
    if c in '①': return 0
    if c in '②': return 1
    if c in '③': return 2
    if c in '④': return 3
    return -1

# ──────────────────────────────────────────────
# 코드 블록 감지 & 포맷팅
# ──────────────────────────────────────────────
CODE_TRIGGERS = re.compile(
    r'(public\s+class\s+\w+|public\s+static\s+void|'
    r'System\.out\.|new\s+\w+\s*\(|'
    r'def\s+\w+\s*\(|print\s*\(|for\s+\w+\s+in\s+range|'
    r'while\s+\w+|if\s+\w+.*:$|'
    r'^\s*SELECT\s+|^\s*INSERT\s+|^\s*UPDATE\s+|^\s*DELETE\s+|'
    r'^\s*CREATE\s+|^\s*DROP\s+|^\s*ALTER\s+)',
    re.IGNORECASE | re.MULTILINE
)

def reformat_java(code):
    """Java 코드: {, }, ; 기준으로 줄바꿈·들여쓰기 복원"""
    out = []
    indent = 0
    i = 0
    code = code.strip()
    n = len(code)
    while i < n:
        c = code[i]
        if c == '{':
            out.append(' {')
            indent += 1
            out.append('\n' + '    ' * indent)
            # 다음 공백 건너뜀
            while i+1 < n and code[i+1] == ' ':
                i += 1
        elif c == '}':
            # 줄 끝 공백 제거 후 닫기
            while out and out[-1] == ' ':
                out.pop()
            indent = max(0, indent - 1)
            out.append('\n' + '    ' * indent + '}')
        elif c == ';':
            out.append(';')
            # 다음이 공백 or 닫는 중괄호면 줄바꿈
            j = i + 1
            while j < n and code[j] == ' ':
                j += 1
            if j < n and code[j] not in '}':
                out.append('\n' + '    ' * indent)
                i = j - 1
        else:
            out.append(c)
        i += 1
    result = ''.join(out).strip()
    # 빈 줄 여러개 제거
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result

def reformat_python(code):
    """Python: 키워드 앞에 줄바꿈 삽입"""
    # 이미 줄바꿈이 있으면 그대로
    if '\n' in code and code.count('\n') > 2:
        return code
    # 키워드 앞에 줄바꿈 삽입
    keywords = ['def ', 'return ', 'for ', 'while ', 'if ', 'elif ', 'else:', 'print(', 'result', 'total', 'sum']
    result = code
    for kw in keywords:
        # 줄 시작이 아닐 때만
        result = re.sub(r'(?<!\n)(?<!\A)(' + re.escape(kw) + r')', r'\n\1', result)
    # 들여쓰기 추정: 키워드 다음 블록
    lines = result.split('\n')
    formatted = []
    indent = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.match(r'(def |class |for |while |if |elif |else:)', line):
            formatted.append('    ' * indent + line)
            if line.endswith(':'):
                indent += 1
        elif line.startswith('return ') or line.startswith('break') or line.startswith('continue'):
            formatted.append('    ' * indent + line)
        else:
            formatted.append('    ' * indent + line)
        # 닫는 경우 (단순 휴리스틱)
    return '\n'.join(formatted)

def reformat_sql(code):
    """SQL: 주요 절 앞에 줄바꿈"""
    keywords = ['SELECT', 'FROM', 'WHERE', 'ORDER BY', 'GROUP BY', 'HAVING',
                'INSERT INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE FROM',
                'CREATE TABLE', 'DROP TABLE', 'ALTER TABLE']
    result = code.strip()
    for kw in keywords:
        result = re.sub(r'\s+(' + re.escape(kw) + r')\s+',
                        r'\n\1 ', result, flags=re.IGNORECASE)
    return result.strip()

def split_q_and_code(q_text):
    """질문 텍스트에서 코드 부분을 분리, (설명, 코드, 언어) 반환"""
    # Java
    java_m = re.search(
        r'(public\s+class\s+\w+|public\s+static\s+void\s+main|'
        r'class\s+\w+\s*\{|System\.out\.|new\s+\w+\s*\()',
        q_text)
    # Python
    py_m = re.search(
        r'(def\s+\w+\s*[\(\*]|print\s*\(|for\s+\w+\s+in\s+range'
        r'|list_data|fruits\s*=|numbers\s*=|sentence\s*=|hap\s*=)',
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

    # 가장 앞에 나오는 것 선택
    best_m, lang = min(candidates, key=lambda x: x[0].start())
    desc = q_text[:best_m.start()].strip()
    raw_code = q_text[best_m.start():].strip()

    if lang == 'java':
        code = reformat_java(raw_code)
    elif lang == 'python':
        code = reformat_python(raw_code)
    else:
        code = reformat_sql(raw_code)

    return desc, code, lang

# ──────────────────────────────────────────────
# 시나공 파서
# ──────────────────────────────────────────────
def parse_sinagong(path):
    doc = fitz.open(path)
    full = ''.join(doc[i].get_text() for i in range(doc.page_count))
    questions = []

    rounds = re.split(r'(\d)회 최종점검 모의고사', full)
    for ri in range(1, len(rounds), 2):
        round_no = rounds[ri]
        block = rounds[ri+1] if ri+1 < len(rounds) else ''

        amap = {}
        for m in re.finditer(r'정답\s*:\s*((?:\d+\.[①②③④]\s*)+)', block):
            for am in re.finditer(r'(\d+)\.([①②③④])', m.group(1)):
                amap[int(am.group(1))] = norm(am.group(2))

        cp = re.compile(r'([①②③④])\s*(.+?)(?=[①②③④]|$)', re.DOTALL)
        pat = re.compile(r'(?<!\d)(\d{1,2})\.\s+(.+?)(?=\n\d{1,2}\.\s|\n정답|$)', re.DOTALL)

        for m in pat.finditer(block):
            qno = int(m.group(1))
            if not (1 <= qno <= 60): continue
            raw = m.group(2).strip()
            found = cp.findall(raw)
            if len(found) < 4: continue
            choices = [c[1].strip().replace('\n', ' ')[:150] for c in found[:4]]
            qtxt = raw
            for ch in '①②③④':
                i = qtxt.find(ch)
                if i != -1: qtxt = qtxt[:i].strip(); break
            qtxt = qtxt.replace('\n', ' ').strip()
            if len(qtxt) < 5: continue
            ans = amap.get(qno, -1)
            if ans == -1: continue

            desc, code, lang = split_q_and_code(qtxt)
            questions.append({
                'source': f'시나공 {round_no}회',
                'q': desc,
                'code': code,
                'lang': lang,
                'choices': choices,
                'answer': ans
            })

    print(f'시나공 추출: {len(questions)}개', file=sys.stderr)
    return questions

# ──────────────────────────────────────────────
# 이기적 파서
# ──────────────────────────────────────────────
def parse_ikjeok(path):
    doc = fitz.open(path)
    full = ''.join(doc[i].get_text() for i in range(doc.page_count))
    questions = []

    def extract_answers(text):
        amap = {}
        for m in re.finditer(r'정답\s+((?:\d{2}\s+[①②③④]\s*){1,20})', text):
            for am in re.finditer(r'(\d{2})\s+([①②③④])', m.group(1)):
                amap[int(am.group(1))] = norm(am.group(2))
        return amap

    def process_block(text, src):
        amap = extract_answers(text)
        cp = re.compile(r'([①②③④])\s*(.+?)(?=[①②③④]|$)', re.DOTALL)
        pat = re.compile(r'(?:^|\n)(\d{2})\s+(.+?)(?=\n\d{2}\s|\n정답|$)', re.DOTALL)
        for m in pat.finditer(text):
            qno = int(m.group(1))
            if not (1 <= qno <= 20): continue
            raw = m.group(2).strip()
            found = cp.findall(raw)
            if len(found) < 4: continue
            choices = [c[1].strip().replace('\n', ' ')[:150] for c in found[:4]]
            qtxt = raw
            for ch in '①②③④':
                i = qtxt.find(ch)
                if i != -1: qtxt = qtxt[:i].strip(); break
            qtxt = qtxt.replace('\n', ' ').strip()
            if len(qtxt) < 5: continue
            ans = amap.get(qno, -1)
            if ans == -1: continue
            desc, code, lang = split_q_and_code(qtxt)
            questions.append({
                'source': src,
                'q': desc,
                'code': code,
                'lang': lang,
                'choices': choices,
                'answer': ans
            })

    parts = re.split(r'합격을 다지는\n?예상문제', full)
    for pi, part in enumerate(parts[1:], 1):
        process_block(part, f'이기적_예상{pi}')

    print(f'이기적 추출: {len(questions)}개', file=sys.stderr)
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
    base = 'c:/Users/3class_013/Desktop/프로그래밍기능사/'
    qs1 = parse_sinagong(base + '2026시나공_프로그래밍기능사필기_최종점검모의고사.pdf')
    qs2 = parse_ikjeok(base + '2026 이기적 프로그래밍기능사 필기 기본서(기출분석자료).pdf')
    all_qs = dedup(qs1 + qs2)
    print(f'총 {len(all_qs)}개 문제 추출', file=sys.stderr)
    out_path = base + 'questions.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_qs, f, ensure_ascii=False, indent=2)
    print(f'저장 완료: {out_path}')
    print(f'TOTAL:{len(all_qs)}')
