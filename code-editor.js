/* A small code editor for the Workshop (create.html), written for the site: a plain <textarea> (so typing, selection,
   the phone keyboard and native undo all stay the browser's own) under a highlighted copy of the text, with line numbers,
   tab and auto-indent, bracket closing and matching, a comment toggle and an error-line mark. JavaScript and Python.
   The pure parts (highlight, line diff, bracket matching) are exported for tests/test-code-editor.cjs. */
(function(root){
  'use strict';
  const esc=s=>s.replace(/[&<>]/g,c=>c==='&'?'&amp;':c==='<'?'&lt;':'&gt;');
  const KW={
    js:new Set('break case catch class const continue debugger default delete do else export extends finally for function if import in instanceof let new of return static super switch this throw try typeof var void while with yield async await true false null undefined NaN Infinity'.split(' ')),
    py:new Set('and as assert async await break class continue def del elif else except False finally for from global if import in is lambda None nonlocal not or pass raise return True try while with yield print range len abs min max sum float int list'.split(' '))
  };
  /* tokens: [type, text]; types: c comment, s string, n number, k keyword, f a call (name before '('), h the helpers (hl, Math), p punctuation, w word, ' ' other */
  function tokens(src,lang){
    const out=[],n=src.length,py=lang==='py';let i=0;
    const push=(t,a,b)=>out.push([t,src.slice(a,b)]);
    while(i<n){
      const c=src[i],d=src[i+1];
      if(!py&&c==='/'&&d==='/'||py&&c==='#'){let j=src.indexOf('\n',i);if(j<0)j=n;push('c',i,j);i=j;continue;}
      if(!py&&c==='/'&&d==='*'){let j=src.indexOf('*/',i+2);j=j<0?n:j+2;push('c',i,j);i=j;continue;}
      if(c==='"'||c==="'"||c==='`'&&!py){
        const triple=py&&src.startsWith(c.repeat(3),i);let j=i+(triple?3:1);
        while(j<n){if(src[j]==='\\'){j+=2;continue;}if(triple?src.startsWith(c.repeat(3),j):src[j]===c){j+=triple?3:1;break;}if(src[j]==='\n'&&c!=='`'&&!triple)break;j++;}
        push('s',i,Math.min(j,n));i=Math.min(j,n);continue;}
      if(/[0-9]/.test(c)||c==='.'&&/[0-9]/.test(d||'')){const hex=/^0[xX]/.test(src.slice(i,i+2));let j=i;while(j<n&&(/[\w.]/.test(src[j])||!hex&&(src[j]==='+'||src[j]==='-')&&/[eE]/.test(src[j-1])&&/[0-9.]/.test(src[j-2]||'')))j++;push('n',i,j);i=j;continue;}
      if(/[A-Za-z_$\u00c0-\uffff]/.test(c)){let j=i;while(j<n&&/[\w$\u00c0-\uffff]/.test(src[j]))j++;const w=src.slice(i,j);
        let k=j;while(k<n&&src[k]===' ')k++;
        push(KW[py?'py':'js'].has(w)?'k':w==='hl'||w==='Math'?'h':src[k]==='('?'f':'w',i,j);i=j;continue;}
      if(/[()[\]{}]/.test(c)){push('p',i,i+1);i++;continue;}
      let j=i+1;while(j<n&&!/[\w$"'`/#()[\]{}.0-9\u00c0-\uffff]/.test(src[j]))j++;push(' ',i,j);i=j;
    }
    return out;
  }
  /* the text as HTML; `marks` are character offsets to wrap as a matched bracket */
  function highlight(src,lang,marks){
    const m=new Set(marks||[]);let pos=0,html='';
    for(const [t,s] of tokens(src,lang)){
      if(t==='p'&&m.has(pos))html+='<span class="ce-bm">'+esc(s)+'</span>';
      else if(t===' '||t==='w'||t==='p')html+=esc(s);
      else html+='<span class="ce-'+t+'">'+esc(s)+'</span>';
      pos+=s.length;
    }
    return html;
  }
  const PAIRS={'(':')','[':']','{':'}'},CLOSE={')':'(',']':'[','}':'{'};
  /* the bracket at or just before `pos` and its partner, ignoring brackets in strings and comments; null when none */
  function matchBracket(src,pos,lang){
    const code=[];let at=0;
    for(const [t,s] of tokens(src,lang)){if(t==='p')code.push(at);at+=s.length;}
    const idx=new Map(code.map((p,i)=>[p,i]));
    for(const p of [pos-1,pos]){
      if(!idx.has(p))continue;const ch=src[p];let k=idx.get(p),depth=0;
      if(PAIRS[ch]){for(let i=k;i<code.length;i++){const c=src[code[i]];if(PAIRS[c])depth++;else if(CLOSE[c]){depth--;if(!depth)return c===PAIRS[ch]?[p,code[i]]:null;}}return null;}
      if(CLOSE[ch]){for(let i=k;i>=0;i--){const c=src[code[i]];if(CLOSE[c])depth++;else if(PAIRS[c]){depth--;if(!depth)return c===CLOSE[ch]?[code[i],p]:null;}}return null;}
    }
    return null;
  }
  /* a line diff: [{op:' '|'-'|'+', text}], common head and tail trimmed, then a longest common subsequence */
  function diffLines(a,b){
    const A=a.split('\n'),B=b.split('\n');let s=0,ea=A.length,eb=B.length;
    while(s<ea&&s<eb&&A[s]===B[s])s++;while(ea>s&&eb>s&&A[ea-1]===B[eb-1]){ea--;eb--;}
    const head=A.slice(0,s).map(t=>({op:' ',text:t})),tail=A.slice(ea).map(t=>({op:' ',text:t}));
    const X=A.slice(s,ea),Y=B.slice(s,eb),n=X.length,m=Y.length,mid=[];
    if(n*m>4e6){for(const t of X)mid.push({op:'-',text:t});for(const t of Y)mid.push({op:'+',text:t});return [...head,...mid,...tail];}
    const L=Array.from({length:n+1},()=>new Uint32Array(m+1));
    for(let i=n-1;i>=0;i--)for(let j=m-1;j>=0;j--)L[i][j]=X[i]===Y[j]?L[i+1][j+1]+1:Math.max(L[i+1][j],L[i][j+1]);
    let i=0,j=0;while(i<n&&j<m){if(X[i]===Y[j]){mid.push({op:' ',text:X[i]});i++;j++;}else if(L[i+1][j]>=L[i][j+1])mid.push({op:'-',text:X[i++]});else mid.push({op:'+',text:Y[j++]});}
    while(i<n)mid.push({op:'-',text:X[i++]});while(j<m)mid.push({op:'+',text:Y[j++]});
    return [...head,...mid,...tail];
  }

  /* ── the widget ── */
  function create(host,opt={}){
    let lang=opt.lang==='py'?'py':'js',errLine=0,marks=[],queued=0,escaped=false;
    host.classList.add('ce');
    host.innerHTML='<div class="ce-gutter" aria-hidden="true"><div class="ce-lines"></div></div><div class="ce-body"><div class="ce-layer"><div class="ce-err" hidden></div><pre class="ce-hl" aria-hidden="true"><code></code></pre></div>'+
      '<textarea class="ce-input" spellcheck="false" autocapitalize="off" autocomplete="off" autocorrect="off" wrap="off"></textarea></div>';
    const ta=host.querySelector('textarea'),code=host.querySelector('code'),layer=host.querySelector('.ce-layer'),lines=host.querySelector('.ce-lines'),errBox=host.querySelector('.ce-err');
    ta.setAttribute('aria-label',opt.label||'code');ta.value=opt.value||'';
    const unit=()=>lang==='py'?'    ':'  ';
    let shownLines=0;
    function paint(){
      queued=0;const v=ta.value;
      code.innerHTML=highlight(v,lang,marks)+'\n ';
      const count=v.split('\n').length;
      if(count!==shownLines||lines.dataset.err!==String(errLine)){shownLines=count;lines.dataset.err=String(errLine);let h='';for(let i=1;i<=count;i++)h+=i===errLine?'<b>'+i+'</b>\n':i+'\n';lines.innerHTML=h;}
      sync();
    }
    const later=()=>{if(!queued)queued=requestAnimationFrame(paint);};
    function sync(){layer.style.transform=`translate(${-ta.scrollLeft}px,${-ta.scrollTop}px)`;lines.style.transform=`translateY(${-ta.scrollTop}px)`;}
    function bracket(){const r=ta.selectionStart===ta.selectionEnd?matchBracket(ta.value,ta.selectionStart,lang):null;const next=r||[];if(next.join()!==marks.join()){marks=next;later();}}
    /* edits go through the browser's own editing command where it has one, so Ctrl+Z undoes them */
    function insert(text,from=ta.selectionStart,to=ta.selectionEnd){
      ta.setSelectionRange(from,to);
      let ok=false;try{ok=document.execCommand('insertText',false,text);}catch(e){}
      if(!ok||ta.value.slice(from,from+text.length)!==text){ta.setRangeText(text,from,to,'end');ta.dispatchEvent(new Event('input'));}
    }
    const lineStart=p=>ta.value.lastIndexOf('\n',p-1)+1;
    function indentLines(out){
      const v=ta.value,s=lineStart(ta.selectionStart),eRaw=ta.selectionEnd,e=v.indexOf('\n',eRaw-(eRaw>ta.selectionStart&&v[eRaw-1]==='\n'?1:0));const end=e<0?v.length:e;
      const block=v.slice(s,end),u=unit();
      const next=block.split('\n').map(l=>out?l.replace(new RegExp('^( {1,'+u.length+'}|\\t)'),''):u+l).join('\n');
      insert(next,s,end);ta.setSelectionRange(s,s+next.length);
    }
    function toggleComment(){
      const v=ta.value,s=lineStart(ta.selectionStart),e0=v.indexOf('\n',ta.selectionEnd),end=e0<0?v.length:e0,mark=lang==='py'?'# ':'// ';
      const ls=v.slice(s,end).split('\n'),all=ls.filter(l=>l.trim()).every(l=>l.trimStart().startsWith(mark.trim()));
      const next=ls.map(l=>{if(!l.trim())return l;if(all)return l.replace(new RegExp('^(\\s*)'+mark.trim().replace(/[/#]/g,'\\$&')+' ?'),'$1');const ind=/^\s*/.exec(l)[0];return ind+mark+l.slice(ind.length);}).join('\n');
      insert(next,s,end);ta.setSelectionRange(s,s+next.length);
    }
    ta.addEventListener('keydown',e=>{
      const mod=e.ctrlKey||e.metaKey;
      if(e.key==='Escape'){escaped=true;return;}
      if(e.key==='Tab'&&!mod&&!e.altKey){if(escaped){escaped=false;return;}e.preventDefault();
        if(e.shiftKey||ta.selectionStart!==ta.selectionEnd&&ta.value.slice(ta.selectionStart,ta.selectionEnd).includes('\n'))indentLines(e.shiftKey);else insert(unit());return;}
      escaped=false;
      if(mod&&e.key==='Enter'){e.preventDefault();opt.onRun&&opt.onRun();return;}
      if(mod&&(e.key==='s'||e.key==='S')){e.preventDefault();opt.onSave&&opt.onSave();return;}
      if(mod&&e.key==='/'){e.preventDefault();toggleComment();return;}
      if(e.key==='Enter'&&!mod&&!e.shiftKey&&!e.altKey&&!e.isComposing){
        e.preventDefault();const v=ta.value,p=ta.selectionStart,s=lineStart(p),ind=/^[ \t]*/.exec(v.slice(s,p))[0];
        const before=v.slice(s,p).trimEnd(),after=v[ta.selectionEnd]||'';
        const open=lang==='py'?/:$/.test(before):/[{[(]$/.test(before);
        if(open&&lang!=='py'&&PAIRS[before.slice(-1)]===after){insert('\n'+ind+unit()+'\n'+ind);const q=p+1+ind.length+unit().length;ta.setSelectionRange(q,q);}
        else insert('\n'+ind+(open?unit():''));
        return;
      }
      if(!mod&&!e.altKey&&e.key.length===1&&!e.isComposing){
        const v=ta.value,p=ta.selectionStart,next=v[p]||'';
        if(ta.selectionStart===ta.selectionEnd&&(CLOSE[e.key]||e.key==='"'||e.key==="'")&&next===e.key){e.preventDefault();ta.setSelectionRange(p+1,p+1);bracket();return;}
        if(PAIRS[e.key]&&ta.selectionStart===ta.selectionEnd&&(!next||/[\s)\]};,]/.test(next))){e.preventDefault();insert(e.key+PAIRS[e.key]);ta.setSelectionRange(p+1,p+1);return;}
      }
      if(e.key==='Backspace'&&ta.selectionStart===ta.selectionEnd){const v=ta.value,p=ta.selectionStart;if(p>0&&PAIRS[v[p-1]]===v[p]){e.preventDefault();insert('',p-1,p+1);}}
    });
    ta.addEventListener('input',()=>{if(errLine){errLine=0;errBox.hidden=true;}later();bracket();opt.onChange&&opt.onChange(ta.value);});
    ta.addEventListener('scroll',sync,{passive:true});
    for(const t of ['keyup','click','focus'])ta.addEventListener(t,bracket);
    ta.addEventListener('blur',()=>{if(marks.length){marks=[];later();}});
    paint();
    return {
      el:ta,
      get value(){return ta.value;},
      /* replace the whole text; undoable with Ctrl+Z when the browser lets the edit through its own command */
      setValue(v,{undoable=false}={}){v=String(v??'');if(v===ta.value)return;if(undoable){const s=ta.scrollTop;insert(v,0,ta.value.length);ta.setSelectionRange(0,0);ta.scrollTop=s;}else{ta.value=v;paint();opt.onChange&&opt.onChange(v);}},
      setLang(l){lang=l==='py'?'py':'js';later();},
      get lang(){return lang;},
      insert(text){ta.focus();insert(text);},
      focus(){ta.focus();},
      markError(line){
        errLine=line>0?line:0;
        if(errLine){const lh=parseFloat(getComputedStyle(ta).lineHeight)||20,pad=parseFloat(getComputedStyle(ta).paddingTop)||0;errBox.style.top=(pad+(errLine-1)*lh)+'px';errBox.style.height=lh+'px';errBox.hidden=false;
          const top=pad+(errLine-1)*lh;if(top<ta.scrollTop||top>ta.scrollTop+ta.clientHeight-lh)ta.scrollTop=Math.max(0,top-ta.clientHeight/3);}
        else errBox.hidden=true;
        paint();
      },
      gotoLine(line){const v=ta.value;let p=0;for(let i=1;i<line&&p>=0;i++)p=v.indexOf('\n',p)+1;if(p<0)p=v.length;ta.focus();ta.setSelectionRange(p,p);const lh=parseFloat(getComputedStyle(ta).lineHeight)||20;ta.scrollTop=Math.max(0,(line-4)*lh);}
    };
  }
  const api={create,highlight,tokens,matchBracket,diffLines};
  if(typeof module==='object'&&module.exports)module.exports=api;else root.HL_EDITOR=api;
})(typeof window!=='undefined'?window:this);
