"""
PDF 랜덤 퀴즈 생성기
====================
사용법:
  이 파일을 더블클릭 → PDF 추가 → 퀴즈 생성

지원 형식 (자동 감지):
  ① 시나공  : "1. 문제\n① A\n② B\n③ C\n④ D"  + 정답: 1.② ...
  ② 이기적  : "01 문제\n① A\n② B\n③ C\n④ D"  + 정답  01 ③ ...
  ③ 일반형  : "1. 문제\n① A\n② B\n③ C\n④ D"  (정답 없어도 추출)
  ④ 기출문제: 번호 + ①②③④ 보기 패턴 있으면 대부분 인식

핵심 조건: ①②③④ 보기가 있는 객관식이면 어떤 책이든 OK
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading, json, os, re, fitz, base64

# ══════════════════════════════════════════════
# 코드 포맷팅
# ══════════════════════════════════════════════
def get_page_images(page):
    """페이지에서 이미지 추출 (작은 장식용 이미지 제외)"""
    images = []
    try:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block.get("type") != 1:
                continue
            x0, y0, x1, y1 = block["bbox"]
            w, h = x1 - x0, y1 - y0
            if w < 80 or h < 80:
                continue
            img_bytes = block.get("image")
            if not img_bytes:
                continue
            ext = block.get("ext", "png")
            b64 = base64.b64encode(img_bytes).decode()
            images.append({'y': y0, 'data': f'data:image/{ext};base64,{b64}'})
    except Exception:
        pass
    return images

def reformat_java(code):
    out=[]; indent=0; i=0; code=code.strip(); n=len(code)
    while i<n:
        c=code[i]
        if c=='{':
            out.append(' {'); indent+=1
            out.append('\n'+'    '*indent)
            while i+1<n and code[i+1]==' ': i+=1
        elif c=='}':
            while out and out[-1]==' ': out.pop()
            indent=max(0,indent-1)
            out.append('\n'+'    '*indent+'}')
        elif c==';':
            out.append(';')
            j=i+1
            while j<n and code[j]==' ': j+=1
            if j<n and code[j] not in '}':
                out.append('\n'+'    '*indent); i=j-1
        else: out.append(c)
        i+=1
    return re.sub(r'\n{3,}','\n\n',''.join(out).strip())

def reformat_python(code):
    if '\n' in code and code.count('\n')>2: return code
    for kw in ['def ','return ','for ','while ','if ','elif ','else:',
               'try:','except','finally:','print(']:
        code=re.sub(r'(?<!\n)(?<!\A)('+re.escape(kw)+r')',r'\n\1',code)
    # 메서드 호출 앞에 줄바꿈 (예: fruits.remove( → \nfruits.remove()
    code=re.sub(r'\)\s+(\w+[\.\[])',r')\n\1',code)
    lines=[l.strip() for l in code.split('\n') if l.strip()]
    out=[]; indent=0
    for l in lines:
        if re.match(r'(else:|elif |except.*:|finally:)',l):
            indent=max(0,indent-1)
            out.append('    '*indent+l)
            indent+=1
        elif re.match(r'(def |class |for |while |if |try:)',l):
            out.append('    '*indent+l)
            if l.endswith(':'): indent+=1
        else:
            out.append('    '*indent+l)
    return '\n'.join(out)

def reformat_sql(code):
    for kw in ['SELECT','FROM','WHERE','ORDER BY','GROUP BY','HAVING',
               'INSERT INTO','VALUES','UPDATE','SET','DELETE FROM',
               'CREATE TABLE','DROP TABLE','ALTER TABLE']:
        code=re.sub(r'\s+('+re.escape(kw)+r')\s+',r'\n\1 ',code,flags=re.IGNORECASE)
    return code.strip()

def split_code(qtxt):
    java=re.search(r'(public\s+class\s+\w+|public\s+static\s+void\s+main|System\.out\.)',qtxt)
    py=re.search(r'(def\s+\w+\s*\(|print\s*\(|for\s+\w+\s+in\s+range|'
                 r'try\s*:|except.*:|finally\s*:|'
                 r'\w+\s*=\s*[\[\{]|'
                 r'\w+\.\w+\s*\()',qtxt)
    sql=re.search(r'(?i)(SELECT\s+[\w\*]|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM)',qtxt)
    cands=[(m,l) for m,l in [(java,'java'),(py,'python'),(sql,'sql')] if m]
    if not cands: return qtxt.strip(),'',''
    best,lang=min(cands,key=lambda x:x[0].start())
    desc=qtxt[:best.start()].strip()
    raw=qtxt[best.start():].strip()
    code=reformat_java(raw) if lang=='java' else reformat_python(raw) if lang=='python' else reformat_sql(raw)
    return desc,code,lang

# ══════════════════════════════════════════════
# 정답 추출 (여러 패턴 지원)
# ══════════════════════════════════════════════
def norm(c):
    return {'①':0,'②':1,'③':2,'④':3}.get(c,-1)

def extract_answers(text):
    amap={}
    # 패턴1: 시나공  "정답 : 1.② 2.③ ..."
    for m in re.finditer(r'정답\s*:\s*((?:\d+\.[①②③④]\s*)+)',text):
        for am in re.finditer(r'(\d+)\.([①②③④])',m.group(1)):
            amap[int(am.group(1))]=norm(am.group(2))
    # 패턴2: 이기적  "정답  01 ③  02 ④ ..."
    for m in re.finditer(r'정답\s+((?:\d{2}\s+[①②③④]\s*){1,60})',text):
        for am in re.finditer(r'(\d{2})\s+([①②③④])',m.group(1)):
            amap[int(am.group(1))]=norm(am.group(2))
    # 패턴3: 기출/모의고사 "1 ① 2 ③ ..." (정답표 한 줄)
    for m in re.finditer(r'(?:정\s*답|답\s*안)\s*((?:\d+[\s\.]+[①②③④①②③④]\s*){3,})',text):
        for am in re.finditer(r'(\d+)[\s\.]+([①②③④①②③④])',m.group(1)):
            amap[int(am.group(1))]=norm(am.group(2))
    # 패턴4: "01 ①  02 ②  03 ③ ..." (번호+동그라미 반복)
    rows=re.findall(r'(\d{1,2})\s+([①②③④①②③④])',text)
    if len(rows)>=5:
        for qno,ans in rows:
            n=norm(ans)
            if n>=0 and int(qno) not in amap:
                amap[int(qno)]=n
    return amap

# ══════════════════════════════════════════════
# 핵심 파서 — 어떤 PDF든 ①②③④ 있으면 추출
# ══════════════════════════════════════════════
CP=re.compile(r'([①②③④])\s*(.+?)(?=[①②③④]|$)',re.DOTALL)

def extract_from_block(text, amap, src):
    """하나의 텍스트 블록에서 문제 추출"""
    questions=[]
    # 문제 번호 패턴: "1." / "01" / "1 " 앞 번호
    pat=re.compile(
        r'(?:^|\n)(\d{1,2})(?:[\.\s]\s*)(.+?)(?=\n\d{1,2}[\.\s]|\n정답|\Z)',
        re.DOTALL)
    for m in pat.finditer(text):
        qno=int(m.group(1))
        if not (1<=qno<=60): continue
        raw=m.group(2).strip()
        found=CP.findall(raw)
        if len(found)<4: continue
        choices=[c[1].strip().replace('\n',' ')[:200] for c in found[:4]]
        # 보기 이전 = 문제 텍스트
        qtxt=raw
        for ch in '①②③④':
            i=qtxt.find(ch)
            if i!=-1: qtxt=qtxt[:i].strip(); break
        qtxt=qtxt.replace('\n',' ').strip()
        if len(qtxt)<5: continue

        ans=amap.get(qno,-1)
        desc,code,lang=split_code(qtxt)
        questions.append({
            'source':src,'q':desc,'code':code,'lang':lang,
            'choices':choices,'answer':ans,'explanation':''
        })
    return questions

# ══════════════════════════════════════════════
# 해설 추출 (시나공 형식)
# ══════════════════════════════════════════════
def extract_explanations(text):
    exp_map={}
    # 시나공: "N회 ... 해설\n1 해설내용\n2 해설내용..."
    parts=re.split(r'\d회[^\n]*해설',text)
    for part in parts[1:]:
        exp_pat=re.compile(r'(?:^|\n)(\d{1,2})\s+(.+?)(?=\n\d{1,2}\s|\n\d{3}\n|\Z)',re.DOTALL)
        for m in exp_pat.finditer(part):
            qno=int(m.group(1))
            if not (1<=qno<=60): continue
            raw=m.group(2).strip()
            raw=raw.replace('\x07','').replace('\t',' ')
            raw=re.sub(r'\s+',' ',raw).strip()
            raw=re.sub(r'•\s*','\n• ',raw)
            raw=re.sub(r'[❶❷❸❹❺❻❼❽]','',raw).strip()
            if len(raw)>10: exp_map[qno]=raw
    return exp_map

# ══════════════════════════════════════════════
# 메인 파서
# ══════════════════════════════════════════════
def parse_pdf(path, status_cb=None):
    doc=fitz.open(path)
    fname=os.path.basename(path)
    if status_cb: status_cb(f'읽는 중: {fname} ({doc.page_count}쪽)')

    # 페이지별 텍스트 + 이미지 추출
    page_data = []
    for i in range(doc.page_count):
        page = doc[i]
        page_data.append({'text': page.get_text(), 'images': get_page_images(page)})

    full=''.join(p['text'] for p in page_data)

    questions=[]
    # 해설 추출
    exp_global=extract_explanations(full)

    # ── 전략1: 회차별 분리 (시나공) ──────────────
    rounds=re.split(r'(\d)회[^\n]*모의고사',full)
    if len(rounds)>3:
        for ri in range(1,len(rounds),2):
            rno=int(rounds[ri])
            block=rounds[ri+1] if ri+1<len(rounds) else ''
            amap=extract_answers(block)
            qs=extract_from_block(block,amap,f'{fname} {rno}회')
            for q in qs:
                q['explanation']=exp_global.get(
                    list(exp_global.keys())[0] if exp_global else 0,'')
            questions.extend(qs)
        if status_cb: status_cb(f'  회차별 추출: {len(questions)}문제')

    # ── 전략2: 예상문제 섹션별 (이기적) ──────────
    parts=re.split(r'합격을 다지는\n?예상문제',full)
    if len(parts)>1:
        for pi,part in enumerate(parts[1:],1):
            amap=extract_answers(part)
            qs=extract_from_block(part,amap,f'{fname} 예상{pi}')
            questions.extend(qs)
        if status_cb: status_cb(f'  예상문제 추출 포함: {len(questions)}문제')

    # ── 전략3: 전체 텍스트 통합 파싱 (기타 PDF) ──
    if len(questions)<10:
        if status_cb: status_cb(f'  일반 형식으로 재시도...')
        amap=extract_answers(full)
        qs=extract_from_block(full,amap,fname)
        questions.extend(qs)
        if status_cb: status_cb(f'  일반 추출: {len(qs)}문제')

    # 해설 매칭 (시나공 형식)
    if exp_global:
        # 회차별로 해설 다시 매칭
        exp_by_round={}
        exp_parts=re.split(r'(\d)회[^\n]*해설',full)
        for ei in range(1,len(exp_parts),2):
            rno=int(exp_parts[ei])
            eblock=exp_parts[ei+1] if ei+1<len(exp_parts) else ''
            exp_by_round[rno]=extract_explanations_from_block(eblock)

        for q in questions:
            # 소스에서 회차 번호 추출
            rm=re.search(r'(\d)회',q['source'])
            if rm:
                rno=int(rm.group(1))
                # 문제 번호는 소스 내 순서로 추정 (간단히 전역 exp_global 사용)
                pass

    # 이미지가 있는 페이지와 문제 연결
    pages_with_images = [(p['text'], p['images']) for p in page_data if p['images']]
    for q in questions:
        snippet = q['q'][:25]
        for page_text, imgs in pages_with_images:
            if snippet in page_text:
                q['image'] = imgs[0]['data']
                break

    if status_cb: status_cb(f'완료: {fname} → {len(questions)}문제 추출')
    return questions

def extract_explanations_from_block(text):
    exp_map={}
    pat=re.compile(r'(?:^|\n)(\d{1,2})\s+(.+?)(?=\n\d{1,2}\s|\Z)',re.DOTALL)
    for m in pat.finditer(text):
        qno=int(m.group(1))
        if not (1<=qno<=60): continue
        raw=m.group(2).strip().replace('\x07','').replace('\t',' ')
        raw=re.sub(r'\s+',' ',raw).strip()
        raw=re.sub(r'[❶❷❸❹❺❻❼❽]','',raw).strip()
        if len(raw)>10: exp_map[qno]=raw
    return exp_map

def dedup(qs):
    seen,out=set(),[]
    for q in qs:
        k=q['q'][:35]
        if k not in seen: seen.add(k); out.append(q)
    return out

# ══════════════════════════════════════════════
# HTML 템플릿
# ══════════════════════════════════════════════
HTML_TEMPLATE=r"""<!DOCTYPE html>
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
#sb{display:flex;gap:14px}.si{text-align:center}
.sn{font-size:1.3rem;font-weight:700}.sl{font-size:.7rem;opacity:.85}
.pw{background:rgba(255,255,255,.25);height:5px;border-radius:3px;margin-top:7px}
.pb{height:5px;background:#fff;border-radius:3px;transition:width .4s}
main{max-width:860px;margin:24px auto;padding:0 12px 60px}
.qc{background:#fff;border-radius:12px;padding:18px 20px;margin-bottom:12px;
  box-shadow:0 1px 4px rgba(0,0,0,.08)}
.qh{display:flex;gap:9px;align-items:flex-start;margin-bottom:10px}
.qn{background:#1a73e8;color:#fff;border-radius:50%;min-width:24px;height:24px;
  display:flex;align-items:center;justify-content:center;font-size:.75rem;font-weight:700;flex-shrink:0}
.qt{font-size:.93rem;line-height:1.65}
pre.cb{background:#1e1e2e;color:#cdd6f4;padding:13px 16px;border-radius:8px;
  font-size:.84rem;font-family:Consolas,"Courier New",monospace;
  line-height:1.6;margin:10px 0 13px;overflow-x:auto;white-space:pre}
pre.cb.sql{background:#1a2a1a;color:#a8d8a8}
.chs{display:grid;grid-template-columns:1fr 1fr;gap:7px}
@media(max-width:480px){.chs{grid-template-columns:1fr}}
.ch{background:#f8f9fa;border:2px solid #e0e0e0;border-radius:8px;padding:9px 12px;
  text-align:left;cursor:pointer;font-size:.87rem;font-family:inherit;
  transition:all .15s;display:flex;align-items:center;gap:7px;line-height:1.4}
.ch:hover:not(:disabled){background:#e8f0fe;border-color:#1a73e8}
.cn{background:#e0e0e0;color:#444;border-radius:50%;min-width:20px;height:20px;
  display:flex;align-items:center;justify-content:center;font-size:.73rem;font-weight:700;flex-shrink:0}
.ch.ok{background:#e6f4ea;border-color:#34a853}.ch.ok .cn{background:#34a853;color:#fff}
.ch.ng{background:#fce8e6;border-color:#ea4335}.ch.ng .cn{background:#ea4335;color:#fff}
.ch.rv{background:#e6f4ea;border-color:#34a853;opacity:.75}.ch.rv .cn{background:#34a853;color:#fff}
.ch:disabled{cursor:default}
.ra{margin-top:11px;display:none}.ra.show{display:block}
.rl{font-size:.9rem;font-weight:700;margin-bottom:8px}
.rl.ok{color:#34a853}.rl.ng{color:#ea4335}
.eb{background:#f0f4ff;border-left:4px solid #1a73e8;border-radius:0 8px 8px 0;
  padding:12px 15px;font-size:.87rem;line-height:1.7;color:#333;white-space:pre-wrap}
.src{font-size:.7rem;color:#bbb;margin-top:7px}
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
  <div><h1>PDF 랜덤 퀴즈</h1><p id="ri">로딩 중...</p>
  <div class="pw"><div class="pb" id="pb" style="width:0%"></div></div></div>
  <div id="sb">
    <div class="si"><div class="sn" id="sa">0</div><div class="sl">푼 문제</div></div>
    <div class="si"><div class="sn" id="so">0</div><div class="sl">정답</div></div>
    <div class="si"><div class="sn" id="sn2">0</div><div class="sl">오답</div></div>
  </div>
</header>
<main id="quiz"></main>
<div id="modal">
  <div class="mb"><h2>시험 완료!</h2>
    <div class="ms" id="msc"></div><p id="mmg"></p>
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
function e(s){return(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}
function render(qs){
  const C=document.getElementById("quiz");C.innerHTML="";const N=["①","②","③","④"];
  qs.forEach((q,i)=>{
    const d=document.createElement("div");d.className="qc";
    const ch=q.code?`<pre class="cb ${q.lang||""}">${e(q.code)}</pre>`:"";
    const imgHtml=q.image?`<img src="${q.image}" style="max-width:100%;border-radius:8px;margin:8px 0 12px;display:block" />`:"";
    d.innerHTML=`<div class="qh"><div class="qn">${i+1}</div><div class="qt">${e(q.q)}</div></div>${imgHtml}${ch}<div class="chs" id="ch${i}"></div><div class="ra" id="ra${i}"><div class="rl" id="rl${i}"></div><div class="eb" id="eb${i}" style="display:none"></div></div><div class="src">[${e(q.source)}]</div>`;
    C.appendChild(d);
    const chDiv=d.querySelector("#ch"+i);
    q.choices.forEach((c,ci)=>{const b=document.createElement("button");b.className="ch";b.innerHTML=`<span class="cn">${N[ci]}</span>${e(c)}`;b.onclick=()=>sel(i,ci);chDiv.appendChild(b);});
  });
  C.insertAdjacentHTML("beforeend","<button id='nbtn' onclick='startNew()'>새 문제 "+Math.min(60,AQ.length)+"개 뽑기</button>");
}
function sel(qi,chosen){
  const btns=document.querySelectorAll("#ch"+qi+" .ch");
  btns.forEach(b=>b.disabled=true);
  const q=cur[qi],correct=q.answer;
  const ra=document.getElementById("ra"+qi),rl=document.getElementById("rl"+qi),eb=document.getElementById("eb"+qi);
  if(correct>=0){
    btns[chosen].classList.add(chosen===correct?"ok":"ng");
    if(chosen!==correct)btns[correct].classList.add("rv");
    rl.textContent=chosen===correct?"✔ 정답입니다!":"✘ 오답! 정답은 "+["①","②","③","④"][correct]+"번입니다.";
    rl.classList.add(chosen===correct?"ok":"ng");
    if(chosen===correct)ok++;else ng++;
  } else {
    btns[chosen].classList.add("ok");
    rl.textContent="선택 완료 (이 문제는 정답표 없음)";
    rl.style.color="#888";
  }
  if(q.explanation&&q.explanation.trim()){eb.style.display="block";eb.textContent="💡 "+q.explanation;}
  ra.classList.add("show");
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

# ══════════════════════════════════════════════
# GUI
# ══════════════════════════════════════════════
class App:
    def __init__(self):
        self.root=tk.Tk()
        self.root.title('PDF 랜덤 퀴즈 생성기')
        self.root.geometry('600x500')
        self.root.resizable(False,False)

        tk.Label(self.root,text='PDF 랜덤 퀴즈 생성기',
                 font=('맑은 고딕',14,'bold'),pady=14).pack()

        info=('① PDF 파일을 추가하세요 (여러 개 동시 가능)\n'
              '② "퀴즈 생성" 버튼 클릭 → HTML 파일 자동 생성\n'
              '③ 생성된 HTML을 브라우저로 열면 랜덤 퀴즈 시작!\n\n'
              '※ ①②③④ 보기가 있는 객관식 PDF면 대부분 인식됩니다.')
        tk.Label(self.root,text=info,justify='left',
                 fg='#444',font=('맑은 고딕',9),padx=16).pack(anchor='w')

        frm=tk.Frame(self.root); frm.pack(fill='both',expand=True,padx=14,pady=6)
        self.lb=tk.Listbox(frm,font=('맑은 고딕',10),height=8)
        sb=tk.Scrollbar(frm,command=self.lb.yview)
        self.lb.config(yscrollcommand=sb.set)
        self.lb.pack(side='left',fill='both',expand=True)
        sb.pack(side='right',fill='y')

        bf=tk.Frame(self.root); bf.pack(fill='x',padx=14,pady=4)
        tk.Button(bf,text='PDF 추가',command=self.add,
                  bg='#1a73e8',fg='white',font=('맑은 고딕',10),
                  padx=12,pady=5).pack(side='left',padx=4)
        tk.Button(bf,text='선택 삭제',command=self.remove,
                  font=('맑은 고딕',10),padx=12,pady=5).pack(side='left',padx=4)
        tk.Button(bf,text='전체 삭제',command=lambda:self.lb.delete(0,'end'),
                  font=('맑은 고딕',10),padx=12,pady=5).pack(side='left',padx=4)
        tk.Button(bf,text='퀴즈 생성 ▶',command=self.run,
                  bg='#34a853',fg='white',font=('맑은 고딕',11,'bold'),
                  padx=16,pady=6).pack(side='right',padx=4)

        self.sv=tk.StringVar(value='PDF 파일을 추가하세요.')
        tk.Label(self.root,textvariable=self.sv,font=('맑은 고딕',9),
                 fg='#555',wraplength=560).pack(pady=6)
        self.prog=ttk.Progressbar(self.root,length=560,mode='indeterminate')
        self.prog.pack(pady=4)
        self.root.mainloop()

    def add(self):
        files=filedialog.askopenfilenames(
            title='PDF 파일 선택',
            filetypes=[('PDF','*.pdf'),('모든 파일','*.*')])
        for f in files:
            if f not in self.lb.get(0,'end'):
                self.lb.insert('end',f)
        self.sv.set(f'{self.lb.size()}개 파일 선택됨')

    def remove(self):
        for i in reversed(self.lb.curselection()): self.lb.delete(i)

    def run(self):
        files=list(self.lb.get(0,'end'))
        if not files:
            messagebox.showwarning('경고','PDF 파일을 먼저 추가하세요!'); return
        self.prog.start(10)
        threading.Thread(target=self._gen,args=(files,),daemon=True).start()

    def _gen(self,files):
        try:
            all_qs=[]
            for f in files:
                self.sv.set(f'처리 중: {os.path.basename(f)}')
                qs=parse_pdf(f,lambda s:self.sv.set(s))
                all_qs.extend(qs)
                self.sv.set(f'{os.path.basename(f)}: {len(qs)}문제 추출')

            all_qs=dedup(all_qs)
            has_ans=sum(1 for q in all_qs if q['answer']>=0)
            has_exp=sum(1 for q in all_qs if q.get('explanation'))
            self.sv.set(f'총 {len(all_qs)}문제 (정답 있음: {has_ans}, 해설 있음: {has_exp}) — HTML 생성 중...')

            if len(all_qs)<5:
                self.root.after(0,lambda:messagebox.showerror('추출 실패',
                    f'문제가 {len(all_qs)}개밖에 추출되지 않았습니다.\n\n'
                    '이 PDF는 ①②③④ 형식의 객관식이 아닐 수 있습니다.\n'
                    '또는 텍스트가 이미지로 되어 있어 읽을 수 없을 수 있습니다.'))
                return

            qs_json=json.dumps(all_qs,ensure_ascii=False)
            html=HTML_TEMPLATE.replace('__DATA__',qs_json)

            save_dir=os.path.dirname(files[0])
            out=os.path.join(save_dir,'quiz_from_pdf.html')
            with open(out,'w',encoding='utf-8') as f: f.write(html)

            self.sv.set(f'✔ 완료! {len(all_qs)}문제 → {os.path.basename(out)}')
            self.root.after(0,lambda:messagebox.showinfo('생성 완료',
                f'총 {len(all_qs)}문제 추출 완료!\n'
                f'  • 정답 있음: {has_ans}개\n'
                f'  • 해설 있음: {has_exp}개\n\n'
                f'파일: {out}\n\n'
                '브라우저로 열어서 바로 풀어보세요!'))
            os.startfile(out)
        except Exception as ex:
            self.root.after(0,lambda:messagebox.showerror('오류',str(ex)))
        finally:
            self.root.after(0,self.prog.stop)

if __name__=='__main__':
    try:
        import fitz
    except ImportError:
        root=tk.Tk(); root.withdraw()
        messagebox.showerror('라이브러리 오류',
            'PyMuPDF가 없습니다.\n명령 프롬프트에서:\npip install pymupdf')
        raise SystemExit
    App()
