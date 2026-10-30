"""Manually constructed geometry and native-font outlines for 2023 KPhE figures.

No source pixels, contour tracing, or raster objects enter any output asset.
Original crops are reference evidence only (tmp/kphe_redraw_cd_qa).
"""
from __future__ import annotations
import hashlib,json,math,sys
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape
import pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path
from kphe_fonts import font_path,equation_fonts
from kphe_legacy_equations import legacy_equation_fonts

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools/kphe_redraw/cd'
INK='#161616';GRAY='#bababa';LIGHT='#e4e4e4'
_REGISTERED=set()

@lru_cache(None)
def ft(path):return TTFont(path)
@lru_cache(None)
def glyph(path,code):
 f=ft(path);name=f.getBestCmap().get(code)
 if name is None:raise ValueError(f'Native font lacks U+{code:04X}: {path}')
 pen=SVGPathPen(f.getGlyphSet());f.getGlyphSet()[name].draw(pen)
 return pen.getCommands(),f['hmtx'][name][0],f['head'].unitsPerEm

@lru_cache(None)
def equation(expr,size,face):
 import matplotlib
 from matplotlib.mathtext import MathTextParser
 from matplotlib.font_manager import FontProperties,fontManager
 roman,italic=legacy_equation_fonts()if face=='HyhwpEQ'else equation_fonts()
 for p in [roman,italic,font_path('TimesNewRomanPS-BoldMT')]:
  if str(p)not in _REGISTERED:fontManager.addfont(str(p));_REGISTERED.add(str(p))
 family=f'KPhE {face}'
 matplotlib.rcParams.update({'mathtext.fontset':'custom','mathtext.rm':family+' Roman','mathtext.it':family+' Italic','mathtext.bf':'Times New Roman:weight=bold','mathtext.sf':family+' Roman','mathtext.tt':family+' Roman','mathtext.cal':'STIXGeneral:style=italic','mathtext.fallback':'stix'})
 return MathTextParser('path').parse('$'+expr+'$',dpi=72,prop=FontProperties(family=family+' Roman',size=size))

class SVG:
 def __init__(self,w=300,h=180,face='HancomEQN'):
  self.w,self.h,self.face=w,h,face;self.scale=min(1,232/w);self.items=[]
 def add(self,s):self.items.append(s)
 def dashed(self,pts,dash,width,color):
  pattern=[float(v)for v in dash.replace(',',' ').split()];pattern=pattern if len(pattern)%2==0 else pattern*2
  phase=0;remain=pattern[0]
  for a,b in zip(pts,pts[1:]):
   length=math.dist(a,b)
   if length<1e-8:continue
   done=0
   while done<length-1e-8:
    step=min(remain,length-done);p=(a[0]+(b[0]-a[0])*done/length,a[1]+(b[1]-a[1])*done/length);q=(a[0]+(b[0]-a[0])*(done+step)/length,a[1]+(b[1]-a[1])*(done+step)/length)
    if phase%2==0:self.line(*p,*q,width,color)
    done+=step;remain-=step
    if remain<1e-8:phase=(phase+1)%len(pattern);remain=pattern[phase]
 def line(self,x1,y1,x2,y2,width=1,color=INK,dash=None):
  if dash:self.dashed([(x1,y1),(x2,y2)],dash,width,color);return
  self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"'+(f' stroke-dasharray="{dash}"'if dash else'')+'/>')
 def path(self,d,width=1,color=INK,fill='none',dash=None):
  if dash:
   assert fill=='none'
   pen=RecordingPen();parse_path(d,pen);pts=[];start=None
   for op,args in pen.value:
    if op=='moveTo':
     if pts:self.dashed(pts,dash,width,color)
     pts=[args[0]];start=args[0]
    elif op=='lineTo':pts.append(args[0])
    elif op=='curveTo':
     p=pts[-1];c1,c2,end=args
     for j in range(1,81):
      t=j/80;u=1-t;pts.append((u**3*p[0]+3*u*u*t*c1[0]+3*u*t*t*c2[0]+t**3*end[0],u**3*p[1]+3*u*u*t*c1[1]+3*u*t*t*c2[1]+t**3*end[1]))
    elif op=='qCurveTo':
     p=pts[-1];c,end=args
     for j in range(1,81):
      t=j/80;u=1-t;pts.append((u*u*p[0]+2*u*t*c[0]+t*t*end[0],u*u*p[1]+2*u*t*c[1]+t*t*end[1]))
    elif op=='closePath':pts.append(start)
   if pts:self.dashed(pts,dash,width,color)
   return
  self.add(f'<path d="{d}" stroke="{color}" stroke-width="{width}" fill="{fill}"'+(f' stroke-dasharray="{dash}"'if dash else'')+'/>')
 def poly(self,pts,width=1,color=INK,fill='none',close=False,dash=None):
  if dash:self.dashed(list(pts)+([pts[0]]if close else[]),dash,width,color);return
  self.path('M '+' L '.join(f'{x},{y}'for x,y in pts)+(' Z'if close else''),width,color,fill,dash)
 def rect(self,x,y,w,h,fill='none',stroke=INK,width=1):self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')
 def ellipse(self,x,y,rx,ry,fill='none',stroke=INK,width=1,dash=None):
  if dash:
   assert fill=='none';self.dashed([(x+rx*math.cos(i*math.pi/180),y+ry*math.sin(i*math.pi/180))for i in range(361)],dash,width,stroke);return
  self.add(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')
 def circle(self,x,y,r,fill='none',stroke=INK,width=1):self.ellipse(x,y,r,r,fill,stroke,width)
 def arrow(self,x1,y1,x2,y2,width=1,color=INK,head=5,both=False,dash=None):
  angle=math.atan2(y2-y1,x2-x1);ux,uy=math.cos(angle),math.sin(angle)
  pad=min(head*.65,math.hypot(x2-x1,y2-y1)*.3)
  self.line(x1+(pad*ux if both else 0),y1+(pad*uy if both else 0),x2-pad*ux,y2-pad*uy,width,color,dash)
  def tip(x,y,a):
   ux,uy=math.cos(a),math.sin(a);self.poly([(x,y),(x-head*ux+head*.6*uy,y-head*uy-head*.6*ux),(x-head*ux-head*.6*uy,y-head*uy+head*.6*ux)],0,color,color,True)
  a=math.atan2(y2-y1,x2-x1);tip(x2,y2,a)
  if both:tip(x1,y1,a+math.pi)
 def arc(self,cx,cy,rx,ry,a1,a2,width=1,dash=None,arrow=False):
  pts=[(cx+rx*math.cos(math.radians(a1+(a2-a1)*i/60)),cy+ry*math.sin(math.radians(a1+(a2-a1)*i/60)))for i in range(61)]
  self.poly(pts,width=width,dash=dash)
  if arrow:self.arrow(*pts[-3],*pts[-1],width,head=4)
 def text(self,s,x,y,size=12,anchor='middle',color=INK,font='Gulim'):
  size=min(9.8,max(8.8,size*self.scale))/self.scale
  p=str(font_path(font));gs=[glyph(p,ord(c))for c in s];width=sum(a/u*size for _,a,u in gs);xx=x-width/2 if anchor=='middle'else x-width if anchor=='end'else x
  for d,a,u in gs:
   if d:self.add(f'<path d="{d}" fill="{color}" transform="translate({xx:.4f},{y:.4f}) scale({size/u:.7f},{-size/u:.7f})"/>')
   xx+=a/u*size
 def math(self,s,x,y,size=13,anchor='middle',color=INK):
  size=min(9.8,max(8.5,size*self.scale))/self.scale
  p=equation(s,size,self.face);xx=x-p.width/2 if anchor=='middle'else x-p.width if anchor=='end'else x
  for item in p.glyphs:
   f,sz,code=item[:3];gx,gy=item[-2:]
   d,_,u=glyph(str(f.fname),code)
   self.add(f'<path d="{d}" fill="{color}" transform="translate({xx+gx:.4f},{y-gy:.4f}) scale({sz/u:.7f},{-sz/u:.7f})"/>')
  for rx,ry,rw,rh in p.rects:self.rect(xx+rx,y-ry-rh,rw,rh,color,'none',0)
 def resistor(self,x1,y1,x2,y2,n=6,amp=5):
  dx,dy=x2-x1,y2-y1;ll=math.hypot(dx,dy);ux,uy=dx/ll,dy/ll;pts=[(x1,y1),(x1+dx*.12,y1+dy*.12)]
  for i in range(2*n+1):
   t=.14+.72*i/(2*n);off=amp*(1 if i%2 else-1);pts.append((x1+dx*t-uy*off,y1+dy*t+ux*off))
  pts.extend([(x1+dx*.88,y1+dy*.88),(x2,y2)]);self.poly(pts,1.1)
 def spring(self,x1,y1,x2,y2,n=9,amp=7):self.resistor(x1,y1,x2,y2,n,amp)
 def battery(self,x,y,size=12,horizontal=True):
  if horizontal:self.line(x-3,y-size*.6,x-3,y+size*.6,2.4);self.line(x+3,y-size,x+3,y+size,1.2)
  else:self.line(x-size*.6,y-3,x+size*.6,y-3,2.4);self.line(x-size,y+3,x+size,y+3,1.2)
 def ground(self,x,y,w=25):
  self.line(x-w/2,y,x+w/2,y)
  for t in range(0,int(w),4):self.line(x-w/2+t,y,x-w/2+t-4,y+5,.7)
 def svg(self):return f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w*self.scale}pt" height="{self.h*self.scale}pt" viewBox="0 0 {self.w} {self.h}"><g stroke-linecap="round" stroke-linejoin="round">'+''.join(self.items)+'</g></svg>'

