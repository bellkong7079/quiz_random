import fitz, sys, re, json
sys.stdout.reconfigure(encoding='utf-8')

# ──────────────────────────────────────────────
# 유틸: 보기 문자 정규화
# ──────────────────────────────────────────────
CIRCLE = {'①':0,'②':1,'③':2,'④':3,
          '①':0,'②':1,'③':2,'④':3}  # 혹시 다른 인코딩도 커버

def norm_choice_char(c):
    if c in '①①': return 0
    if c in '②②': return 1
    if c in '③③': return 2
    if c in '④④': return 3
    return -1

# ──────────────────────────────────────────────
# 시나공 파서 (1~5회 각 60문제)
# ──────────────────────────────────────────────
def parse_sinagong(path):
    doc = fitz.open(path)
    full = ''.join(doc[i].get_text() for i in range(doc.page_count))

    questions = []

    # 회차 블록 분리
    rounds = re.split(r'(\d)회 최종점검 모의고사', full)
    # rounds[0] = 앞부분(목차), [1]='1', [2]=1회 내용, [3]='2', [4]=2회 내용 ...

    for ri in range(1, len(rounds), 2):
        round_no = rounds[ri]
        block = rounds[ri+1] if ri+1 < len(rounds) else ''

        # 정답 파싱: "정답 : 1.② 2.③ ..." 또는 한 줄에 여러 개
        answer_map = {}
        for m in re.finditer(
            r'정답\s*:\s*((?:\d+\.[\①②③④]\s*)+)',
            block, re.DOTALL):
            for am in re.finditer(r'(\d+)\.([\①②③④])', m.group(1)):
                qno = int(am.group(1))
                answer_map[qno] = norm_choice_char(am.group(2))

        # 문제 파싱
        # 패턴: "N. 문제본문\n① A\n② B\n③ C\n④ D"
        # 문제 본문은 여러 줄 가능, 보기가 나오기 전까지
        q_pattern = re.compile(
            r'(?<!\d)(\d{1,2})\.\s+(.+?)(?=(?:\n\d{1,2}\.\s)|(?:\n정답)|$)',
            re.DOTALL
        )
        choice_pattern = re.compile(r'[①②③④①②③④]\s*(.+?)(?=[①②③④①②③④]|$)', re.DOTALL)

        for m in q_pattern.finditer(block):
            qno = int(m.group(1))
            if qno < 1 or qno > 60:
                continue
            raw = m.group(2).strip()

            # 보기 4개 분리
            cp = re.compile(r'([①②③④①②③④])\s*(.+?)(?=[①②③④①②③④]|정답|$)', re.DOTALL)
            choices_raw = cp.findall(raw)
            if len(choices_raw) < 4:
                continue

            choices = [c[1].strip().replace('\n', ' ')[:120] for c in choices_raw[:4]]

            # 문제 텍스트 (보기 이전)
            q_text = raw
            for ch in '①②③④①②③④':
                idx = q_text.find(ch)
                if idx != -1:
                    q_text = q_text[:idx].strip()
                    break

            q_text = q_text.replace('\n', ' ').strip()
            if len(q_text) < 5:
                continue

            # 코드 블록 감지 (자바/파이썬 코드가 있으면 분리)
            code = ''
            code_match = re.search(
                r'(public class|def |print\(|System\.out|var |int |String|class |SELECT|UPDATE|DELETE|INSERT|CREATE|DROP|ALTER)',
                q_text)
            # 코드는 본문에 포함된 채로 유지 (분리 어려움)

            ans = answer_map.get(qno, -1)
            if ans == -1:
                continue

            questions.append({
                'source': f'시나공 {round_no}회',
                'q': q_text,
                'choices': choices,
                'answer': ans
            })

    print(f'시나공 추출: {len(questions)}개', file=sys.stderr)
    return questions


