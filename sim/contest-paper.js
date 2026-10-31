/* A4 practice answer sheets and device-local optical mark reading. No scan leaves the browser. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.ContestPaper=api;})(typeof globalThis==='object'?globalThis:this,function(){
  'use strict';
  const VERSION=1, W=210,H=297, ANCHORS=[{x:10,y:10},{x:200,y:10},{x:200,y:287},{x:10,y:287}];
  const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function hash(s){let h=2166136261;for(const c of String(s)){h^=c.charCodeAt(0);h=Math.imul(h,16777619);}return h>>>0;}
  function digitCount(e){if(e.digits===3)return 3;if(e.answerMax!==null)return Math.max(1,String(e.answerMax??999).length);const a=(e.answers||[]).flat().filter(v=>Number.isSafeInteger(Number(v))&&Number(v)>=0);return Math.max(6,...a.map(v=>String(v).length));}
  function layout(e,options={}){
    if(!e||!e.id||!Number.isInteger(e.questions)||e.questions<1||e.questions>200||!['choice','integer','proof'].includes(e.kind))throw new Error('Unsupported answer sheet');
    const digits=e.kind==='integer'?digitCount(e):0;if(digits>15)throw new Error('Answer exceeds safe integer precision');
    const title=typeof e.title==='object'?e.title.ko||e.title.en:e.title||e.id,per=e.kind==='choice'?60:e.kind==='integer'?(digits>12?5:digits>5?10:20):1;
    const count=Math.ceil(e.questions/per),sheets=[];
    for(let index=0;index<count;index++){
      const q0=index*per+1,qn=Math.min(e.questions,q0+per-1),qs=[];
      for(let q=q0;q<=qn;q++)qs.push(q);
      sheets.push({index,q0,qn,questions:qs,kind:e.kind,digits,anchors:ANCHORS.map(p=>({...p})),bubbles:[],code:[],working:false});
    }
    if(e.kind==='proof')for(let n=0;n<Math.max(0,Math.min(10,options.extraSheets||0));n++)sheets.push({index:sheets.length,q0:null,qn:null,questions:[],kind:'proof',digits:0,anchors:ANCHORS.map(p=>({...p})),bubbles:[],code:[],working:true});
    const model={version:VERSION,id:e.id,title,kind:e.kind,questions:e.questions,offset:e.questionOffset||0,digits,width:W,height:H,sheets};
    for(const sheet of sheets){
      const h=hash([VERSION,e.id,e.kind,e.questions,e.questionOffset||0,digits,sheet.index,sheets.length].join('|'))&0xfffff;
      const bits=[1,0,1,1,...Array.from({length:20},(_,i)=>(h>>>(19-i))&1)];
      sheet.code=bits.map((bit,i)=>({x:30+i*6.4,y:58,bit,size:3}));
      if(e.kind==='choice')for(let i=0;i<sheet.questions.length;i++){
        const q=sheet.questions[i],col=Math.floor(i/20),row=i%20,x=18+col*61,y=73+row*9.5;
        for(let v=1;v<=(e.choices||5);v++)sheet.bubbles.push({q,column:0,value:v,x:x+16+(v-1)*7.5,y,r:1.65});
      }
      if(e.kind==='integer'){
        const cols=digits>12?1:digits>5?2:4,cw=180/cols;
        for(let i=0;i<sheet.questions.length;i++){
          const q=sheet.questions[i],col=Math.floor(i/5),row=i%5,x=15+col*cw,y=66+row*43,step=digits>5?7:5.7,start=digits===3?15:11;
          for(let column=0;column<digits;column++)for(let value=0;value<10;value++)sheet.bubbles.push({q,column,value,x:x+start+column*step,y:y+11+value*3.05,r:digits===3?1.30:1.18});
        }
      }
    }
    return model;
  }
  function svg(e,index=0,options={}){
    const m=layout(e,options),s=m.sheets[index];if(!s)throw new Error('No such sheet');
    let out=`<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297" role="img" aria-label="${esc(m.title)} 답안지 ${index+1}"><rect width="210" height="297" fill="white"/><g fill="black" font-family="Arial,Malgun Gothic,sans-serif">`;
    const text=(x,y,t,size=3,more='')=>`<text x="${x}" y="${y}" font-size="${size}" ${more}>${esc(t)}</text>`;
    s.anchors.forEach((p,i)=>{out+=`<rect x="${p.x-3.5}" y="${p.y-3.5}" width="7" height="7"/>`;if(!i)out+=`<rect x="${p.x-1.2}" y="${p.y-1.2}" width="2.4" height="2.4" fill="white"/>`;});
    out+=text(19,21,'HaslaLab · 학습용 답안지',3.1)+text(191,21,`${index+1} / ${m.sheets.length}`,3.1,'text-anchor="end"');
    const titleLines=[];let line='',units=0;for(const ch of m.title){const u=/[\x00-\x7f]/.test(ch)?.55:1;if(units+u>42){titleLines.push(line);line='';units=0;}line+=ch;units+=u;}if(line)titleLines.push(line);
    titleLines.slice(0,2).forEach((t,i)=>out+=text(19,30+i*5.4,t,4.1,'font-weight="bold"'));
    out+=text(19,44,'성명: __________________  수험번호/메모: __________________',3.2);
    out+=text(19,50,e.kind==='proof'?'주최기관 공식 양식이 아닌 HaslaLab 연습지입니다. 문항 번호와 쪽수를 적으세요.':'검정색으로 원 안을 꽉 채우세요. 지운 흔적·중복 마킹은 반드시 검토하세요.',2.7);
    out+=text(19,54,e.kind==='integer'?`${m.digits}자리 마킹 · 모든 자리를 표시하세요(예: 7 → ${String(7).padStart(m.digits,'0')}).`:'A4 · 실제 크기 100% · 여백 없음 · 네 모서리 검정 표식을 자르지 마세요.',2.7);
    for(const c of s.code)if(c.bit)out+=`<rect x="${c.x-c.size/2}" y="${c.y-c.size/2}" width="${c.size}" height="${c.size}"/>`;
    if(e.kind==='choice')for(let i=0;i<s.questions.length;i++){
      const q=s.questions[i],col=Math.floor(i/20),row=i%20,x=18+col*61,y=73+row*9.5;out+=text(x,y+1,`${q+m.offset}.`,3.3);
      for(let v=1;v<=(e.choices||5);v++)out+=text(x+16+(v-1)*7.5,y-2.8,(e.choiceLabels||[])[v-1]||String(v),2.5,'text-anchor="middle"');
    }
    if(e.kind==='integer'){
      const cols=m.digits>12?1:m.digits>5?2:4,cw=180/cols,start=m.digits===3?15:11,step=m.digits>5?7:5.7;
      for(let i=0;i<s.questions.length;i++){
        const q=s.questions[i],x=15+Math.floor(i/5)*cw,y=66+(i%5)*43;
        out+=text(x,y+1,`${q+m.offset}번`,3.2);
        for(let c=0;c<m.digits;c++)out+=text(x+start+c*step,y+6,`${m.digits-c}자리`,2.0,'text-anchor="middle"');
        for(let v=0;v<10;v++)out+=text(x+4,y+12+v*3.05,v,2.2);
      }
    }
    for(const b of s.bubbles)out+=`<circle cx="${b.x}" cy="${b.y}" r="${b.r}" fill="white" stroke="black" stroke-width=".18"/>`;
    if(e.kind==='proof'){
      const q=s.questions[0],points=Array.isArray(e.points)?e.points[q-1]:e.point||7;
      out+=text(19,69,s.working?'추가 풀이·워킹시트':`${q+m.offset}번 풀이 · ${points}점`,4.1);
      out+=text(19,77,s.working?'문항 번호: __________  이어지는 쪽: __________':'답과 그 근거를 빠짐없이 서술하세요. 추가 용지에도 성명·문항 번호를 적으세요.',2.8);
      for(let y=87;y<279;y+=8)out+=`<line x1="19" x2="191" y1="${y}" y2="${y}" stroke="#999" stroke-width=".13"/>`;
    }
    out+=text(19,283,`식별: ${e.id} · ${index+1}/${m.sheets.length} · 양식 v${VERSION}`,2.25);
    return out+'</g></svg>';
  }
  function print(e,options={}){
    if(typeof document==='undefined')throw new Error('Printing needs a browser');
    const m=layout(e,options),frame=document.createElement('iframe');frame.title='인쇄용 답안지';frame.className='contest-print-frame';
    frame.style.cssText='position:fixed;width:1px;height:1px;left:-10000px;top:0;border:0';
    frame.srcdoc=`<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>${esc(m.title)} · 답안지</title><style>@page{size:A4 portrait;margin:0}*{box-sizing:border-box}html,body{margin:0;padding:0;background:white}.page{width:210mm;height:297mm;break-after:page;page-break-after:always;overflow:hidden}.page:last-child{break-after:auto;page-break-after:auto}svg{display:block;width:210mm;height:297mm}body{-webkit-print-color-adjust:exact;print-color-adjust:exact}</style></head><body>${m.sheets.map((s,i)=>`<section class="page">${svg(e,i,options)}</section>`).join('')}</body></html>`;
    frame.onload=()=>{setTimeout(()=>{try{frame.contentWindow.focus();frame.contentWindow.print();}catch(error){options.onError?.(error);}},100);};document.body.append(frame);
    const close=()=>frame.remove();frame.contentWindow?.addEventListener('afterprint',()=>setTimeout(close,1000),{once:true});setTimeout(close,180000);
    return {sheets:m.sheets.length,close};
  }
  function solve(a,b){const n=b.length,m=a.map((r,i)=>r.slice().concat(b[i]));for(let k=0;k<n;k++){let p=k;for(let i=k+1;i<n;i++)if(Math.abs(m[i][k])>Math.abs(m[p][k]))p=i;if(Math.abs(m[p][k])<1e-10)throw new Error('Registration points are degenerate');[m[k],m[p]]=[m[p],m[k]];const d=m[k][k];for(let j=k;j<=n;j++)m[k][j]/=d;for(let i=0;i<n;i++)if(i!==k){const f=m[i][k];for(let j=k;j<=n;j++)m[i][j]-=f*m[k][j];}}return m.map(r=>r[n]);}
  function homography(from,to){if(from.length!==4||to.length!==4)throw new Error('Four points required');const a=[],b=[];for(let i=0;i<4;i++){const {x,y}=from[i],u=to[i].x,v=to[i].y;a.push([x,y,1,0,0,0,-u*x,-u*y]);b.push(u);a.push([0,0,0,x,y,1,-v*x,-v*y]);b.push(v);}return solve(a,b).concat(1);}
  function transform(h,x,y){const d=h[6]*x+h[7]*y+1;if(Math.abs(d)<1e-10)throw new Error('Invalid registration');return {x:(h[0]*x+h[1]*y+h[2])/d,y:(h[3]*x+h[4]*y+h[5])/d};}
  function darkness(image,x,y){const ix=Math.round(x),iy=Math.round(y);if(ix<0||iy<0||ix>=image.width||iy>=image.height)return null;const i=(iy*image.width+ix)*4,d=image.data;return (1-(.2126*d[i]+.7152*d[i+1]+.0722*d[i+2])/255)*(d[i+3]/255);}
  function sample(image,h,x,y,r){let sum=0,n=0;for(let a=-3;a<=3;a++)for(let b=-3;b<=3;b++)if(a*a+b*b<=9){const p=transform(h,x+a*r/3,y+b*r/3),v=darkness(image,p.x,p.y);if(v===null)throw new Error('Sheet cropped or outside photo');sum+=v;n++;}return sum/n;}
  function classify(scores){const order=scores.map((score,index)=>({score,index})).sort((a,b)=>b.score-a.score),top=order[0],second=order[1]?.score||0;if(top.score<.18)return {status:'blank',value:null};if(second>.34)return {status:'multiple',value:null};if(top.score<.44||top.score-second<.22)return {status:'uncertain',value:null};return {status:'marked',value:top.index};}
  function verifyCode(image,sheet,h){return sheet.code.every(c=>{const v=sample(image,h,c.x,c.y,.75);return c.bit?v>.62:v<.25;});}
  function recognize(image,model,sheetIndex=0,points){
    if(model.kind==='proof')throw new Error('서술형은 마킹 인식 대신 스캔 답안을 제출하세요.');
    if(!image||image.data.length<image.width*image.height*4)throw new Error('Invalid scan image');
    const sheet=model.sheets[sheetIndex];if(!sheet)throw new Error('No such page');
    const found=points||detectAnchors(image);if(!found)throw new Error('네 모서리 검정 표식을 찾지 못했습니다. 네 점을 직접 지정하세요.');
    let h=null;for(let k=0;k<4;k++){const candidate=homography(sheet.anchors,found.map((_,i)=>found[(i+k)%4]));if(verifyCode(image,sheet,candidate)){h=candidate;break;}}
    if(!h)throw new Error('용지 식별 코드가 이 시험·쪽과 맞지 않거나 흐립니다. 올바른 답안지인지 확인하세요.');
    const rows=[],marks={};for(const q of sheet.questions){
      const groups=[];for(let c=0;c<(model.kind==='integer'?model.digits:1);c++){
        const bubbles=sheet.bubbles.filter(b=>b.q===q&&b.column===c).sort((a,b)=>a.value-b.value),scores=bubbles.map(b=>sample(image,h,b.x,b.y,b.r*.64));
        const r=classify(scores);groups.push({...r,value:r.status==='marked'?bubbles[r.value].value:null,scores});
      }
      const allBlank=groups.every(g=>g.status==='blank'),valid=groups.every(g=>g.status==='marked');
      const status=allBlank?'blank':valid?'marked':groups.some(g=>g.status==='multiple')?'multiple':'uncertain';
      const rawDigits=groups.map(g=>g.value===null?'?':String(g.value)).join(''),value=status==='marked'?(model.kind==='integer'?Number(rawDigits):groups[0].value):null;
      if(value!==null)marks[q]=value;rows.push({q,number:q+model.offset,status,value,rawDigits,groups});
    }
    return {examId:model.id,sheetIndex,rows,marks,uncertain:rows.filter(r=>!['marked','blank'].includes(r.status)).map(r=>r.q),registered:true};
  }
  function detectAnchors(image){
    const scale=Math.max(1,Math.ceil(Math.max(image.width,image.height)/1400)),w=Math.ceil(image.width/scale),h=Math.ceil(image.height/scale),dark=new Uint8Array(w*h),seen=new Uint8Array(w*h),components=[];
    for(let y=0;y<h;y++)for(let x=0;x<w;x++)dark[y*w+x]=darkness(image,Math.min(image.width-1,x*scale),Math.min(image.height-1,y*scale))>.65?1:0;
    const queue=new Int32Array(w*h);
    for(let start=0;start<dark.length;start++)if(dark[start]&&!seen[start]){
      let head=0,tail=1,minx=start%w,maxx=minx,miny=Math.floor(start/w),maxy=miny;queue[0]=start;seen[start]=1;
      while(head<tail){const k=queue[head++],x=k%w,y=Math.floor(k/w);minx=Math.min(minx,x);maxx=Math.max(maxx,x);miny=Math.min(miny,y);maxy=Math.max(maxy,y);for(const next of [x>0?k-1:-1,x<w-1?k+1:-1,y>0?k-w:-1,y<h-1?k+w:-1])if(next>=0&&dark[next]&&!seen[next]){seen[next]=1;queue[tail++]=next;}}
      const cw=maxx-minx+1,ch=maxy-miny+1,ratio=cw/ch,fill=tail/(cw*ch);
      if(cw>w*.014&&cw<w*.08&&ch>h*.012&&ch<h*.08&&ratio>.48&&ratio<1.9&&fill>.36)components.push({x:(minx+maxx)/2/w,y:(miny+maxy)/2/h,area:cw*ch});
    }
    const corners=[[0,0],[1,0],[1,1],[0,1]],picked=[];
    for(const [cx,cy] of corners){const choices=components.filter(p=>(cx?p.x>.72:p.x<.28)&&(cy?p.y>.75:p.y<.25));choices.sort((a,b)=>(Math.hypot(a.x-cx,a.y-cy)-Math.hypot(b.x-cx,b.y-cy))||b.area-a.area);if(!choices.length)return null;picked.push({x:choices[0].x*w*scale,y:choices[0].y*h*scale});}
    return picked;
  }
  let pdfPromise=null;
  function pdfLibrary(){if(typeof window==='undefined')return Promise.reject(new Error('PDF reader needs browser'));if(window.pdfjsLib)return Promise.resolve(window.pdfjsLib);return pdfPromise||(pdfPromise=new Promise((resolve,reject)=>{const s=document.createElement('script');s.src='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';s.onload=()=>{window.pdfjsLib.GlobalWorkerOptions.workerSrc='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';resolve(window.pdfjsLib);};s.onerror=()=>{pdfPromise=null;reject(new Error('PDF 읽기 모듈을 불러오지 못했습니다. 사진 파일을 사용하거나 다시 시도하세요.'));};document.head.append(s);}));}
  function mountScan(host,e,options={}){
    const model=layout(e),ko=options.lang!=='en',tr=(a,b)=>ko?a:b;if(model.kind==='proof'){host.textContent=tr('서술형 답안은 스캔 제출 기능으로 제출하세요.','Submit scanned proof pages through the grading service.');return {dispose(){}};}
    let alive=true,tasks=[],active=null,image=null,points=[],manual=false,current=null,readers=[],accepted=new Map(),version=0,emitted=false;
    const text=(s)=>document.createTextNode(s),button=(label,fn)=>{const b=document.createElement('button');b.type='button';b.textContent=label;b.onclick=fn;return b;};
    host.classList.add('contest-scan');host.replaceChildren();const h=document.createElement('h3');h.textContent=tr('인쇄 답안지 스캔 읽기','Read printed answer sheets');host.append(h);
    const note=document.createElement('p');note.className='hint';note.textContent=tr('이 시험에서 출력한 마킹 답안지의 네 모서리까지 촬영하세요. 파일은 이 기기에서만 읽습니다. 인식 후 각 답안을 확인한 다음 채점에 사용합니다.','Photograph all four corner markers of the sheet printed for this exam. Files stay on this device. Review the recognized answers before grading.');host.append(note);
    const input=document.createElement('input');input.type='file';input.accept='image/*,application/pdf,.pdf';input.multiple=true;input.setAttribute('aria-label',tr('스캔 답안 사진 또는 PDF','Scanned answer images or PDF'));host.append(input);
    const status=document.createElement('p');status.className='contest-scan-status';status.setAttribute('role','status');host.append(status);
    const controls=document.createElement('div');controls.className='row';
    const pageSelect=document.createElement('select');pageSelect.setAttribute('aria-label',tr('답안지 쪽 선택','Answer sheet page'));for(const s of model.sheets){const o=document.createElement('option');o.value=s.index;o.textContent=tr(`${s.index+1}쪽 (${s.q0+model.offset}~${s.qn+model.offset}번)`,`Page ${s.index+1}`);pageSelect.append(o);}controls.append(pageSelect);
    const manualButton=button(tr('모서리 네 점 직접 지정','Set four corners'),()=>{if(!image)return;manual=true;points=[];current=null;status.textContent=tr('종이에 인쇄된 표식을 왼쪽 위 → 오른쪽 위 → 오른쪽 아래 → 왼쪽 아래 순서로 누르세요.','Click printed corner markers: top left, top right, bottom right, bottom left.');draw();});
    const rotate=button(tr('사진 90° 회전','Rotate 90°'),()=>{if(!image)return;const c=document.createElement('canvas');c.width=image.height;c.height=image.width;const src=document.createElement('canvas');src.width=image.width;src.height=image.height;src.getContext('2d').putImageData(image,0,0);const ctx=c.getContext('2d');ctx.translate(c.width,0);ctx.rotate(Math.PI/2);ctx.drawImage(src,0,0);image=ctx.getImageData(0,0,c.width,c.height);points=[];manual=false;inspect();});
    const skip=button(tr('현재 파일 건너뛰기','Skip current file'),()=>next());controls.append(manualButton,rotate,skip);host.append(controls);
    const canvas=document.createElement('canvas');canvas.className='contest-scan-image';canvas.setAttribute('aria-label',tr('스캔 답안과 모서리 선택','Scanned answer and corner selection'));host.append(canvas);
    const review=document.createElement('div');review.className='contest-scan-review';host.append(review);const list=document.createElement('div');list.className='contest-scan-pages';host.append(list);
    const done=button(options.confirmLabel||tr('검토한 인식 답안을 채점 양식에 반영','Use reviewed answers for grading'),()=>{if(emitted||accepted.size!==model.sheets.length)return;const marks={},rows=[];for(const s of model.sheets){const page=accepted.get(s.index);Object.assign(marks,page.marks);rows.push(...page.rows);}emitted=true;done.disabled=true;options.onRecognized?.({examId:e.id,marks,rows,pages:[...accepted.keys()].sort((a,b)=>a-b),complete:true,reviewed:true,uncertain:[]});});host.append(done);
    function pages(){list.replaceChildren();for(const s of model.sheets){const row=document.createElement('div');row.className='row';row.append(text(`${s.index+1}쪽: ${accepted.has(s.index)?tr('확인 완료','confirmed'):tr('아직 없음','missing')}`));if(accepted.has(s.index))row.append(button(tr('이 쪽 지우기','Remove page'),()=>{accepted.delete(s.index);pages();}));list.append(row);}done.disabled=emitted||accepted.size!==model.sheets.length;}
    function draw(){if(!image)return;canvas.width=image.width;canvas.height=image.height;const c=canvas.getContext('2d');c.putImageData(image,0,0);points.forEach((p,i)=>{c.fillStyle='#e22';c.beginPath();c.arc(p.x,p.y,Math.max(8,image.width/100),0,Math.PI*2);c.fill();c.fillStyle='white';c.font=`bold ${Math.max(13,image.width/65)}px sans-serif`;c.fillText(i+1,p.x-4,p.y+5);});}
    function inspect(){if(!image)return;review.replaceChildren();current=null;draw();try{
      const anchors=points.length===4?points:detectAnchors(image);let result=null;
      const order=[Number(pageSelect.value),...model.sheets.map(s=>s.index).filter(i=>i!==Number(pageSelect.value))];
      for(const n of order)try{result=recognize(image,model,n,anchors);break;}catch(_){}
      if(!result)throw new Error(tr('표식 또는 시험·쪽 식별 코드를 확인하지 못했습니다. 용지와 촬영 상태를 확인하거나 네 모서리를 직접 지정하세요.','Could not verify markers or the exam/page code. Check the sheet or set its corners.'));
      if(accepted.has(result.sheetIndex))throw new Error(tr(`${result.sheetIndex+1}쪽은 이미 등록되어 있습니다. 아래 목록에서 지운 다음 다시 추가하세요.`,`Page ${result.sheetIndex+1} is already registered. Remove it below before replacing it.`));
      pageSelect.value=String(result.sheetIndex);current=result;status.textContent=tr(`${result.sheetIndex+1}쪽을 인식했습니다. 흐리거나 겹친 마킹 ${result.uncertain.length}개를 확인하세요.`,`Read page ${result.sheetIndex+1}. Review ${result.uncertain.length} uncertain marks.`);showReview();
    }catch(error){status.textContent=error.message;status.classList.add('error');}}
    function showReview(){review.replaceChildren();status.classList.remove('error');const table=document.createElement('table'),tbody=document.createElement('tbody'),unresolved=new Set(current.uncertain);table.innerHTML=`<thead><tr><th>${tr('문항','Question')}</th><th>${tr('인식·수정 답안','Read / correct answer')}</th><th>${tr('상태','Status')}</th></tr></thead>`;table.append(tbody);
      const confirm=button(tr('이 쪽 답안을 확인·사용','Confirm this page'),()=>{if(unresolved.size)return;accepted.set(current.sheetIndex,{...current,reviewed:true});current=null;review.replaceChildren();pages();next();});
      function finishRow(row,value,cell){if(value===null)delete current.marks[row.q];else current.marks[row.q]=value;row.value=value;row.status=value===null?'blank':'marked';unresolved.delete(row.q);cell.textContent=tr('확인함','Reviewed');cell.className='';confirm.disabled=unresolved.size>0;}
      for(const row of current.rows){const trEl=document.createElement('tr'),q=document.createElement('td'),answerCell=document.createElement('td'),state=document.createElement('td');q.textContent=row.number;state.textContent=({marked:tr('마킹','Marked'),blank:tr('빈칸','Blank'),multiple:tr('중복 · 확인 필요','Multiple · review'),uncertain:tr('불확실 · 확인 필요','Unclear · review')})[row.status];state.className=unresolved.has(row.q)?'error':'';
        if(e.kind==='choice'){const sel=document.createElement('select');sel.setAttribute('aria-label',tr(`${row.number}번 답안`,`${row.number} answer`));sel.innerHTML=`<option value="">${tr('미응답','Blank')}</option>`+Array.from({length:e.choices||5},(_,i)=>`<option value="${i+1}">${esc((e.choiceLabels||[])[i]||i+1)}</option>`).join('');sel.value=row.value??'';sel.onchange=()=>finishRow(row,sel.value?Number(sel.value):null,state);answerCell.append(sel);}else{const inp=document.createElement('input');inp.type='text';inp.inputMode='numeric';inp.maxLength=model.digits;inp.setAttribute('aria-label',tr(`${row.number}번 정수 답안`,`${row.number} integer answer`));inp.value=row.value===null?'':String(row.value).padStart(model.digits,'0');inp.oninput=()=>{const v=inp.value.trim();if(/^\d+$/.test(v)&&v.length<=model.digits&&Number.isSafeInteger(Number(v)))finishRow(row,Number(v),state);else{unresolved.add(row.q);confirm.disabled=true;state.textContent=tr('정수 답안을 확인하세요','Check integer answer');state.className='error';}};answerCell.append(inp);}
        answerCell.append(button(tr('미응답으로 확인','Confirm blank'),()=>{finishRow(row,null,state);const el=answerCell.querySelector('input,select');if(el)el.value='';}));trEl.append(q,answerCell,state);tbody.append(trEl);
      }review.append(table,confirm);confirm.disabled=unresolved.size>0;
    }
    async function next(){review.replaceChildren();current=null;points=[];manual=false;active=tasks.shift()||null;if(!active){image=null;canvas.width=canvas.height=1;status.textContent=tr('파일 읽기를 마쳤습니다. 모든 쪽을 확인한 뒤 인식 답안을 반영하세요.','Files processed. Confirm every page, then use the reviewed answers.');return;}const serial=++version;status.textContent=tr('스캔 파일을 읽는 중…','Reading scan…');try{
      let source;if(active.doc){const page=await active.doc.getPage(active.page),vp=page.getViewport({scale:Math.min(3,2200/page.getViewport({scale:1}).width)}),c=document.createElement('canvas');c.width=Math.ceil(vp.width);c.height=Math.ceil(vp.height);await page.render({canvasContext:c.getContext('2d'),viewport:vp}).promise;source=c;}else{const url=URL.createObjectURL(active.file),img=new Image();try{img.src=url;await img.decode();source=img;}finally{URL.revokeObjectURL(url);}}
      if(!alive||serial!==version)return;const scale=Math.min(1,2600/Math.max(source.width,source.height)),c=document.createElement('canvas');c.width=Math.round(source.width*scale);c.height=Math.round(source.height*scale);c.getContext('2d').drawImage(source,0,0,c.width,c.height);image=c.getContext('2d').getImageData(0,0,c.width,c.height);inspect();
    }catch(error){if(alive)status.textContent=error.message;}}
    input.onchange=async()=>{
      const files=[...input.files];input.value='';if(!files.length)return;
      if(files.length>12||files.reduce((n,f)=>n+f.size,0)>80*1024*1024){status.textContent=tr('한 번에 파일 12개·합계 80MB까지 읽을 수 있습니다.','Choose up to 12 files / 80 MB per batch.');return;}
      const prepared=[],docs=[];
      try{
        for(const file of files){
          if(file.type==='application/pdf'||/\.pdf$/i.test(file.name)){
            const lib=await pdfLibrary(),doc=await lib.getDocument({data:new Uint8Array(await file.arrayBuffer())}).promise;docs.push(doc);
            if(doc.numPages>12)throw new Error(tr('스캔 PDF는 12쪽 이하로 나누어 주세요.','Split scan PDFs into at most 12 pages.'));
            for(let p=1;p<=doc.numPages;p++)prepared.push({doc,page:p});
          }else if(file.type.startsWith('image/'))prepared.push({file});
          else throw new Error(tr('사진 또는 PDF를 선택하세요.','Select images or PDFs.'));
          if(prepared.length+tasks.length>24)throw new Error(tr('읽기 대기 중인 파일을 먼저 확인하세요.','Review queued scan pages before adding more.'));
        }
        if(!alive){for(const doc of docs)Promise.resolve(doc.destroy()).catch(()=>{});return;}
        readers.push(...docs);tasks.push(...prepared);if(!active)next();
      }catch(error){for(const doc of docs)try{Promise.resolve(doc.destroy()).catch(()=>{});}catch(_){}status.textContent=error.message;}
    };
    canvas.onclick=event=>{if(!manual||!image)return;const rect=canvas.getBoundingClientRect();points.push({x:(event.clientX-rect.left)*canvas.width/rect.width,y:(event.clientY-rect.top)*canvas.height/rect.height});draw();if(points.length===4){manual=false;inspect();}};
    pageSelect.onchange=()=>{if(image)inspect();};pages();return {dispose(){alive=false;version++;tasks=[];for(const doc of readers)try{Promise.resolve(doc.destroy()).catch(()=>{});}catch(_){}host.replaceChildren();}};
  }
  return {VERSION,layout,svg,print,digitCount,homography,transform,classify,detectAnchors,recognize,mountScan};
});
