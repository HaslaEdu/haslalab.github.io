const test=require('node:test'),assert=require('node:assert/strict');
const p=require('../sim/contest-paper.js');
const choice={id:'kmchc-test',kind:'choice',questions:60,choices:4,title:{ko:'한국중학생화학대회 연습 답안지'},questionOffset:0};
function polygon(image,points,color){const minx=Math.max(0,Math.floor(Math.min(...points.map(p=>p.x)))),maxx=Math.min(image.width-1,Math.ceil(Math.max(...points.map(p=>p.x)))),miny=Math.max(0,Math.floor(Math.min(...points.map(p=>p.y)))),maxy=Math.min(image.height-1,Math.ceil(Math.max(...points.map(p=>p.y))));for(let y=miny;y<=maxy;y++)for(let x=minx;x<=maxx;x++){let inside=false;for(let i=0,j=points.length-1;i<points.length;j=i++){const a=points[i],b=points[j];if((a.y>y)!==(b.y>y)&&x<(b.x-a.x)*(y-a.y)/(b.y-a.y)+a.x)inside=!inside;}if(inside){const k=(y*image.width+x)*4;image.data[k]=image.data[k+1]=image.data[k+2]=color;}}}
function scan(model,index,marks={},dest=[{x:50,y:50},{x:1000,y:50},{x:1000,y:1435},{x:50,y:1435}]){
 const image={width:1100,height:1500,data:new Uint8ClampedArray(1100*1500*4).fill(255)},sheet=model.sheets[index],h=p.homography(sheet.anchors,dest);
 const shape=(x,y,rx,ry,color)=>polygon(image,[[-1,-1],[1,-1],[1,1],[-1,1]].map(([a,b])=>p.transform(h,x+a*rx,y+b*ry)),color);
 const circle=(x,y,r,color)=>polygon(image,Array.from({length:24},(_,i)=>p.transform(h,x+r*Math.cos(i*Math.PI/12),y+r*Math.sin(i*Math.PI/12))),color);
 for(const a of sheet.anchors)shape(a.x,a.y,3.5,3.5,0);
 for(const c of sheet.code)if(c.bit)shape(c.x,c.y,c.size/2,c.size/2,0);
 for(const b of sheet.bubbles){circle(b.x,b.y,b.r,0);circle(b.x,b.y,b.r-.18,255);const mark=marks[b.q];let fill=false;if(model.kind==='choice')fill=(Array.isArray(mark)?mark:[mark]).includes(b.value);else if(mark!==undefined){const digits=String(mark).padStart(model.digits,'0');fill=digits[b.column]===String(b.value);}if(fill)circle(b.x,b.y,b.r*.88,0);}
 return {image,points:dest};
}
function rotate(image){const out={width:image.height,height:image.width,data:new Uint8ClampedArray(image.data.length)};for(let y=0;y<image.height;y++)for(let x=0;x<image.width;x++){const a=(y*image.width+x)*4,b=(x*out.width+out.width-y-1)*4;out.data.set(image.data.subarray(a,a+4),b);}return out;}
test('A4 layouts keep every bubble and marker inside the printable sheet with stable per-page identity',()=>{
 for(const e of [choice,{...choice,kind:'integer',questions:20,digits:3},{...choice,kind:'integer',questions:25,answerMax:null,answers:[1234567]},{...choice,kind:'integer',questions:20,answerMax:null,answers:[999999999999999]}]){const m=p.layout(e);assert.ok(m.sheets.length);for(const s of m.sheets){assert.ok(s.code.length>=24);for(const b of s.bubbles){assert.ok(b.x-b.r>14&&b.x+b.r<196);assert.ok(b.y-b.r>63&&b.y+b.r<280);}}}
 const a=p.layout(choice),b=p.layout({...choice,id:'different'});assert.notDeepEqual(a.sheets[0].code,b.sheets[0].code);
});
test('perspective registration reads black marking, preserves blanks and flags duplicate choices',()=>{
 const m=p.layout(choice),{image,points}=scan(m,0,{1:3,2:[1,4],60:2},[{x:60,y:40},{x:1010,y:90},{x:1060,y:1450},{x:35,y:1410}]);
 const r=p.recognize(image,m,0,points);assert.equal(r.marks[1],3);assert.equal(r.marks[60],2);assert.equal(r.rows[1].status,'multiple');assert.equal(r.rows[2].status,'blank');assert.ok(r.uncertain.includes(2));
});
test('automatic anchors and rotated photos retain sheet identity',()=>{
 const m=p.layout(choice),{image}=scan(m,0,{1:4,59:2});assert.ok(p.detectAnchors(image));assert.equal(p.recognize(image,m).marks[1],4);const rotated=rotate(image);assert.equal(p.recognize(rotated,m).marks[59],2);
});
test('a different exam/page code or missing registration is rejected instead of becoming a blank submission',()=>{
 const m=p.layout(choice),{image}=scan(m,0);assert.throws(()=>p.recognize(image,p.layout({...choice,id:'other-exam'})),/식별/);const blank={...image,data:new Uint8ClampedArray(image.data.length).fill(255)};assert.throws(()=>p.recognize(blank,m),/표식/);
});
test('integer sheets preserve leading zeroes, unrestricted historical digits and displayed question offsets',()=>{
 const m=p.layout({...choice,kind:'integer',questions:4,digits:3,questionOffset:10}),{image,points}=scan(m,0,{1:7,2:0,4:999});const r=p.recognize(image,m,0,points);assert.equal(r.marks[1],7);assert.equal(r.rows[0].rawDigits,'007');assert.equal(r.marks[2],0);assert.equal(r.rows[0].number,11);assert.equal(r.rows[2].status,'blank');
 const large=p.layout({...choice,kind:'integer',questions:1,answerMax:null,answers:[23252]});assert.ok(large.digits>=5);const x=scan(large,0,{1:23252});assert.equal(p.recognize(x.image,large,0,x.points).marks[1],23252);
});
test('proof forms provide separate question pages and additional working pages without a machine-grading grid',()=>{
 const e={id:'proof',kind:'proof',questions:4,questionOffset:4,points:[7,7,7,7],title:{ko:'고등부 2차 2교시'}},m=p.layout(e,{extraSheets:1});assert.equal(m.sheets.length,5);assert.ok(m.sheets.every(s=>s.bubbles.length===0));assert.match(p.svg(e,0),/5번 풀이/);assert.match(p.svg(e,0),/7점/);
});
