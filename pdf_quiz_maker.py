"""
PDF 퀴즈 자동 생성기
====================
사용법:
  1. 이 파일(.py)을 더블클릭하면 GUI 창이 열립니다.
  2. PDF 파일을 여러 개 선택하세요 (프로그래밍기능사 형식 권장).
  3. "퀴즈 생성" 버튼을 누르면 quiz_from_pdf.html 이 생성됩니다.
  4. 생성된 HTML 파일을 더블클릭해서 브라우저로 열면 랜덤 퀴즈!

지원 형식:
  - 시나공: "1. 질문\n① A\n② B\n③ C\n④ D" + "정답: 1.② ..."
  - 이기적: "01 질문\n① A\n② B\n③ C\n④ D" + "정답  01 ③ ..."
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading, json, os, re, fitz

# ── 파서 ───────────────────────────────────────
CIRC = {'①':0,'②':1,'③':2,'④':3}
def norm(c):
    for k,v in CIRC.items():
        if c == k: return v
    return -1

def parse_pdf(path, status_cb=None):
    doc = fitz.open(path)
    full = ''.join(doc[i].get_text() for i in range(doc.page_count))
    fname = os.path.basename(path)
    if status_cb: status_cb(f"읽는 중: {fname} ({doc.page_count}쪽)")

    questions = []

    # ── 시나공 스타일 (N. 문제) ──────────────────
    # 회차 분리 시도
    rounds = re.split(r'(\d)회\s+최종점검\s*모의고사', full)
    if len(rounds) > 2:
        for ri in range(1, len(rounds), 2):
            rno = rounds[ri]
            block = rounds[ri+1] if ri+1 < len(rounds) else ''
            # 정답 수집
            amap = {}
            for m in re.finditer(r'정답\s*:\s*((?:\d+\.[①②③④]\s*)+)', block):
                for am in re.finditer(r'(\d+)\.([①②③④])', m.group(1)):
                    amap[int(am.group(1))] = norm(am.group(2))
            # 문제 수집
            _extract_numbered(block, amap, f'{fname} {rno}회', questions)

    # ── 이기적 스타일 (0N 문제) ──────────────────
    # 예상문제 섹션 분리
    parts = re.split(r'합격을 다지는\n?예상문제', full)
    for pi, part in enumerate(parts[1:], 1):
        amap = {}
        for m in re.finditer(r'정답\s+((?:\d{2}\s+[①②③④]\s*){1,20})', part):
            for am in re.finditer(r'(\d{2})\s+([①②③④])', m.group(1)):
                amap[int(am.group(1))] = norm(am.group(2))
        _extract_zero_padded(part, amap, f'{fname} 예상{pi}', questions)

    # ── 기출복원문제 ─────────────────────────────
    kichi = full.find('기출복원문제')
    if kichi > 0:
        kblock = full[max(0,kichi-30000):kichi]
        amap = {}
        for m in re.finditer(r'정답\s+((?:\d{2}\s+[①②③④]\s*){1,60})', full[kichi:kichi+8000]):
            for am in re.finditer(r'(\d{2})\s+([①②③④])', m.group(1)):
                amap[int(am.group(1))] = norm(am.group(2))
        _extract_zero_padded(kblock[-10000:], amap, f'{fname} 기출', questions)

    if status_cb: status_cb(f"추출 완료: {fname} → {len(questions)}문제")
    return questions


def _extract_numbered(text, amap, src, out):
    """시나공 스타일: '1. 문제\n① ...' """
    cp = re.compile(r'([①②③④])\s*(.+?)(?=[①②③④]|$)', re.DOTALL)
    pat = re.compile(r'(?<!\d)(\d{1,2})\.\s+(.+?)(?=\n\d{1,2}\.\s|\n정답|$)', re.DOTALL)
    for m in pat.finditer(text):
        qno = int(m.group(1))
        if not (1 <= qno <= 60): continue
        raw = m.group(2).strip()
        found = cp.findall(raw)
        if len(found) < 4: continue
        choices = [c[1].strip().replace('\n',' ')[:150] for c in found[:4]]
        qtxt = raw
        for ch in '①②③④':
            i = qtxt.find(ch)
            if i != -1: qtxt = qtxt[:i].strip(); break
        qtxt = qtxt.replace('\n',' ').strip()
        if len(qtxt) < 5: continue
        ans = amap.get(qno, -1)
        if ans == -1: continue
        out.append({'source': src, 'q': qtxt, 'choices': choices, 'answer': ans})


def _extract_zero_padded(text, amap, src, out):
    """이기적 스타일: '01 문제\n① ...' """
    cp = re.compile(r'([①②③④])\s*(.+?)(?=[①②③④]|$)', re.DOTALL)
    pat = re.compile(r'(?:^|\n)(\d{2})\s+(.+?)(?=\n\d{2}\s|\n정답|$)', re.DOTALL)
    for m in pat.finditer(text):
        qno = int(m.group(1))
        if not (1 <= qno <= 60): continue
        raw = m.group(2).strip()
        found = cp.findall(raw)
        if len(found) < 4: continue
        choices = [c[1].strip().replace('\n',' ')[:150] for c in found[:4]]
        qtxt = raw
        for ch in '①②③④':
            i = qtxt.find(ch)
            if i != -1: qtxt = qtxt[:i].strip(); break
        qtxt = qtxt.replace('\n',' ').strip()
        if len(qtxt) < 5: continue
        ans = amap.get(qno, -1)
        if ans == -1: continue
        out.append({'source': src, 'q': qtxt, 'choices': choices, 'answer': ans})


def dedup(qs):
    seen, out = set(), []
    for q in qs:
        k = q['q'][:35]
        if k not in seen:
            seen.add(k); out.append(q)
    return out


# ── HTML 생성 ───────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PDF 랜덤 퀴즈</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Malgun Gothic",sans-serif;background:#f0f2f5;color:#222}
header{background:linear-gradient(135deg,#1a73e8,#0d47a1);color:#fff;
  padding:16px 22px;display:flex;justify-content:space-between;align-items:center;
  position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,.3)}
header h1{font-size:1.1rem}header p{font-size:.75rem;opacity:.8;margin-top:3px}
#sb{display:flex;gap:14px}
.si{text-align:center}.sn{font-size:1.3rem;font-weight:700}.sl{font-size:.7rem;opacity:.85}
.pw{background:rgba(255,255,255,.25);height:5px;border-radius:3px;margin-top:7px}
.pb{height:5px;background:#fff;border-radius:3px;transition:width .4s}
main{max-width:860px;margin:24px auto;padding:0 12px 60px}
.qc{background:#fff;border-radius:12px;padding:18px 20px;margin-bottom:12px;
  box-shadow:0 1px 4px rgba(0,0,0,.08)}
.qh{display:flex;gap:9px;align-items:flex-start;margin-bottom:10px}
.qn{background:#1a73e8;color:#fff;border-radius:50%;min-width:24px;height:24px;
  display:flex;align-items:center;justify-content:center;font-size:.75rem;font-weight:700;flex-shrink:0}
.qt{font-size:.93rem;line-height:1.65;white-space:pre-wrap}
.chs{display:grid;grid-template-columns:1fr 1fr;gap:7px}
@media(max-width:480px){.chs{grid-template-columns:1fr}}
.cb{background:#f8f9fa;border:2px solid #e0e0e0;border-radius:8px;padding:8px 12px;
  text-align:left;cursor:pointer;font-size:.86rem;font-family:inherit;
  transition:all .15s;display:flex;align-items:center;gap:6px;line-height:1.4}
.cb:hover:not(:disabled){background:#e8f0fe;border-color:#1a73e8}
.cn{background:#e0e0e0;color:#444;border-radius:50%;min-width:20px;height:20px;
  display:flex;align-items:center;justify-content:center;font-size:.73rem;font-weight:700;flex-shrink:0}
.cb.ok{background:#e6f4ea;border-color:#34a853}.cb.ok .cn{background:#34a853;color:#fff}
.cb.ng{background:#fce8e6;border-color:#ea4335}.cb.ng .cn{background:#ea4335;color:#fff}
.cb.rv{background:#e6f4ea;border-color:#34a853;opacity:.7}.cb.rv .cn{background:#34a853;color:#fff}
.cb:disabled{cursor:default}
.rm{margin-top:8px;font-size:.83rem;font-weight:700;display:none}
.rm.show{display:block}.rm.ok{color:#34a853}.rm.ng{color:#ea4335}
.src{font-size:.7rem;color:#bbb;margin-top:5px}
#nbtn{display:block;margin:32px auto 0;background:#1a73e8;color:#fff;border:none;
  border-radius:10px;padding:13px 34px;font-size:.97rem;font-family:inherit;cursor:pointer}
#nbtn:hover{background:#1558b0}
#modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:200;
  align-items:center;justify-content:center}
#modal.show{display:flex}
.mb{background:#fff;border-radius:16px;padding:34px 42px;text-align:center;
  max-width:320px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,.3)}
.mb h2{font-size:1.35rem;margin-bottom:5px}
.ms{font-size:2.7rem;font-weight:700;color:#1a73e8;margin:12px 0}
.mb p{color:#555;font-size:.9rem;margin-bottom:18px}
.mbs{display:flex;gap:9px;justify-content:center}
.mbt{background:#1a73e8;color:#fff;border:none;border-radius:8px;padding:10px 26px;
  font-size:.92rem;font-family:inherit;cursor:pointer}
.mbt.ol{background:#fff;color:#1a73e8;border:2px solid #1a73e8}
</style>
</head>
<body>
<header>
  <div>
    <h1>PDF 랜덤 모의고사</h1>
    <p id="ri">로딩 중...</p>
    <div class="pw"><div class="pb" id="pb" style="width:0%"></div></div>
  </div>
  <div id="sb">
    <div class="si"><div class="sn" id="sa">0</div><div class="sl">푼 문제</div></div>
    <div class="si"><div class="sn" id="so">0</div><div class="sl">정답</div></div>
    <div class="si"><div class="sn" id="sn2">0</div><div class="sl">오답</div></div>
  </div>
</header>
<main id="quiz"></main>
<div id="modal">
  <div class="mb">
    <h2>시험 완료!</h2>
    <div class="ms" id="msc"></div>
    <p id="mmg"></p>
    <div class="mbs">
      <button class="mbt ol" onclick="closeM()">결과 보기</button>
      <button class="mbt" onclick="startNew()">새 문제 뽑기</button>
    </div>
  </div>
</div>
<script>
const AQ=__DATA__;
let cur=[],ans=0,ok=0,ng=0,rn=0;
function p60(){const a=[...AQ];for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a.slice(0,Math.min(60,a.length));}
function e(s){return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}
function render(qs){
  const C=document.getElementById("quiz");C.innerHTML="";
  const N=["①","②","③","④"];
  qs.forEach((q,i)=>{
    const d=document.createElement("div");d.className="qc";d.id="qc"+i;
    d.innerHTML=`<div class="qh"><div class="qn">${i+1}</div><div class="qt">${e(q.q)}</div></div><div class="chs" id="c${i}"></div><div class="rm" id="m${i}"></div><div class="src">[${e(q.source)}]</div>`;
    C.appendChild(d);
    const ch=d.querySelector("#c"+i);
    q.choices.forEach((c,ci)=>{
      const b=document.createElement("button");b.className="cb";
      b.innerHTML=`<span class="cn">${N[ci]}</span>${e(c)}`;
      b.onclick=()=>sel(i,ci);ch.appendChild(b);
    });
  });
  C.insertAdjacentHTML("beforeend","<button id='nbtn' onclick='startNew()'>새 문제 뽑기</button>");
}
function sel(qi,ch){
  const bs=document.querySelectorAll("#c"+qi+" .cb");
  bs.forEach(b=>b.disabled=true);
  const a=cur[qi].answer,m=document.getElementById("m"+qi);
  bs[ch].classList.add(ch===a?"ok":"ng");
  if(ch!==a)bs[a].classList.add("rv");
  m.classList.add("show");
  if(ch===a){m.textContent="✔ 정답!";m.classList.add("ok");ok++;}
  else{m.textContent="✘ 오답! 정답은 "+["①","②","③","④"][a]+"번";m.classList.add("ng");ng++;}
  ans++;upd();if(ans===cur.length)setTimeout(showM,500);
}
function upd(){
  document.getElementById("sa").textContent=ans;
  document.getElementById("so").textContent=ok;
  document.getElementById("sn2").textContent=ng;
  document.getElementById("pb").style.width=(ans/cur.length*100)+"%";
}
function showM(){
  const p=Math.round(ok/cur.length*100);
  document.getElementById("msc").textContent=ok+" / "+cur.length+" ("+p+"%)";
  document.getElementById("mmg").textContent=p>=80?"합격권입니다! 훌륭해요!":p>=60?"조금만 더 노력하면 합격!":"취약 부분을 집중 복습해 보세요!";
  document.getElementById("modal").classList.add("show");
}
function closeM(){document.getElementById("modal").classList.remove("show");}
function startNew(){
  closeM();ans=0;ok=0;ng=0;rn++;
  document.getElementById("ri").textContent="전체 "+AQ.length+"문제 중 랜덤 "+Math.min(60,AQ.length)+"문제 ("+rn+"회차)";
  upd();cur=p60();render(cur);window.scrollTo({top:0,behavior:"smooth"});
}
startNew();
</script>
</body>
</html>"""