def cylinder(s,x,y,w,h,shade=GRAY):
 s.path(f'M{x},{y-h/2} L{x+w},{y-h/2} A{h*.22},{h/2} 0 0 1 {x+w},{y+h/2} L{x},{y+h/2} A{h*.22},{h/2} 0 0 1 {x},{y-h/2} Z',fill=shade)
 s.ellipse(x+w,y,h*.22,h/2,shade)
def prism(s,x,y,w,h,depth=8,fill=LIGHT):
 s.rect(x,y,w,h,fill);s.poly([(x,y),(x+depth,y-depth),(x+w+depth,y-depth),(x+w,y)],fill=fill,close=True);s.poly([(x+w,y),(x+w+depth,y-depth),(x+w+depth,y+h-depth),(x+w,y+h)],fill=fill,close=True)

DRAW={}
def figure(part,num):
 def deco(fn):DRAW[(part,num)]=fn;return fn
 return deco

@figure('T1c',1)
def t1c1():
 s=SVG(190,190);s.rect(15,8,160,20,'#777','none');s.text('절연체',40,22,11,color='white');s.circle(95,29,2.4,INK);s.line(95,29,46,134);s.line(95,29,144,134)
 for x in[45,145]:s.circle(x,143,18,'#c8c8c8');s.math('+Q',x,148,15)
 s.math('m',17,149);s.math('m',173,149);s.arrow(95,136,95,180);s.math('g',106,169);return s

@figure('T1c',3)
def t1c3():
 s=SVG(310,190);prism(s,38,71,68,24,7,'#e73e2d');s.text('N',98,88,10);prism(s,223,71,68,24,7,'#7592b8');s.text('S',230,88,10)
 for dx in[0,4,8,12]:s.poly([(153+dx,142),(153+dx,40),(181+dx,10),(181+dx,113),(153+dx,142)],.8,color='#666')
 s.text('코일',145,26,10);s.ellipse(132,139,13,24,'#c9c9c9');s.poly([(22,157),(104,157),(119,140)]);s.poly([(22,178),(116,178),(129,161)]);s.rect(3,145,72,40,'#f3f3f3');s.text('구조요청용',39,161,10);s.text('전파발신기',39,176,10)
 s.line(138,124,207,51,.8,dash='3 2');s.arc(204,50,12,11,235,580,arrow=True);s.text('회전',228,45,10);return s

@figure('T1c',4)
def t1c4():
 s=SVG(250,170);s.poly([(22,30),(22,143),(225,143),(225,30)]);s.line(22,30,49,30);s.battery(53,30);s.line(58,30,114,30)
 for y,n in[(30,1),(86,2),(143,3)]:
  if n>1:s.line(22,y,114,y)
  s.resistor(114,y,192,y);s.line(192,y,225,y);s.math('R_'+str(n),154,y-12)
 s.math('E',53,56);return s

