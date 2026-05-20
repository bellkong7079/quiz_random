import fitz, sys, re
sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r'C:\Users\jb733\OneDrive\바탕 화면\quiz\quiz_random\22년_정보처리산업기사_필기_기출문제\2022년1회_산업기사 필기 기출문제.pdf'
doc = fitz.open(pdf_path)
full = ''.join(doc[i].get_text() for i in range(doc.page_count))

CP = re.compile(r'([①②③④])\s*(.+?)(?=[①②③④]|$)', re.DOTALL)

pat = re.compile(
    r'(?:^|\n)(\d{1,2})(?:[\.\s]\s*)(.+?)(?=\n\d{1,2}[\.\s]|\n정답|\Z)',
    re.DOTALL)

print('=== 처음 5개 문제 파싱 ===')
count = 0
for m in pat.finditer(full):
    qno = int(m.group(1))
    if not (1 <= qno <= 60):
        continue
    raw = m.group(2).strip()
    found = CP.findall(raw)
    if len(found) < 4:
        continue
    choices = [c[1].strip().replace('\n',' ')[:80] for c in found[:4]]
    qtxt = raw
    for ch in '①②③④':
        i = qtxt.find(ch)
        if i != -1: qtxt = qtxt[:i].strip(); break
    qtxt = qtxt.replace('\n', ' ').strip()
    print(f'Q{qno}: {qtxt[:60]}')
    for ci, ch in enumerate(choices):
        print(f'  {["①","②","③","④"][ci]}: "{ch[:50]}"')
    count += 1
    if count >= 5:
        break
