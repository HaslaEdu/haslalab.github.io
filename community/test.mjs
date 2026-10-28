// run against `npm run dev` on a fresh local DB:  node test.mjs
const B=(process.env.API||"http://127.0.0.1:8787")+"/api";
const call=async(m,p,body,tok)=>{const r=await fetch(B+p,{method:m,headers:{"Content-Type":"application/json",Origin:"http://localhost:8765",...(tok?{Authorization:"Bearer "+tok}:{})},body:body?JSON.stringify(body):undefined});return [r.status,await r.json(),r.headers.get("access-control-allow-origin")];};
const ok=(c,msg)=>console.log((c?"PASS ":"FAIL ")+msg);
let [s,j,o]=await call("POST","/signup",{username:"alice",nickname:"앨리스",password:"password1"});ok(s===200&&j.token&&o==="http://localhost:8765","signup "+s);
const A=j.token;
[s,j]=await call("POST","/signup",{username:"ALICE",nickname:"x1",password:"password1"});ok(s===409&&j.error==="username_taken","dup username "+j.error);
[s,j]=await call("POST","/signup",{username:"bob",nickname:"앨리스",password:"password1"});ok(s===409&&j.error==="nickname_taken","dup nick");
[s,j]=await call("POST","/signup",{username:"bo",nickname:"bob",password:"password1"});ok(s===400,"short username");
[s,j]=await call("POST","/signup",{username:"bob",nickname:"밥",password:"short"});ok(s===400&&j.error==="bad_password","short pw");
[s,j]=await call("POST","/signup",{username:"bob",nickname:"밥 Kim",password:"password2"});ok(s===200,"signup bob");const Bt=j.token;
[s,j]=await call("POST","/login",{username:"alice",password:"wrong"});ok(s===401,"bad login");
[s,j]=await call("POST","/login",{username:"Alice",password:"password1"});ok(s===200&&j.user.nickname==="앨리스","login case-insens");
[s,j]=await call("GET","/me",null,A);ok(j.user&&j.user.username==="alice","me");
[s,j]=await call("POST","/posts",{board:"qna",title:"APhO 2025 질문",body:"<script>alert(1)</script>\n두번째 줄"},A);ok(s===200,"post");const P=j.id;
[s,j]=await call("POST","/posts",{board:"nope",title:"t",body:"b"},A);ok(s===400,"bad board");
[s,j]=await call("POST","/posts",{board:"free",title:"t",body:"b"});ok(s===401,"anon post");
[s,j]=await call("GET","/posts?board=qna");ok(j.total===1&&j.posts[0].nickname==="앨리스","list");
[s,j]=await call("GET","/posts?q=2025");ok(j.total===1,"search");
[s,j]=await call("GET","/posts?q=%25");ok(j.total===0,"search escape %");
[s,j]=await call("POST",`/posts/${P}/comments`,{body:"답변"},Bt);ok(s===200,"comment");const C=j.id;
[s,j]=await call("POST",`/posts/${P}/like`,null,Bt);ok(j.liked&&j.n_likes===1,"like");
[s,j]=await call("POST",`/posts/${P}/like`,null,Bt);ok(!j.liked&&j.n_likes===0,"unlike");
[s,j]=await call("POST",`/posts/${P}/like`,null,Bt);
[s,j]=await call("GET",`/posts/${P}?view=1`,null,Bt);ok(j.post.n_comments===1&&j.liked&&!j.post.mine&&j.comments[0].mine&&j.post.views===1,"get post");
[s,j]=await call("PATCH",`/posts/${P}`,{title:"x",body:"y"},Bt);ok(s===403,"edit others forbidden");
[s,j]=await call("PATCH",`/posts/${P}`,{title:"수정",body:"y"},A);ok(s===200,"edit own");
[s,j]=await call("DELETE",`/comments/${C}`,null,A);ok(s===403,"del others comment");
[s,j]=await call("DELETE",`/comments/${C}`,null,Bt);ok(s===200,"del own comment");
[s,j]=await call("GET",`/posts/${P}`);ok(j.post.n_comments===0&&j.post.title==="수정","after");
[s,j]=await call("POST","/report",{kind:"post",id:P,reason:"spam"},Bt);ok(s===200,"report");
for(let i=0;i<6;i++)[s,j]=await call("POST","/posts",{board:"free",title:"t"+i,body:"b"},Bt);
ok(s===429,"post rate limit "+s);
[s,j]=await call("POST","/me/password",{old:"password2",password:"password3"},Bt);ok(s===200,"pw change");
[s,j]=await call("POST","/login",{username:"bob",password:"password3"});ok(s===200,"login new pw");
[s,j]=await call("POST","/logout",null,A);[s,j]=await call("GET","/me",null,A);ok(j.user===null,"logout");
[s,j]=await call("DELETE","/me",null,Bt);[s,j]=await call("GET",`/posts?board=free`);ok(j.posts.every(p=>p.gone===1),"account delete anonymises");
[s,j]=await call("DELETE",`/posts/${P}`,null,(await call("POST","/login",{username:"alice",password:"password1"}))[1].token);ok(s===200,"del post");
const r=await fetch(B+"/health",{method:"OPTIONS",headers:{Origin:"https://evil.example"}});ok(!r.headers.get("access-control-allow-origin"),"cors deny");