@figure('T1c',5)
def t1c5():
 s=SVG(320,210);s.rect(22,10,224,133,'#bcbaba');s.text('신용카드',62,31,12);s.text('0000-1111-2222-3333',39,62,11,anchor='start');s.text('02/24',39,77,11,anchor='start');s.text('한국물리학회',39,92,11,anchor='start');s.rect(22,101,224,32,'#8f8a86')
 pattern='NNSSNSNN S'.replace(' ','')
 for i,c in enumerate(pattern):
  for j,p in enumerate([c,'S'if c=='N'else'N']):s.rect(30+16*i,105+13*j,12,12,'#e83328'if p=='N'else'#4278c2','none');s.text(p,36+16*i,115+13*j,9)
 s.text('마그네틱 띠',210,113,9);s.arrow(258,91,311,91);s.text('카드 긁는',282,65,9);s.text('방향',282,79,9)
 for y in[154,159,164,169]:s.ellipse(123,y,36,5)
 s.poly([(91,151),(10,191),(47,191)]);s.poly([(157,171),(105,191),(68,191)]);s.circle(57,191,11);s.text('V',57,196,12);s.text('유도 코일 + 회로',175,197,10);return s

@figure('T1c',7)
def t1c7():
 s=SVG(320,165);cylinder(s,94,85,78,140,'#7e7e7e');cylinder(s,177,90,61,89,'#b5b0ac');s.text('고정됨',126,89,12)
 s.arrow(10,83,75,83,12,'#aaa',15);s.arrow(309,83,257,83,12,'#aaa',15);s.text('힘 N',37,73,11);s.text('힘 N',284,73,11)
 s.text('접촉면',243,14,10);s.text('운동마찰계수',259,27,10);s.math(r'\mu',307,27,11)
 s.arrow(241,65,241,115,both=True);s.text('상하',198,58,10);s.text('진동',198,72,10);s.text('(진동수',198,86,10);s.math('f,',198,100,10);s.text('진폭',198,114,10);s.math('A)',198,128,10);return s

@figure('T1c',8)
def t1c8():
 s=SVG(320,112);s.rect(8,15,125,88);s.line(70,15,70,103,width=.7);s.rect(188,15,125,88);s.line(250,15,250,103,dash='3 2',color='#999')
 left=[(23,27),(62,27),(30,41),(58,44),(24,61),(40,70),(59,72),(59,85),(24,93),(48,98)]
 right=[(204,27),(243,28),(282,34),(305,46),(237,46),(205,61),(266,65),(289,77),(229,97),(297,94)]
 for x,y in left+right:s.circle(x,y,3.8,'#888')
 s.arrow(150,59,177,59,10,'#aaa',10);return s

@figure('T1c',9)
def t1c9():
 s=SVG(260,185);s.arrow(18,165,253,165);s.arrow(33,180,33,8);s.math('P',24,15);s.math('V',250,180)
 s.line(88,165,88,104,dash='3 2');s.line(191,165,191,135,dash='3 2');s.arrow(88,103,88,29)
 s.path('M88,29 C115,48 143,63 191,72');s.arrow(174,69,191,72);s.arrow(191,72,191,135)
 s.path('M191,135 C148,131 113,119 88,103');s.arrow(104,114,88,103)
 s.text('등적가열',60,65,11);s.text('(점화)',60,79,11);s.text('단열팽창',149,37,11);s.text('등적냉각',223,105,11);s.text('단열압축',140,145,11)
 s.math('V_i',88,182);s.math('V_f=rV_i',191,182,12);return s

@figure('T1c',10)
def t1c10():
 s=SVG(320,145)
 for cx in[80,246]:s.ellipse(cx,67,52,52,dash='2 2')
 s.circle(80,67,24,'white');s.math('+',80,73,18);s.text('양성자',80,106,10);s.circle(117,29,9,'white');s.math('-',117,33);s.text('전자',121,13,10)
 s.circle(194,67,9,'white');s.math('+',194,72);s.text('양전자',222,72,10);s.circle(298,67,9,'white');s.math('-',298,72);s.text('전자',281,53,10)
 s.text('“수소 원자”',80,138,11);s.text('“포지트로늄”',246,138,11);return s

@figure('T1c',11)
def t1c11():
 s=SVG(240,185);s.text('원자',115,14,11);s.text('중성자',30,39,11)
 for y in[50,77,104,131,158]:s.arrow(8,y,51,y,2.5,'#888',9)
 for y in[31,54,77,100,123,146,169]:s.circle(116,y,6,INK)
 s.arrow(103,57,103,74,.6,both=True,head=3);s.math('d',96,70,10)
 for y in[77,123]:
  for r in[10,17,24]:s.arc(118,y,r,r,-35,35,.8)
 s.line(221,24,221,174)
 pts=[]
 for i in range(401):
  y=25+149*i/400;amp=8+18*math.exp(-((y-102)/45)**2);pts.append((221-amp*(.5+.5*math.cos((y-39)*2*math.pi/16)),y))
 s.poly(pts,.8,color='#666');s.arrow(123,180,221,180,.6,both=True,head=3);s.math('L',174,176,10);return s

@figure('T1c',12)
def t1c12():
 s=SVG(300,160);s.rect(35,47,239,62,'#b4b0ac','none');s.arrow(35,109,291,109);s.arrow(121,154,121,19);s.math('x',288,124);s.math('y',111,23);s.math('0',132,123);s.math('d',132,42)
 s.arrow(44,148,121,109);s.path('M121,109 Q142.8,87.2 166,47');s.arrow(157,62.6,166,47);s.arrow(166,47,235,13);s.line(166,17,166,89,.7,dash='2 2')
 s.arc(121,109,18,18,90,151,.7);s.math(r'60^\circ',110,146,10);s.arc(166,47,17,17,90,120,.7);s.math(r'\theta_i',151,88,11);s.arc(166,47,15,15,-90,-26,.7);s.math(r'\theta_f',182,31,11)
 s.text('진공',246,34,11);s.text('투명판',245,80,11);s.math('n(y)',245,96);s.text('진공',246,132,11);return s

