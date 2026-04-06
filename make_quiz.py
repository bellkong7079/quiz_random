import json, sys, os
sys.stdout.reconfigure(encoding='utf-8')

base = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(base, 'questions.json'), encoding='utf-8') as f:
    qs = json.load(f)

qs_json = json.dumps(qs, ensure_ascii=False)

html = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>프로그래밍기능사 랜덤 모의고사</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Malgun Gothic",sans-serif;background:#f0f2f5;color:#222}
header{background:linear-gradient(135deg,#1a73e8,#0d47a1);color:#fff;
  padding:18px 24px;display:flex;justify-content:space-between;align-items:center;
  position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,.3)}
header h1{font-size:1.15rem;line-height:1.4}
header p{font-size:.78rem;opacity:.8;margin-top:3px}
#sb{display:flex;gap:16px;font-size:.9rem;flex-shrink:0}
.si{text-align:center}.sn{font-size:1.35rem;font-weight:700}.sl{font-size:.7rem;opacity:.85}
.pw{background:rgba(255,255,255,.25);height:5px;border-radius:3px;margin-top:8px}
.pb{height:5px;background:#fff;border-radius:3px;transition:width .4s}
main{max-width:860px;margin:28px auto;padding:0 14px 60px}

/* 문제 카드 */
.qc{background:#fff;border-radius:12px;padding:20px 22px;
  margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.qh{display:flex;gap:10px;align-items:flex-start;margin-bottom:10px}
.qn{background:#1a73e8;color:#fff;border-radius:50%;
  min-width:26px;height:26px;display:flex;align-items:center;
  justify-content:center;font-size:.78rem;font-weight:700;flex-shrink:0}
.qt{font-size:.95rem;line-height:1.65}

/* 코드 블록 */
pre.cb{background:#1e1e2e;color:#cdd6f4;padding:13px 16px;border-radius:8px;
  font-size:.84rem;font-family:Consolas,"Courier New",monospace;
  line-height:1.6;margin:10px 0 13px;overflow-x:auto;white-space:pre}
pre.cb.sql{background:#1a2a1a;color:#a8d8a8}

/* 보기 버튼 */
.chs{display:grid;grid-template-columns:1fr 1fr;gap:8px}
@media(max-width:500px){.chs{grid-template-columns:1fr}}
.ch{background:#f8f9fa;border:2px solid #e0e0e0;border-radius:8px;
  padding:9px 13px;text-align:left;cursor:pointer;
  font-size:.88rem;font-family:inherit;
  transition:all .15s;display:flex;align-items:center;gap:7px;line-height:1.45}
.ch:hover:not(:disabled){background:#e8f0fe;border-color:#1a73e8}
.cn{background:#e0e0e0;color:#444;border-radius:50%;
  min-width:21px;height:21px;display:flex;align-items:center;
  justify-content:center;font-size:.75rem;font-weight:700;flex-shrink:0}
.ch.ok{background:#e6f4ea;border-color:#34a853}
.ch.ok .cn{background:#34a853;color:#fff}
.ch.ng{background:#fce8e6;border-color:#ea4335}
.ch.ng .cn{background:#ea4335;color:#fff}
.ch.rv{background:#e6f4ea;border-color:#34a853;opacity:.75}
.ch.rv .cn{background:#34a853;color:#fff}
.ch:disabled{cursor:default}

/* 결과 + 해설 */
.result-area{margin-top:12px;display:none}
.result-area.show{display:block}
.result-line{font-size:.9rem;font-weight:700;margin-bottom:8px}
.result-line.ok{color:#34a853}
.result-line.ng{color:#ea4335}

.exp-box{background:#f8f9fa;border-left:4px solid #1a73e8;
  border-radius:0 8px 8px 0;padding:12px 15px;
  font-size:.88rem;line-height:1.7;color:#333;white-space:pre-wrap}

.src{font-size:.7rem;color:#bbb;margin-top:8px}

#nbtn{display:block;margin:36px auto 0;background:#1a73e8;color:#fff;border:none;
  border-radius:10px;padding:14px 36px;font-size:1rem;font-family:inherit;cursor:pointer}
#nbtn:hover{background:#1558b0}

/* 모달 */
#modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);
  z-index:200;align-items:center;justify-content:center}
#modal.show{display:flex}
.mb{background:#fff;border-radius:16px;padding:36px 44px;text-align:center;
  max-width:340px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,.3)}
.mb h2{font-size:1.4rem;margin-bottom:6px}
.ms{font-size:2.8rem;font-weight:700;color:#1a73e8;margin:14px 0}
.mb p{color:#555;font-size:.92rem;margin-bottom:20px}
.mbs{display:flex;gap:10px;justify-content:center}
.mbt{background:#1a73e8;color:#fff;border:none;border-radius:8px;padding:11px 28px;
  font-size:.95rem;font-family:inherit;cursor:pointer}
.mbt.ol{background:#fff;color:#1a73e8;border:2px solid #1a73e8}
</style>
</head>
<body>
<header>
  <div>
    <h1>프로그래밍기능사 랜덤 모의고사</h1>
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
      <button class="mbt" onclick="startNew()">새 문제 60개</button>
    </div>
  </div>
</div>
<script>
const AQ = ''' + qs_json + ''';
let cur=[],ans=0,ok=0,ng=0,rn=0;

function pick60(){
  const a=[...AQ];
  for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}
  return a.slice(0,Math.min(60,a.length));
}

function e(s){return(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}

function render(qs){
  const C=document.getElementById("quiz");
  C.innerHTML="";
  const N=["①","②","③","④"];
  qs.forEach((q,i)=>{
    const d=document.createElement("div");
    d.className="qc";d.id="qc"+i;
    const codeHtml=q.code?`<pre class="cb ${q.lang||""}">${e(q.code)}</pre>`:"";
    d.innerHTML=
      `<div class="qh"><div class="qn">${i+1}</div><div class="qt">${e(q.q)}</div></div>`+
      codeHtml+
      `<div class="chs" id="ch${i}"></div>`+
      `<div class="result-area" id="ra${i}">`+
        `<div class="result-line" id="rl${i}"></div>`+
        `<div class="exp-box" id="ex${i}" style="display:none"></div>`+
      `</div>`+
      `<div class="src">[출처: ${e(q.source)}]</div>`;
    C.appendChild(d);
    const ch=d.querySelector("#ch"+i);
    q.choices.forEach((c,ci)=>{
      const b=document.createElement("button");
      b.className="ch";
      b.innerHTML=`<span class="cn">${N[ci]}</span>${e(c).replace(/\\n/g,'<br>')}`;
      b.onclick=()=>sel(i,ci);
      ch.appendChild(b);
    });
  });
  C.insertAdjacentHTML("beforeend","<button id=\\'nbtn\\' onclick=\\'startNew()\\'>새 문제 60개 뽑기</button>");
}

function sel(qi,chosen){
  const btns=document.querySelectorAll("#ch"+qi+" .ch");
  btns.forEach(b=>b.disabled=true);
  const q=cur[qi];
  const correct=q.answer;
  const ra=document.getElementById("ra"+qi);
  const rl=document.getElementById("rl"+qi);
  const ex=document.getElementById("ex"+qi);

  btns[chosen].classList.add(chosen===correct?"ok":"ng");
  if(chosen!==correct) btns[correct].classList.add("rv");

  ra.classList.add("show");
  if(chosen===correct){
    rl.textContent="✔ 정답입니다!";
    rl.classList.add("ok");
    ok++;
  } else {
    rl.textContent="✘ 오답! 정답은 "+["①","②","③","④"][correct]+"번입니다.";
    rl.classList.add("ng");
    ng++;
  }

  // 해설 표시
  if(q.explanation && q.explanation.trim()){
    ex.style.display="block";
    ex.textContent="💡 "+q.explanation;
  }

  ans++;upd();
  if(ans===cur.length) setTimeout(showM,500);
}

function upd(){
  document.getElementById("sa").textContent=ans;
  document.getElementById("so").textContent=ok;
  document.getElementById("sn2").textContent=ng;
  document.getElementById("pb").style.width=(ans/cur.length*100)+"%";
}

function showM(){
  const p=Math.round(ok/cur.length*100);
  document.getElementById("msc").textContent=ok+" / "+cur.length+"  ("+p+"%)";
  document.getElementById("mmg").textContent=
    p>=80?"합격권입니다! 훌륭해요!":
    p>=60?"조금만 더 노력하면 합격할 수 있어요!":
    "취약 부분을 집중 복습해 보세요. 파이팅!";
  document.getElementById("modal").classList.add("show");
}
function closeM(){document.getElementById("modal").classList.remove("show");}

function startNew(){
  closeM();ans=0;ok=0;ng=0;rn++;
  document.getElementById("ri").textContent=
    "전체 "+AQ.length+"문제 중 랜덤 "+Math.min(60,AQ.length)+"문제 ("+rn+"회차)";
  upd();cur=pick60();render(cur);
  window.scrollTo({top:0,behavior:"smooth"});
}
startNew();
</script>
</body>
</html>'''

out = os.path.join(base, 'quiz_random.html')
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)

has_exp = sum(1 for q in qs if q.get('explanation'))
print(f'생성 완료: {out}')
print(f'총 {len(qs)}문제 | 해설 있음: {has_exp}개')
