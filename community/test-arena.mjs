// v4 (weekly problems, grading, OCR, rankings), against `npm run dev` on a fresh local DB with
// GEMINI_BASE / UPSTAGE_BASE pointing at a stand-in server:  node test-arena.mjs
const B=(process.env.API||"http://127.0.0.1:8787")+"/api";
const call=async(m,p,body,tok)=>{const r=await fetch(B+p,{method:m,headers:{"Content-Type":"application/json",Origin:"http://localhost:8765",...(tok?{Authorization:"Bearer "+tok}:{})},body:body?JSON.stringify(body):undefined});return [r.status,await r.json()];};
const ok=(c,msg)=>console.log((c?"PASS ":"FAIL ")+msg);
const sign=async(u,n)=>(await call("POST","/signup",{username:u,nickname:n,password:"password1"}))[1].token;
const A=await sign("arenaA","아레나A"), Bt=await sign("arenaB","아레나B");
let [s,j]=await call("GET","/weekly?lang=ko");
ok(s===200&&j.problems.length===3&&j.week==="2026-W44","weekly list "+j.week);
ok(j.problems.every(p=>!("answer" in p)&&!("rubric" in p)&&!("body" in p)),"list hides answers");
const [P1,P2,P3]=j.problems.map(p=>p.id);
[s,j]=await call("GET",`/problems/${P3}?lang=en`);ok(j.problem.body&&j.problem.criteria.length===4&&!j.problem.solution&&!j.problem.criteria[0].requirement,"problem detail hides rubric text and solution");
[s,j]=await call("POST",`/problems/${P1}/submit`,{answer:"1.79"});ok(s===401,"submit needs login");
[s,j]=await call("POST",`/problems/${P1}/submit`,{answer:"1.79"},A);ok(j.status==="graded"&&j.score===100,"short right");
[s,j]=await call("POST",`/problems/${P1}/submit`,{answer:"1.70"},Bt);ok(j.score===0,"short wrong");
[s,j]=await call("POST",`/problems/${P1}/submit`,{answer:"1,794"},Bt);ok(j.score===100,"decimal comma");
[s,j]=await call("POST",`/problems/${P2}/submit`,{answer:"5.19"},Bt);ok(j.score===100,"astro short");
[s,j]=await call("POST",`/problems/${P2}/submit`,{answer:"abc"},A);ok(j.score===0&&j.detail.why==="not_a_number","not a number");
const essay="토크는 mgr sin(theta) 이고 수평 방향이다. dL/dt = tau 이므로 L의 방향만 바뀐다. Omega = mgr/L. fast top 근사.";
[s,j]=await call("POST",`/problems/${P3}/submit`,{answer:essay,via_ocr:true},A);
ok(j.status==="graded"&&j.detail.grader.startsWith("gemini"),"essay graded "+JSON.stringify(j).slice(0,120));
ok(j.score===55&&j.detail.evidenceIssue&&j.detail.scores.find(x=>x.id==="C").got===0,"unsupported evidence zeroes C → 25+20+0+10="+j.score);
ok(j.detail.feedback.length===1,"invented feedback quote dropped");
[s,j]=await call("GET",`/problems/${P3}`,null,A);ok(j.problem.mine.length===1&&j.problem.mine[0].via_ocr===1,"my submissions");
[s,j]=await call("GET","/rank?scope=week");ok(j.rows[0].nickname==="아레나B"&&j.rows[0].total===200&&j.rows[1].total===155,"weekly ranking "+JSON.stringify(j.rows.map(r=>[r.nickname,r.total])));
[s,j]=await call("GET","/rank?scope=all",null,A);ok(j.mine&&j.mine.rank===2&&j.rows[0].tier==="bronze","all-time + mine");
[s,j]=await call("GET","/me/stats",null,A);ok(j.rank===2&&j.total===155&&j.solved===1&&j.subs.length===3,"my stats");
// OCR
const png=Buffer.from("89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000D49444154789C6360000002000154A24F5D0000000049454E44AE426082","hex");
const fd=new FormData();fd.append("image",new Blob([png],{type:"image/png"}),"a.png");
let r=await fetch(B+"/ocr?mode=math",{method:"POST",headers:{Authorization:"Bearer "+A,Origin:"http://localhost:8765"},body:fd});let o=await r.json();
ok(r.status===200&&typeof o.text==="string","ocr "+r.status+" "+JSON.stringify(o).slice(0,80));
const fd2=new FormData();fd2.append("image",new Blob([Buffer.from("not an image at all")],{type:"image/png"}),"a.png");
r=await fetch(B+"/ocr",{method:"POST",headers:{Authorization:"Bearer "+A},body:fd2});ok(r.status===415,"ocr rejects non-image "+r.status);
r=await fetch(B+"/ocr",{method:"POST",body:fd});ok(r.status===401,"ocr needs login");
// admin
[s,j]=await call("GET","/admin/queue",null,A);ok(s===403,"admin only");
console.log("done");