@figure('T1c',13)
def t1c13():
 s=SVG(320,110)
 for off,case in[(0,'a'),(164,'b')]:
  cx=off+80;s.ellipse(cx,57,72,24,dash='1 2',stroke='#555');s.rect(cx-1.5,16,3,79,'#eee');s.text('('+case+')',off+10,17,10)
  a=(off+28,76);b=(off+132,38)
  s.line(*a,*b,1.3 if case=='a' else 5)
  if case=='a':s.circle(*a,4,'#888');s.circle(*b,4,'#888');s.math('m',off+17,86,11);s.math('m',off+142,36,11)
  else:s.math('2m',off+61,52,11)
  s.arrow(b[0],b[1],b[0]-20,b[1]-11,.7,head=4);s.math('F',b[0]-15,b[1]-17,11);s.arrow(a[0],a[1]+7,b[0],b[1]+7,.5,both=True,head=3);s.math('L',off+102,70,11)
 return s

@figure('T1c',14)
def t1c14():
 s=SVG(200,155);s.rect(12,140,180,10,'#ddd');s.rect(53,58,104,82,'#eee');s.rect(86,30,34,28);s.math('m_1',103,49,15);s.text('M',105,107,20);s.circle(168,42,5);s.poly([(120,39),(166,39),(173,42),(173,80)]);s.rect(158,80,35,27);s.math('m_2',176,98,15);s.arrow(12,93,45,93);s.math('F',27,83);return s

@figure('T1c',16)
def t1c16():
 s=SVG(220,180);s.circle(33,35,8,'#aaa');s.line(40,35,170,35,2.3);s.circle(170,35,2.2,INK);s.line(170,35,170,164);s.path('M33,35 A137,129 0 0 0 170,164',.7,dash='2 2')
 s.arrow(33,19,170,19,.7,both=True,head=4);s.math('l',103,13);s.math('m',45,53);s.circle(170,110,2.2,INK);s.math('P',159,114);s.arrow(182,35,182,110,.7,both=True,head=4);s.math('x',194,77);s.line(170,35,193,35,.6,dash='2 2');s.line(170,110,193,110,.6,dash='2 2');s.line(170,110,187,127);s.text('막대기',201,137,11);return s

@figure('T1c',17)
def t1c17():
 s=SVG(175,195);s.ellipse(81,151,67,25,dash='2 2');s.line(81,151,81,16,.8,dash='2 2');s.line(81,16,142,157);s.circle(142,157,5,'#bbb');s.math('m',161,167);s.arrow(87,13,149,145,.7,both=True,head=4);s.math('l',128,76)
 s.arc(81,16,21,21,66,90,.8);s.math(r'\theta',94,51);s.arrow(81,151,48,174,.7,both=True,head=4);s.math('r',63,152);return s

@figure('T1c',19)
def t1c19():
 s=SVG(190,180);cx,cy,r=94,101,69;s.circle(cx,cy,r);s.circle(cx,cy,1.2,INK);s.line(cx,cy,cx,33,.8,dash='2 2');s.line(47,51,141,51);s.circle(47,51,2.5,'white');s.circle(141,51,2.5,'white');s.text('서울',27,55,11);s.text('부산',162,55,11);s.arrow(47,45,141,45,.6,both=True,head=3);s.math('d',91,41);s.arrow(cx,cy,151,62,.6,dash='2 2',head=3);s.math('R',133,89);return s

@figure('T1c',21)
def t1c21():
 s=SVG(300,205);o=(145,18);r=137
 s.arc(*o,r,r,0,145,.7);s.line(145,18,145,155,.6,color='#aaa');s.line(145,18,282,18,.6,color='#aaa')
 for ang,c in[(90,'A'),(60,'B'),(30,'C'),(0,'D')]:
  x=145+r*math.cos(math.radians(ang));y=18+r*math.sin(math.radians(ang));s.line(145,18,x,y,.6,color='#aaa');s.circle(x,y,1.2,'#666');s.math(c,x+8,y+4,11)
 for ang in[15,45,75]:s.math(r'30^\circ',145+42*math.cos(math.radians(ang)),18+42*math.sin(math.radians(ang)),10)
 bx,by=59,127;s.line(145,18,bx,by,1.4);s.math('R',93,72)
 # Seated person assembled from independently drawn body/limb primitives.
 s.circle(bx-9,by-9,5.5,INK);s.path(f'M{bx-13},{by-4} Q{bx-17},{by+4} {bx-9},{by+13} L{bx+4},{by+16} L{bx+10},{by+31} L{bx+17},{by+34} L{bx+16},{by+29} L{bx+9},{by+9} L{bx-1},{by+7} L{bx-1},{by-1} Z',fill=INK)
 s.poly([(bx-9,by+3),(bx+2,by+5),(bx+12,by-4)],3.8);s.poly([(bx-7,by+13),(bx-20,by+15),(bx-24,by+10)],4);s.circle(bx,by+13,2.8,'#efcf50');s.math('m',bx-19,by+25,11)
 s.rect(6,185,288,12,INK);s.line(145,155,145,185,.6,dash='2 2');s.math('R/4',133,178,11);s.arrow(146,181,289,181,.6,both=True,head=4);s.math('d',219,174,11);return s

@figure('T1c',22)
def t1c22():
 s=SVG(300,155);s.rect(92,11,202,113);s.ellipse(42,104,32,19);s.text('관찰자',42,101,11);s.text('A',42,115,11);s.ellipse(129,55,32,20);s.text('관찰자',129,52,11);s.text('B',129,66,11);s.rect(164,48,68,12,'#999');s.rect(233,22,56,54);s.text('굴절률',260,51,11);s.math('n',283,51);s.text('레이저 (파장 λ)',194,96,10);s.arrow(183,78,214,78);s.circle(130,135,17,'#999');s.circle(256,135,17,'#999');s.arrow(168,147,215,147);s.math('v',190,139);return s

@figure('T1c',23)
def t1c23():
 s=SVG(218,170);s.circle(19,71,7,'white');s.math(r'\pi',15,56,16);s.arrow(26,71,85,71);s.circle(100,71,18,'white');s.math('p',126,80,16)
 s.arrow(115,62,187,25);s.circle(190,23,9,INK);s.math(r'\pi',205,18,16);s.arrow(110,86,150,132);s.circle(156,140,17,INK);s.math('p',178,162,16);return s