# ──────────────────────────────────────────────
# 이기적 파서 (예상문제 + 기출복원문제)
# ──────────────────────────────────────────────
def parse_ikjeok(path):
    doc = fitz.open(path)
    full = ''.join(doc[i].get_text() for i in range(doc.page_count))

    questions = []

    # 정답 파싱: "정답  01 ③  02 ④ ..." 형태
    def extract_answers(text):
        amap = {}
        for m in re.finditer(r'정답\s+((?:\d{2}\s+[\①②③④①②③④]\s*)+)', text):
            for am in re.finditer(r'(\d{2})\s+([\①②③④①②③④])', m.group(1)):
                amap[int(am.group(1))] = norm_choice_char(am.group(2))
        return amap

    # 섹션별로 분리해서 파싱
    sections = re.split(r'합격을 다지는\n예상문제', full)
    section_names = ['이론', 'SEC01_예상', 'SEC02_예상', 'SEC03_예상', 'SEC04_예상', '기출']

    for si, sec in enumerate(sections[1:], 1):
        ans_map = extract_answers(sec)
        # 패턴: "0N\t문제" 또는 "0N 문제"
        q_pat = re.compile(
            r'(?:^|\n)(\d{2})\s+(.+?)(?=\n\d{2}\s|\n정답|$)',
            re.DOTALL
        )
        cp = re.compile(r'([①②③④①②③④])\s*(.+?)(?=[①②③④①②③④]|$)', re.DOTALL)

        for m in q_pat.finditer(sec):
            qno = int(m.group(1))
            if qno < 1 or qno > 20:
                continue
            raw = m.group(2).strip()
            choices_raw = cp.findall(raw)
            if len(choices_raw) < 4:
                continue
            choices = [c[1].strip().replace('\n', ' ')[:120] for c in choices_raw[:4]]
            q_text = raw
            for ch in '①②③④①②③④':
                idx = q_text.find(ch)
                if idx != -1:
                    q_text = q_text[:idx].strip()
                    break
            q_text = q_text.replace('\n', ' ').strip()
            if len(q_text) < 5:
                continue
            ans = ans_map.get(qno, -1)
            if ans == -1:
                continue
            questions.append({
                'source': f'이기적_예상{si}',
                'q': q_text,
                'choices': choices,
                'answer': ans
            })

    # 기출복원문제 파싱
    kichul_idx = full.rfind('2026년 제1회 기출복원문제')
    if kichul_idx > 0:
        kblock = full[kichul_idx-5000:kichul_idx]  # 기출 문제는 앞쪽에
        # 기출복원문제 섹션 찾기
        kichul_q_start = full.find('기출복원문제\n')
        if kichul_q_start > 0:
            kblock2 = full[kichul_q_start-30000:kichul_q_start]
            ans_map2 = extract_answers(full[kichul_idx:kichul_idx+5000])
            q_pat2 = re.compile(
                r'(?:^|\n)(\d{2})\s+(.+?)(?=\n\d{2}\s|\n정답|$)',
                re.DOTALL
            )
            cp2 = re.compile(r'([①②③④①②③④])\s*(.+?)(?=[①②③④①②③④]|$)', re.DOTALL)
            for m in q_pat2.finditer(kblock2[-8000:]):
                qno = int(m.group(1))
                if qno < 1 or qno > 60:
                    continue
                raw = m.group(2).strip()
                choices_raw = cp2.findall(raw)
                if len(choices_raw) < 4:
                    continue
                choices = [c[1].strip().replace('\n', ' ')[:120] for c in choices_raw[:4]]
                q_text = raw
                for ch in '①②③④①②③④':
                    idx = q_text.find(ch)
                    if idx != -1:
                        q_text = q_text[:idx].strip()
                        break
                q_text = q_text.replace('\n', ' ').strip()
                if len(q_text) < 5:
                    continue
                ans = ans_map2.get(qno, -1)
                if ans == -1:
                    continue
                questions.append({
                    'source': '이기적_기출2026',
                    'q': q_text,
                    'choices': choices,
                    'answer': ans
                })

    print(f'이기적 추출: {len(questions)}개', file=sys.stderr)
    return questions


# ──────────────────────────────────────────────
# 중복 제거 (문제 텍스트 앞 30자 기준)
# ──────────────────────────────────────────────
def dedup(qs):
    seen = set()
    out = []
    for q in qs:
        key = q['q'][:30]
        if key not in seen:
            seen.add(key)
            out.append(q)
    return out


if __name__ == '__main__':
    base = 'c:/Users/3class_013/Desktop/프로그래밍기능사/'
    qs1 = parse_sinagong(base + '2026시나공_프로그래밍기능사필기_최종점검모의고사.pdf')
    qs2 = parse_ikjeok(base + '2026 이기적 프로그래밍기능사 필기 기본서(기출분석자료).pdf')

    all_qs = dedup(qs1 + qs2)
    print(f'총 {len(all_qs)}개 문제 추출', file=sys.stderr)

    out_path = base + 'questions.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_qs, f, ensure_ascii=False, indent=2)
    print(f'저장 완료: {out_path}', file=sys.stderr)
    print(f'TOTAL:{len(all_qs)}')