/* v2: tags, votes, replies, sorting, best posts, notices */
{
  let [s0, h] = await call("GET", "/health"); ok(h.v >= 2, "health v2+");
  let [s1, a] = await call("POST", "/signup", { username: "v2user", nickname: "브이투", password: "password1" }); const T = a.token;
  let [s2, b] = await call("POST", "/signup", { username: "v2other", nickname: "다른이", password: "password1" }); const U = b.token;
  let [s3, p1] = await call("POST", "/posts", { board: "qna", tag: "q", title: "태그 질문", body: "본문" }, T); ok(s3 === 200, "post with tag");
  let [s4, p2] = await call("POST", "/posts", { board: "qna", tag: "notice", title: "공지 시도", body: "x" }, T);
  let [, g2] = await call("GET", `/posts/${p2.id}`); ok(g2.post.tag === "gen", "notice tag needs admin");
  let [, v1] = await call("POST", `/posts/${p1.id}/vote`, { v: 1 }, U); ok(v1.my === 1 && v1.n_likes === 1, "upvote");
  let [, v2] = await call("POST", `/posts/${p1.id}/vote`, { v: -1 }, U); ok(v2.my === -1 && v2.n_likes === 0 && v2.n_dislikes === 1, "switch to downvote");
  let [, v3] = await call("POST", `/posts/${p1.id}/vote`, { v: -1 }, U); ok(v3.my === 0 && v3.n_dislikes === 0, "take vote back");
  let [, c1] = await call("POST", `/posts/${p1.id}/comments`, { body: "부모" }, U);
  let [, c2] = await call("POST", `/posts/${p1.id}/comments`, { body: "답글", parent_id: c1.id }, T);
  let [, c3] = await call("POST", `/posts/${p1.id}/comments`, { body: "답글의 답글", parent_id: c2.id }, U);
  let [, g1] = await call("GET", `/posts/${p1.id}`, null, U);
  ok(g1.comments.find(c => c.id === c3.id).parent_id === c1.id && g1.post.n_comments === 3, "replies one level deep");
  let [sd] = await call("DELETE", `/comments/${c1.id}`, null, U); let [, g3] = await call("GET", `/posts/${p1.id}`);
  ok(sd === 200 && g3.comments.length === 0 && g3.post.n_comments === 0, "deleting a comment takes its replies");
  await call("POST", `/posts/${p1.id}/vote`, { v: 1 }, U); await call("POST", `/posts/${p1.id}/vote`, { v: 1 }, T);
  let [, lt] = await call("GET", "/posts?board=qna&sort=top"); ok(lt.posts[0].id === p1.id && "snip" in lt.posts[0], "sort top + snippet");
  let [, lh] = await call("GET", "/posts?sort=hot"); ok(Array.isArray(lh.posts), "sort hot");
  let [, lb] = await call("GET", "/posts?best=1"); ok(lb.posts.every(p => p.n_likes - p.n_dislikes >= 3), "best filter");
  let [, la] = await call("GET", "/posts?q=" + encodeURIComponent("브이") + "&field=author"); ok(la.total >= 2, "search by author");
  let [, lq] = await call("GET", "/posts?tag=q"); ok(lq.posts.every(p => p.tag === "q"), "tag filter");
  let [, bd] = await call("GET", "/boards"); ok(bd.boards.some(r => r.board === "qna" && r.n >= 2), "board counts");
}

/* v3: the Korean and the English server keep their own posts */
{
  let [, h] = await call("GET", "/health"); ok(h.v >= 3, "health v3+");
  let [, a] = await call("POST", "/signup", { username: "v3user", nickname: "브이삼", password: "password1" });
  let [, pk] = await call("POST", "/posts", { board: "free", lang: "ko", title: "한국어 글", body: "x" }, a.token);
  let [, pe] = await call("POST", "/posts", { board: "free", lang: "en", title: "English post", body: "x" }, a.token);
  let [, lk] = await call("GET", "/posts?lang=ko&board=free"); let [, le] = await call("GET", "/posts?lang=en&board=free");
  ok(lk.posts.some(p => p.id === pk.id) && !lk.posts.some(p => p.id === pe.id), "ko server only");
  ok(le.posts.some(p => p.id === pe.id) && !le.posts.some(p => p.id === pk.id), "en server only");
  let [, be] = await call("GET", "/boards?lang=en"); ok(be.boards.find(r => r.board === "free").n === 1, "board counts per server");
}