@figure('T1c',24)
def t1c24():
 s=SVG(190,220)
 for y in[10,104]:
  s.rect(15,y,128,58);s.circle(37,y+67,14,'#999');s.circle(121,y+67,14,'#999')
 s.ellipse(79,40,28,16);s.text('관찰자',79,38,10);s.text('A',79,51,10);s.arrow(58,81,100,81);s.math('v',79,75)
 s.rect(39,104,33,20,'#eee');s.rect(80,104,33,20,'#eee');s.text('Q',55,119,11);s.text('P',97,119,11);s.ellipse(43,136,27,16);s.text('관찰자',43,133,10);s.text('B',43,146,10);s.rect(82,145,34,17);s.text('광원',99,157,10);s.arrow(2,211,177,211,.7);s.math('x',183,215);return s

@figure('T1c',25)
def t1c25():
 s=SVG(300,200);s.rect(42,13,70,34,'#888','none');s.rect(112,13,67,34,'#eee');s.rect(179,13,70,34,'#888','none');s.math('X',145,36,18)
 s.poly([(42,30),(23,30),(23,175),(42,175)]);s.poly([(249,30),(279,30),(279,92)]);s.resistor(279,92,279,128);s.poly([(279,128),(279,175),(249,175)]);s.line(145,47,145,175);s.line(103,175,174,175);s.rect(42,162,61,27,'white');s.rect(174,162,75,27,'white');s.math('V_{BE}',73,181);s.math('V_{CB}',210,181)
 for label,x,y in [('E',32,24),('B',134,61),('C',263,24),('I_E',10,103),('I_B',135,103),('I_C',291,91)]:s.math(label,x,y,13)
 return s

@figure('T1c',26)
def t1c26():
 s=SVG(260,200);s.poly([(50,104),(14,104),(14,182),(107,182)]);s.line(107,172,107,192,1.2);s.line(113,176,113,188,2.4);s.poly([(113,182),(241,182),(241,104),(169,104)])
 s.poly([(31,137),(67,62),(192,62),(142,137)],fill='#ddd',close=True);s.poly([(31,137),(142,137),(142,153),(31,153)],fill='#ccc',close=True);s.poly([(142,137),(192,62),(192,78),(142,153)],fill='#c8c8c8',close=True)
 s.arrow(91,91,91,33,6,'#888',9);s.text('자기장',78,21,11);s.math('B',108,21);s.arrow(205,92,232,92,.7);s.arrow(205,92,205,64,.7);s.arrow(205,92,220,68,.7);s.math('x',239,97);s.math('y',225,67);s.math('z',205,57);return s

def person(s,x,y,name,pose='both'):
 s.ellipse(x,y,9,7,'white');s.math(name,x,y+4,11);s.rect(x-4,y+7,8,18,'white');s.poly([(x-4,y+23),(x-16,y+44),(x-9,y+47),(x+1,y+28),(x+10,y+47),(x+17,y+44),(x+5,y+23)],fill='white',close=True)
 if pose=='left':s.rect(x-22,y+8,19,5,'white')
 elif pose=='right':s.rect(x+4,y+8,20,5,'white')
 else:s.rect(x-22,y+8,44,5,'white')

@figure('T2c',1)
def t2c1():
 s=SVG(330,102)
 for ox in[0,111,222]:
  s.rect(ox+4,81,103,9,'#ccc');
  for xx in range(ox+4,ox+108,5):s.line(xx,90,min(xx+5,ox+107),81,.35,color='#888')
 for lab,x in[('(1)',9),('(2)',120),('(3)',231)]:s.text(lab,x,15,10)
 s.rect(24,25,14,56,'#aaa');person(s,60,38,'A','left');s.arrow(54,62,39,62,1,head=5);s.math('F',48,76,11)
 person(s,137,38,"B'",'right');person(s,173,38,'B','left');s.arrow(169,62,151,62,1,head=5);s.math('F',161,76,11)
 person(s,250,38,"C'",'right');person(s,297,38,'C','left');s.arrow(265,62,275,62,1,head=4);s.arrow(286,62,276,62,1,head=4);return s

@figure('T2c',2)
def t2c2():
 s=SVG(200,205);s.ellipse(100,100,84,84,dash='3 3');s.ellipse(100,100,49,49,dash='3 3');s.ellipse(117.5,100,66.5,58)
 s.circle(100,100,2.4,INK);s.text('태양',100,92,11);s.circle(51,100,7);s.text('지구',42,120,11);s.circle(184,100,7);s.text('화성',191,85,11);s.arrow(40,112,40,89,.7,head=4);s.arrow(195,91,195,112,.7,head=4)
 s.poly([(100,43),(114,48),(103,55)],fill='#aaa',close=True);s.text('탐사선',110,35,11);return s

@figure('T2c',3)
def t2c3():
 s=SVG(250,215);s.ellipse(128,128,114,43,'white',width=1.4);s.path('M14,128 L14,134 A114,43 0 0 0 242,134 L242,128',1.1);s.line(128,177,128,210)
 s.poly([(45,111),(45,81),(84,111)],fill='white',close=True);s.poly([(45,81),(64,54),(105,82),(84,111)],fill='white',close=True)
 s.poly([(54,77),(64,63),(83,76),(73,90)],fill='#ddd',close=True);s.poly([(57,76),(64,67),(78,77),(71,85)],fill='white',close=True)
 s.math('3',40,104,11);s.math('4',65,124,11);s.math('5',61,96,11)
 s.line(68.5,76.5,68.5,28,.7,dash='2 2');s.line(128,128,128,28,.7,dash='2 2');s.arrow(68.5,33,128,33,.7,both=True,head=4);s.math(r'1\,\mathrm{m}',98.25,25,12);s.arc(128,128,84,34,100,47,arrow=True);s.math(r'\omega',184,155);return s

@figure('T2c',4)
def t2c4():
 s=SVG(130,200);s.circle(28,26,13);s.math('m',28,31,17);s.arrow(51,26,81,26,2.2,head=7);s.math('v',66,15,15);s.rect(89,27,29,163,'white',width=1.4);return s

