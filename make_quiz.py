import json, sys, os
sys.stdout.reconfigure(encoding='utf-8')

base = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(base, 'questions.json'), encoding='utf-8') as f:
    qs = json.load(f)

qs_json = json.dumps(qs, ensure_ascii=False)

html_template = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>프로그래밍기능사 랜덤 모의고사 60문항</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Malgun Gothic",sans-serif;background:#f0f2f5;color:#222}
header{background:linear-gradient(135deg,#1a73e8,#0d47a1);color:#fff;
  padding:18px 24px;display:flex;justify-content:space-between;
  align-items:center;position:sticky;top:0;z-index:100;
  box-shadow:0 2px 8px rgba(0,0,0,.3)}
header h1{font-size:1.15rem;line-height:1.4}
header p{font-size:.78rem;opacity:.8;margin-top:3px}
#score-board{display:flex;gap:16px;font-size:.9rem;flex-shrink:0}
.sb-item{text-align:center}
.sb-num{font-size:1.35rem;font-weight:700}
.sb-label{font-size:.7rem;opacity:.85}
.prog-wrap{background:rgba(255,255,255,.25);height:5px;border-radius:3px;margin-top:8px}
.prog-bar{height:5px;background:#fff;border-radius:3px;transition:width .4s}
main{max-width:860px;margin:28px auto;padding:0 14px 60px}
.q-card{background:#fff;border-radius:12px;padding:20px 22px;
  margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,.08);
  transition:box-shadow .2s}
.q-card:hover{box-shadow:0 3px 12px rgba(0,0,0,.12)}
.q-head{display:flex;gap:10px;align-items:flex-start;margin-bottom:12px}
.q-num{background:#1a73e8;color:#fff;border-radius:50%;
  min-width:26px;height:26px;display:flex;align-items:center;
  justify-content:center;font-size:.78rem;font-weight:700;flex-shrink:0}
.q-text{font-size:.95rem;line-height:1.65;white-space:pre-wrap}
.choices{display:grid;grid-template-columns:1fr 1fr;gap:8px}
@media(max-width:500px){.choices{grid-template-columns:1fr}}
.c-btn{background:#f8f9fa;border:2px solid #e0e0e0;border-radius:8px;
  padding:9px 13px;text-align:left;cursor:pointer;
  font-size:.88rem;font-family:inherit;
  transition:all .15s;display:flex;align-items:center;gap:7px;line-height:1.45}
.c-btn:hover:not(:disabled){background:#e8f0fe;border-color:#1a73e8}
.c-num{background:#e0e0e0;color:#444;border-radius:50%;
  min-width:21px;height:21px;display:flex;align-items:center;
  justify-content:center;font-size:.75rem;font-weight:700;flex-shrink:0}
.c-btn.correct{background:#e6f4ea;border-color:#34a853}
.c-btn.correct .c-num{background:#34a853;color:#fff}
.c-btn.wrong{background:#fce8e6;border-color:#ea4335}
.c-btn.wrong .c-num{background:#ea4335;color:#fff}
.c-btn.reveal{background:#e6f4ea;border-color:#34a853;opacity:.7}
.c-btn.reveal .c-num{background:#34a853;color:#fff}
.c-btn:disabled{cursor:default}
.result-msg{margin-top:9px;font-size:.85rem;font-weight:700;display:none}
.result-msg.show{display:block}
.result-msg.ok{color:#34a853}
.result-msg.ng{color:#ea4335}
.source-tag{font-size:.72rem;color:#aaa;margin-top:6px}
#new-btn{display:block;margin:36px auto 0;
  background:#1a73e8;color:#fff;border:none;
  border-radius:10px;padding:14px 36px;
  font-size:1rem;font-family:inherit;cursor:pointer;transition:background .2s}
#new-btn:hover{background:#1558b0}
#modal{display:none;position:fixed;inset:0;
  background:rgba(0,0,0,.55);z-index:200;
  align-items:center;justify-content:center}
#modal.show{display:flex}
.modal-box{background:#fff;border-radius:16px;
  padding:36px 44px;text-align:center;
  max-width:340px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,.3)}
.modal-box h2{font-size:1.4rem;margin-bottom:6px}
.modal-score{font-size:2.8rem;font-weight:700;color:#1a73e8;margin:14px 0}
.modal-box p{color:#555;font-size:.92rem;margin-bottom:20px}
.modal-btns{display:flex;gap:10px;justify-content:center}
.m-btn{background:#1a73e8;color:#fff;border:none;
  border-radius:8px;padding:11px 28px;
  font-size:.95rem;font-family:inherit;cursor:pointer}
.m-btn.outline{background:#fff;color:#1a73e8;border:2px solid #1a73e8}
.m-btn:hover{opacity:.88}
</style>
</head>
<body>
<header>
  <div>
    <h1>프로그래밍기능사 랜덤 모의고사</h1>
    <p id="round-info">잠시 후 시작...</p>
    <div class="prog-wrap"><div class="prog-bar" id="prog" style="width:0%"></div></div>
  </div>
  <div id="score-board">
    <div class="sb-item"><div class="sb-num" id="sb-ans">0</div><div class="sb-label">푼 문제</div></div>
    <div class="sb-item"><div class="sb-num" id="sb-ok">0</div><div class="sb-label">정답</div></div>
    <div class="sb-item"><div class="sb-num" id="sb-ng">0</div><div class="sb-label">오답</div></div>
  </div>
</header>
<main id="quiz"></main>
<div id="modal">
  <div class="modal-box">
    <h2>시험 완료!</h2>
    <div class="modal-score" id="m-score"></div>
    <p id="m-msg"></p>
    <div class="modal-btns">
      <button class="m-btn outline" onclick="closeModal()">결과 보기</button>
      <button class="m-btn" onclick="startNew()">새 문제 60개</button>
    </div>
  </div>
</div>
<script>
const ALL_QS = __QS_JSON__;
let cur=[],answered=0,correct=0,wrong=0,roundN=0;

function pick60(){
  const a=[...ALL_QS];
  for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}
  return a.slice(0,Math.min(60,a.length));
}

function esc(s){return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}

function render(qs){
  const C=document.getElementById("quiz");
  C.innerHTML="";
  const N=["①","②","③","④"];
  qs.forEach((q,i)=>{
    const d=document.createElement("div");
    d.className="q-card";d.id="qc"+i;
    d.innerHTML=`<div class="q-head"><div class="q-num">${i+1}</div><div class="q-text">${esc(q.q)}</div></div><div class="choices" id="ch-${i}"></div><div class="result-msg" id="msg-${i}"></div><div class="source-tag">[출처: ${q.source}]</div>`;
    C.appendChild(d);
    const ch=d.querySelector("#ch-"+i);
    q.choices.forEach((c,ci)=>{
      const b=document.createElement("button");
      b.className="c-btn";
      b.innerHTML=`<span class="c-num">${N[ci]}</span>${esc(c)}`;
      b.onclick=()=>sel(i,ci);
      ch.appendChild(b);
    });
  });
  C.insertAdjacentHTML("beforeend","<button id=\\"new-btn\\" onclick=\\"startNew()\\">새 문제 60개 뽑기</button>");
}

function sel(qi,chosen){
  const btns=document.querySelectorAll("#ch-"+qi+" .c-btn");
  btns.forEach(b=>b.disabled=true);
  const ans=cur[qi].answer;
  const msg=document.getElementById("msg-"+qi);
  btns[chosen].classList.add(chosen===ans?"correct":"wrong");
  if(chosen!==ans)btns[ans].classList.add("reveal");
  msg.classList.add("show");
  if(chosen===ans){msg.textContent="✔ 정답!";msg.classList.add("ok");correct++;}
  else{msg.textContent="✘ 오답! 정답은 "+["①","②","③","④"][ans]+"번";msg.classList.add("ng");wrong++;}
  answered++;updateHUD();
  if(answered===cur.length)setTimeout(showModal,500);
}

function updateHUD(){
  document.getElementById("sb-ans").textContent=answered;
  document.getElementById("sb-ok").textContent=correct;
  document.getElementById("sb-ng").textContent=wrong;
  document.getElementById("prog").style.width=(answered/cur.length*100)+"%";
}

function showModal(){
  const pct=Math.round(correct/cur.length*100);
  document.getElementById("m-score").textContent=correct+" / "+cur.length+"  ("+pct+"%)";
  const msg=pct>=80?"합격권입니다! 훌륭해요!":pct>=60?"조금만 더 노력하면 합격할 수 있어요!":"취약 부분을 집중 복습해 보세요. 파이팅!";
  document.getElementById("m-msg").textContent=msg;
  document.getElementById("modal").classList.add("show");
}
function closeModal(){document.getElementById("modal").classList.remove("show");}

function startNew(){
  closeModal();answered=0;correct=0;wrong=0;roundN++;
  document.getElementById("round-info").textContent="전체 "+ALL_QS.length+"문제 중 랜덤 60문제 ("+roundN+"회차)";
  updateHUD();cur=pick60();render(cur);
  window.scrollTo({top:0,behavior:"smooth"});
}
startNew();
</script>
</body>
</html>'''

html = html_template.replace('__QS_JSON__', qs_json)

out = os.path.join(base, 'quiz_random.html')
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'생성 완료: {out}')
print(f'총 {len(qs)}개 문제 포함, 매번 랜덤 60개 출제')