# ── GUI ────────────────────────────────────────
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('PDF 랜덤 퀴즈 생성기')
        self.root.geometry('580x440')
        self.root.resizable(False, False)

        tk.Label(self.root, text='PDF 랜덤 퀴즈 생성기',
                 font=('맑은 고딕', 14, 'bold'), pady=14).pack()

        tk.Label(self.root,
                 text='① PDF 파일을 추가하세요 (여러 개 가능)\n'
                      '② "퀴즈 생성" 버튼을 누르면 HTML 파일이 만들어집니다\n'
                      '③ 생성된 HTML을 더블클릭해서 브라우저로 열면 끝!',
                 justify='left', fg='#555', font=('맑은 고딕', 9), padx=16).pack(anchor='w')

        frm = tk.Frame(self.root); frm.pack(fill='both', expand=True, padx=14, pady=8)
        self.lb = tk.Listbox(frm, font=('맑은 고딕', 10), height=8)
        sb = tk.Scrollbar(frm, command=self.lb.yview)
        self.lb.config(yscrollcommand=sb.set)
        self.lb.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        btn_frm = tk.Frame(self.root); btn_frm.pack(fill='x', padx=14)
        tk.Button(btn_frm, text='PDF 추가', command=self.add_files,
                  bg='#1a73e8', fg='white', font=('맑은 고딕', 10),
                  padx=12, pady=5).pack(side='left', padx=4)
        tk.Button(btn_frm, text='선택 삭제', command=self.remove_sel,
                  font=('맑은 고딕', 10), padx=12, pady=5).pack(side='left', padx=4)
        tk.Button(btn_frm, text='전체 삭제', command=lambda: self.lb.delete(0,'end'),
                  font=('맑은 고딕', 10), padx=12, pady=5).pack(side='left', padx=4)
        tk.Button(btn_frm, text='퀴즈 생성 ▶', command=self.run,
                  bg='#34a853', fg='white', font=('맑은 고딕', 11, 'bold'),
                  padx=16, pady=6).pack(side='right', padx=4)

        self.status = tk.StringVar(value='PDF 파일을 추가하세요.')
        tk.Label(self.root, textvariable=self.status,
                 font=('맑은 고딕', 9), fg='#555',
                 wraplength=540).pack(pady=8)

        self.prog = ttk.Progressbar(self.root, length=540, mode='indeterminate')
        self.prog.pack(pady=4)

        self.root.mainloop()

    def add_files(self):
        files = filedialog.askopenfilenames(
            title='PDF 파일 선택',
            filetypes=[('PDF 파일', '*.pdf'), ('모든 파일', '*.*')])
        for f in files:
            if f not in self.lb.get(0, 'end'):
                self.lb.insert('end', f)
        self.status.set(f'{self.lb.size()}개 파일 선택됨')

    def remove_sel(self):
        for i in reversed(self.lb.curselection()):
            self.lb.delete(i)

    def run(self):
        files = list(self.lb.get(0, 'end'))
        if not files:
            messagebox.showwarning('경고', 'PDF 파일을 먼저 추가하세요!')
            return
        self.prog.start(10)
        threading.Thread(target=self._gen, args=(files,), daemon=True).start()

    def _gen(self, files):
        try:
            all_qs = []
            for f in files:
                qs = parse_pdf(f, lambda s: self.status.set(s))
                all_qs.extend(qs)

            all_qs = dedup(all_qs)
            self.status.set(f'총 {len(all_qs)}문제 추출 완료. HTML 생성 중...')

            if len(all_qs) < 10:
                self.root.after(0, lambda: messagebox.showerror(
                    '오류', f'추출된 문제가 {len(all_qs)}개뿐입니다.\n'
                            '지원하는 형식(시나공/이기적)의 PDF인지 확인하세요.'))
                return

            qs_json = json.dumps(all_qs, ensure_ascii=False)
            html = HTML.replace('__DATA__', qs_json)

            save_dir = os.path.dirname(files[0])
            out = os.path.join(save_dir, 'quiz_from_pdf.html')
            with open(out, 'w', encoding='utf-8') as f:
                f.write(html)

            self.status.set(f'✔ 완료! {len(all_qs)}문제 → {out}')
            self.root.after(0, lambda: messagebox.showinfo(
                '생성 완료',
                f'총 {len(all_qs)}문제가 추출되었습니다.\n\n'
                f'파일: {out}\n\n'
                f'이 파일을 더블클릭해서 브라우저로 여세요!'))
            os.startfile(out)
        except Exception as ex:
            self.root.after(0, lambda: messagebox.showerror('오류', str(ex)))
        finally:
            self.root.after(0, self.prog.stop)


if __name__ == '__main__':
    # fitz(PyMuPDF) 없으면 안내
    try:
        import fitz
    except ImportError:
        root = tk.Tk(); root.withdraw()
        messagebox.showerror('라이브러리 오류',
            'PyMuPDF가 설치되지 않았습니다.\n\n'
            '명령 프롬프트에서 다음을 실행하세요:\n'
            'pip install pymupdf')
        raise SystemExit

    App()