@figure('T2c',5)
def t2c5():
 s=SVG(320,155)
 for cx in[85,261]:s.rect(cx-25,9,50,16,'#bbb');s.arrow(cx-55,35,cx-55,58);s.math('g',cx-64,43)
 s.line(85,25,85,79);s.circle(85,79,6,'#bbb');s.math('m',99,86);s.math('L',94,52)
 s.circle(21,119,6,'#bbb');s.math('M',15,142);s.path('M21,119 Q25,74 85,79',.8,dash='2 2');s.arrow(22,114,33,97);s.math('v',18,102);s.line(19,113,57,113,.7);s.arc(21,119,18,18,-64,-8,.7);s.math(r'\theta_1',43,106,11)
 s.arrow(85,79,85,119,.6,both=True,head=3);s.math('h',77,104);s.arrow(22,125,85,125,.6,both=True,head=3);s.math('D',54,141)
 s.arrow(130,78,173,78,12,'#aaa',13);s.line(261,25,261,79,.7,dash='2 2');s.line(261,25,288,69);s.circle(288,69,6,'#bbb');s.circle(281,74,6,'#bbb');s.path('M198,119 Q203,76 261,79',.8,dash='2 2');s.circle(198,119,6,'white',width=.7);s.arc(261,25,25,25,59,90,.7);s.math(r'\theta_2',273,62,11);return s

@figure('T2c',6)
def t2c6():
 s=SVG(290,155);s.line(9,134,282,134,2.2);s.line(58,134,247,27,1.1);s.poly([(163,135),(245,25),(250,30),(167,138)],fill='#ddd',close=True);s.circle(164,134,3.5,'#aaa')
 s.line(247,27,247,95);s.circle(247,107,11);s.math('M',247,111,15);s.math('T',145,73);s.math('S',228,82);s.text('(질량 m)',212,115,10);s.math('A',162,153);s.math('B',56,152)
 s.arc(58,134,33,33,-29,0);s.math(r'\theta_1',103,130);s.arc(164,134,27,27,-53,0);s.math(r'\theta_2',200,130);return s

@figure('T2c',10)
def t2c10():
 s=SVG(250,185);s.rect(10,10,105,48,'#ccc');s.rect(135,10,105,48,'white');s.text('n형 반도체',63,39,11);s.text('p형 반도체',188,39,11);s.arrow(125,69,125,94,7,INK,9)
 s.rect(20,104,105,47,'#ccc');s.rect(125,104,105,47,'white');s.text('n형 반도체',72,133,11);s.text('p형 반도체',178,133,11);s.arrow(123,174,123,152,.6,head=3);s.arrow(134,174,134,152,.6,head=3);s.math('A',122,184,11);s.math('B',135,184,11);return s

@figure('T2c',11)
def t2c11():
 s=SVG(300,95);s.text('공기',20,28,11);s.circle(69,47,35,'#aaa','none');s.arrow(125,47,158,47,.7,head=4);s.rect(179,47,113,42,'#dce4f5','none');s.poly([(179,27),(179,89),(292,89),(292,27)],.7,color='#999');s.text('공기',195,28,11);s.text('물',196,73,11);s.circle(242,47,35,'#aaa','none');return s

@figure('T2c',12)
def t2c12():
 s=SVG(250,215);s.rect(69,8,135,14,'#ddd')
 for x in range(70,203,6):
  end=min(x+7,204);s.line(x,20,end,20-(end-x)*10/7,.35,color='#999')
 s.rect(58,29,9,148,'#aaa','none');s.rect(211,29,9,148,'#aaa','none')
 for y in[38,77,116,155]:s.arrow(75,y,207,y,.6,color='#888',head=4)
 s.math('E_0',89,91);s.line(145,22,145,60,.7,color='#aaa');s.line(145,22,166,99,.8);s.circle(166,99,7,'#888');s.arc(145,22,22,22,75,90,.7);s.math(r'30^\circ',169,53,10)
 s.arrow(26,77,26,51,.6,head=3);s.arrow(26,77,44,77,.6,head=3);s.math('y',23,48);s.math('x',48,81)
 s.poly([(58,111),(11,111),(11,202),(124,202)]);s.line(124,193,124,211,1.2);s.line(130,196.6,130,207.4,2.4);s.poly([(130,202),(242,202),(242,111),(220,111)]);s.math('V',142,213,11)
 s.line(67,178,67,194,.6,color='#aaa');s.line(211,178,211,194,.6,color='#aaa');s.arrow(67,188,211,188,.6,color='#999',both=True,head=3);s.math('d',139,185,11);return s

@figure('T2c',13)
def t2c13():
 s=SVG(310,182)
 for ox,middle,title in[(0,True,'가'),(158,False,'나')]:
  a=(ox+40,66);b=(ox+80,24);c=(ox+80,109);d=(ox+120,66)
  for p,q in[(a,b),(b,d),(a,c),(c,d)]:s.resistor(*p,*q,n=4,amp=3)
  if middle:s.resistor(*b,*c,n=6,amp=3);s.math(r'4\,\Omega',ox+100,73,11)
  for lab,x,y in [('a',a[0]-6,a[1]-5),('b',b[0],b[1]-9),('c',c[0],c[1]+15),('d',d[0]+5,d[1]-5)]:s.circle(*{'a':a,'b':b,'c':c,'d':d}[lab],1.8,INK);s.math(lab,x,y,11)
  for lab,x,y in[(r'2\,\Omega',ox+46,32),(r'2\,\Omega',ox+112,32),(r'2\,\Omega',ox+43,100),(r'2\,\Omega',ox+113,101)]:s.math(lab,x,y,10)
  s.poly([a,(ox+9,66),(ox+9,139),(ox+76,139)]);s.line(ox+76,129,ox+76,149,1);s.line(ox+82,133,ox+82,145,2.3);s.poly([(ox+82,139),(ox+149,139),(ox+149,66),d]);s.math(r'4\,\mathrm{V}',ox+81,158,11);s.text('('+title+')',ox+80,172,10)
 return s

@figure('T2c',14)
def t2c14():
 s=SVG(320,145)
 for ox,title,slab in[(0,'가',False),(164,'나',True)]:
  s.poly([(ox+108,29),(ox+108,17),(ox+61,17)]);s.circle(ox+58,17,1.5,'white',width=.7);s.circle(ox+42,17,1.5,'white',width=.7);s.poly([(ox+41,17),(ox+12,17),(ox+12,63)]);s.circle(ox+12,71,8,'white',width=.7);s.math('V',ox+12,75,11);s.poly([(ox+12,79),(ox+12,119),(ox+108,119),(ox+108,106)])
  if slab:s.line(ox+58,17,ox+43,9,.8,color='#777')
  else:s.line(ox+42,17,ox+58,17,.8,color='#777')
  s.math('S',ox+49,31,10);s.rect(ox+79,27,70,10,'#bcbcbc','none');s.rect(ox+79,97,70,10,'#bcbcbc','none');s.arrow(ox+69,38,ox+69,97,.5,both=True,head=3);s.math(r'6\,\mathrm{cm}',ox+54,71,9)
  if slab:s.rect(ox+79,62,70,14,'#777','none');s.arrow(ox+154,62,ox+154,76,.5,both=True,head=2.5);s.math(r'2\,\mathrm{cm}',ox+149,57,9,anchor='end')
  s.text('('+title+')',ox+82,140,10)
 return s

@figure('T2c',15)
def t2c15():
 s=SVG(250,195);s.poly([(22,74),(139,153),(236,91),(119,12)],.7,color='#888',close=True);s.poly([(76,107),(173,44),(177,51),(80,114)],fill='#aaa',close=True)
 s.arrow(46,90,141,28,.6,color='#888',both=True,head=3);s.math('L',83,49);s.arrow(171,128,171,71,.7,head=4);s.math('B_0',185,107)
 s.arrow(139,153,178,130,.7,head=4);s.arrow(139,153,113,164,.7,head=4);s.arrow(139,153,139,135,.7,head=4);s.math('x',181,136);s.math('y',107,169);s.math('z',138,130)
 s.line(139,153,15,135,.6,color='#999');s.arc(139,153,36,20,194,219,.7);s.math(r'\theta',100,142);return s

@figure('T2c',16)
def t2c16():
 s=SVG(334,110)
 for ox in[0,172]:
  s.path(f'M{ox+8},32 H{ox+62} V53 H{ox+82} V20 H{ox+150} V103 H{ox+82} V65 H{ox+62} V86 H{ox+8} Z',.8)
  s.math('V',ox+32,27,11);s.math('2V',ox+115,15,11)
 s.line(70,53,70,65,.8)
 before_src=[(31,84),(47,91),(63,80),(80,79),(101,83),(116,87),(61,94),(29,109),(45,117),(59,103),(78,103),(94,100),(66,117),(87,125),(116,115),(24,137),(37,142),(54,142),(72,129),(87,138),(104,130),(18,155),(42,164),(61,157),(85,151),(103,144),(127,145),(20,176),(42,183),(66,179),(85,180),(95,165),(112,158),(111,183),(128,189)]
 before=[(8+(x-8)*54/127,32+(y-69)*54/128)for x,y in before_src]
 # Diagram particles are placed as explicit circle primitives, not sampled contours.
 after_left_src=[(545,89),(597,91),(620,108),(542,113),(576,116),(556,138),(602,133),(628,134),(561,162),(616,169),(540,181),(592,185)]
 after_right_src=[(737,74),(769,59),(806,65),(843,65),(893,59),(765,99),(816,95),(850,106),(887,114),(748,130),(783,120),(801,149),(829,133),(853,143),(744,176),(773,165),(790,195),(826,171),(855,177),(889,169),(740,210),(823,205),(888,210)]
 after_left=[(180+(x-521)*54/127,32+(y-69)*54/128)for x,y in after_left_src]
 after_right=[(254+(x-717)*68/192,20+(y-37)*83/192)for x,y in after_right_src]
 for x,y in before+after_left+after_right:s.circle(x,y,1.9,INK,'none')
 s.arrow(156,59,169,59,3.8,'#426bab',6);return s

@figure('T2c',17)
def t2c17():
 s=SVG(270,185);s.arrow(39,162,254,162,.7);s.arrow(39,162,39,12,.7);s.math(r'P\,(\mathrm{Pa})',22,16,11);s.math(r'V\,(\mathrm{m^3})',240,181,11)
 a=(105,48);b=(196,119);c=(105,119)
 for y,lab in[(48,'2P_0'),(119,'P_0')]:s.line(39,y,105,y,.5,color='#999',dash='1 2');s.math(lab,25,y+4,11)
 for x,lab in[(105,'V_0'),(196,'2V_0')]:s.line(x,119,x,163,.5,color='#999',dash='1 2');s.math(lab,x,180,11)
 s.arrow(*c,*a);s.arrow(*b,*c);s.path('M105,48 C117,87 146,100 196,119');s.arrow(134,93,144,99,1,head=5)
 for lab,x,y in[('A',105,40),('B',207,123),('C',96,132)]:s.math(lab,x,y,11)
 return s

@figure('T2c',18)
def t2c18():
 s=SVG(280,160);s.rect(9,25,262,121,'white');s.rect(16,33,247,105,'white');s.rect(139,33,5,105,'#aaa','none');s.line(110,33,110,138,.8,dash='2 2');s.line(115,33,115,138,.8,dash='2 2');s.arrow(136,86,117,86,.6,color='#888',dash='1 2',head=3)
 s.arrow(16,15,263,15,.6,both=True,head=4);s.math(r'1\,\mathrm{m}',140,10,12);s.line(16,16,16,25,.5);s.line(263,16,263,25,.5);s.arrow(16,153,141,153,.6,both=True,head=4);s.line(16,147,16,159,.5);s.line(141,147,141,159,.5);return s

@figure('T2c',19)
def t2c19():
 s=SVG(320,155);s.path('M8,15 H236 A58,58 0 0 1 294,73 V146 H265 V73 A29,29 0 0 0 236,44 H8 Z',.7,color='#555',fill='#62b0e0')
 s.line(236,15,236,73,.6,color='#666',dash='2 2');s.line(236,73,294,73,.6,color='#666',dash='2 2');s.line(236,73,269,24,.6,color='#666',dash='2 2');s.line(236,73,284,42,.6,color='#666',dash='2 2')
 for y in[24,34]:s.arrow(8,y,130,y,.65,color='#c9807d',head=4);s.line(130,y,262+(y-24)*1.8,y,.65,color='#c9807d')
 s.arrow(263,24,319,34,.65,color='#c9807d',head=4);s.arrow(280,34,319,42,.65,color='#c9807d',head=4);s.line(280,34,265,114,.65,color='#c9807d');s.arrow(265,114,265,120,.65,color='#c9807d',head=4);s.arrow(280,34,293,113,.65,color='#c9807d',head=4);return s

@figure('T2c',20)
def t2c20():
 s=SVG(190,230);x1,x2=68,176
 s.rect(x1,10,3,199,'#666');s.rect(x2,10,3,199,'#666')
 for y in[58,108,158]:s.line(13,y,x2,y,.5,color='#888',dash='1 2')
 pts1=[];pts2=[]
 for i in range(601):
  y=39+i*150/600;env=.96+.04*math.exp(-((y-109)/78)**2);left=2+54*env*(.5+.5*math.cos((y-58)*2*math.pi/25));pts1.append((x1-left,y))
  y=12+i*196/600;right=2+54*(.5+.5*math.cos((y-58)*2*math.pi/50));pts2.append((x2-right,y))
 s.poly(pts1,.9);s.poly(pts2,.9);s.text('(가)',36,226,12);s.text('(나)',145,226,12);return s

@figure('T2d',4)
def t2d4():
 s=SVG(300,100,'HyhwpEQ')
 for x,title in[(53,'가'),(151,'나'),(249,'다')]:
  s.line(x-43,10,x+43,10,1.4);s.line(x,10,x,44,.6,color='#888')
  if x==53:s.circle(x,52,9,'#bbb','none')
  elif x==151:s.line(x-9,44,x+9,44,1.2,color='#aaa')
  else:s.poly([(x,43),(x+12,55),(x,67),(x-12,55)],fill='#bbb',color='#bbb',close=True)
  s.math(r'm,\ \omega',x,78,12);s.text('('+title+')',x,96,11)
 return s

@figure('T2d',7)
def t2d7():
 s=SVG(250,145,'HyhwpEQ');s.arrow(11,108,239,108,.7,color='#777',head=4);s.arrow(105,108,105,10,.7,color='#777',head=4);s.math('x',233,123);s.math('z',98,17)
 for y in range(113,141,4):
  for x in range(13,223,5):s.circle(x+(2 if y%8 else 0),y,.45,'#888','none')
 s.text('초전도체',190,129,13);s.poly([(99,63),(109,53),(112,56),(102,66)],fill='#777',close=True);s.arrow(100,66,116,49,.7,head=3);s.arc(105,59,16,17,-90,-45,.6);s.math(r'\theta',112,45,12);return s

@figure('T2d',10)
def t2d10():
 s=SVG(240,160,'HyhwpEQ');front=[(39,61),(104,78),(104,139),(39,123)];s.poly(front,1,close=True);s.poly([(48,73),(95,85),(95,129),(48,117)],.7,close=True)
 for a,b in[((39,61),(169,8)),((104,78),(232,25)),((104,139),(232,86)),((48,117),(95,97))]:s.line(*a,*b,.8,color='#777')
 s.line(48,73,15,64.5,.5,color='#aaa');s.line(48,117,15,108.5,.5,color='#aaa');s.arrow(22,66.3,22,110.3,.5,color='#888',both=True,head=3);s.math('L',12,92,12);s.line(48,117,48,150,.5,color='#aaa');s.line(95,129,95,158,.5,color='#aaa');s.arrow(48,146,95,158,.5,color='#888',both=True,head=3);s.math('L',71,158,12);return s

@figure('T2d',13)
def t2d13():
 s=SVG(190,135,'HyhwpEQ');s.arrow(15,84,178,84,.8,color='#777',head=4);s.arrow(84,84,84,12,.8,color='#777',head=4);s.line(15,84,150,84,1.3);s.arrow(84,84,84,124,1.1,head=5);s.math('V(x)',65,20,15);s.math('x',169,98,14);s.math('0',76,99,14);s.math(r'-U\delta(x)',122,124,14);return s

def build(selected=None):
 OUT.mkdir(parents=True,exist_ok=True);index=json.loads((ROOT/'tools/kphe_figures/index.json').read_text(encoding='utf8'));figures={}
 wanted={'KPhE_2023_T1c_KO.pdf','KPhE_2023_T2c_KO.pdf','KPhE_2023_T2d_KO.pdf'}
 for key,spec in index['figures'].items():
  if spec['source']not in wanted:continue
  use=next(u for u in spec['uses']if u['where']=='explanation');part,num=use['part'],use['number']
  if selected and (part,num)not in selected:continue
  scene=DRAW[(part,num)]();svg=scene.svg();name=f'2023-{part}-q{num}-{key}';sp=OUT/(name+'.svg');pp=OUT/(name+'.pdf');sp.write_text(svg,encoding='utf8')
  pdf=fitz.open(stream=svg.encode(),filetype='svg').convert_to_pdf();pp.write_bytes(pdf)
  check=fitz.open(pp);assert not check[0].get_images(full=True),f'Raster in {name}'
  figures[key]=dict(file=sp.relative_to(ROOT).as_posix(),pdf=pp.relative_to(ROOT).as_posix(),source=spec['source'],page=spec['page'],rect=spec['rect'],width_pt=scene.w*scene.scale,height_pt=scene.h*scene.scale,recommended_width_pt=scene.w*scene.scale,font_profile=scene.face,sha256=hashlib.sha256(sp.read_bytes()).hexdigest(),pdf_sha256=hashlib.sha256(pp.read_bytes()).hexdigest(),status='draft',method='manually authored native geometry and font glyph outlines; no raster embedding or contour tracing',uses=spec['uses'])
 manifest=OUT/'manifest.json'
 if selected and manifest.exists():
  old=json.loads(manifest.read_text(encoding='utf8'))['figures'];old.update(figures);figures=old
 manifest.write_text(json.dumps(dict(version=1,figures=figures),ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('Authored',len(figures),'native geometry figures')
if __name__=='__main__':build()

