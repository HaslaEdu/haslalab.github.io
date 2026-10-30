"""Manually constructed native geometry for the supplied 2023 intermediate figures.

All shapes are authored from their physical diagrams, never from raster contours.
Source scans are used only by the separate QA/reference step.  The output PDFs
contain PDF paths and embedded native text; there are no image XObjects.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from kphe_fonts import font_path
import kphe_template as typography

OUT = ROOT / 'tools/kphe_redraw/ab'
QA = ROOT / 'tmp/kphe_redraw_ab_qa'
BLACK = (0, 0, 0)
GRAY = (.72, .72, .72)
LIGHT = (.87, .87, .87)
BLUE = (.27, .59, .82)
RED = (.91, .12, .10)
ORANGE = (.85, .42, .13)


class Figure:
    def __init__(self, width, height, math_base_size=16, native_width=232, panel_scale=1):
        self.doc = fitz.open()
        self.w, self.h = float(width), float(height)
        self.page = self.doc.new_page(width=width, height=height)
        self.math_base_size = math_base_size
        self.native_width = native_width
        self.final_scale = native_width/width*panel_scale
        self.font = fitz.Font(fontfile=str(font_path('Gulim')))
        self.page.insert_font(fontname='gulim', fontfile=str(font_path('Gulim')))

    def line(self, a, b, width=1, color=BLACK, dash=None):
        self.page.draw_line(a, b, width=width, color=color, dashes=dash)

    def poly(self, points, width=1, color=BLACK, fill=None, close=False, dash=None):
        s = self.page.new_shape()
        s.draw_polyline(points)
        s.finish(width=width, color=color, fill=fill, closePath=close, dashes=dash)
        s.commit()

    def bezier(self, a, b, c, d, width=1, color=BLACK, dash=None):
        s = self.page.new_shape()
        s.draw_bezier(a, b, c, d)
        s.finish(width=width, color=color, closePath=False, dashes=dash)
        s.commit()

    def rect(self, r, fill=None, width=1, color=BLACK):
        self.page.draw_rect(r, fill=fill, color=color, width=width)

    def ellipse(self, r, fill=None, width=1, color=BLACK):
        self.page.draw_oval(r, fill=fill, color=color, width=width)

    def circle(self, x, y, radius, fill=None, width=1, color=BLACK):
        self.page.draw_circle((x, y), radius, fill=fill, color=color, width=width)

    def arrow(self, a, b, width=1, color=BLACK, head=5, both=False, dash=None):
        self.line(a, b, width, color, dash)
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        if not length:
            return
        ux, uy = dx/length, dy/length
        def tip(p, sign):
            self.poly([p, (p[0]-sign*head*ux+head*.38*uy, p[1]-sign*head*uy-head*.38*ux),
                       (p[0]-sign*head*ux-head*.38*uy, p[1]-sign*head*uy+head*.38*ux)],
                      width=.4, color=color, fill=color, close=True)
        tip(b, 1)
        if both:
            tip(a, -1)

    def arc(self, x, y, rx, ry, start, end, width=1, color=BLACK, dash=None, head=False):
        pts = [(x+rx*math.cos(t), y+ry*math.sin(t)) for t in
               [math.radians(start+(end-start)*i/80) for i in range(81)]]
        self.poly(pts, width, color, dash=dash)
        if head:
            self.arrow(pts[-3], pts[-1], width, color, 4)

    def text(self, value, x, y, size=12, align='left', color=BLACK, rotate=0):
        size=max(size,8.5/self.final_scale)
        length = self.font.text_length(value, fontsize=size)
        if rotate in [90,270]:
            sign=1 if rotate==90 else -1
            if align=='center':y+=sign*length/2
            if align=='right':y+=sign*length
        else:
            if align == 'center': x -= length/2
            if align == 'right': x -= length
            x=max(1,min(x,self.w-length-1))
            y=max(size*self.font.ascender+1,min(y,self.h+size*self.font.descender-1))
        self.page.insert_text((x, y), value, fontname='gulim', fontsize=size, color=color, rotate=rotate)

    def m(self, value, x, y, size=None, align='left'):
        size = self.math_base_size if size is None else size
        size=max(size,8.5/(.83*self.final_scale))
        doc, w, h, depth = typography.math_pdf_transparent(value, size)
        if align == 'center': x -= w/2
        if align == 'right': x -= w
        x=max(1,min(x,self.w-w-1))
        y=max(h-depth+1,min(y,self.h-depth-1))
        self.page.show_pdf_page(fitz.Rect(x, y-(h-depth), x+w, y+depth), doc, 0)

    def spring(self, a, b, turns=12, radius=4, width=.8, color=BLACK):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        ux, uy = dx/length, dy/length
        pts=[]
        for i in range(turns*24+1):
            t=i/(turns*24)
            theta=2*math.pi*turns*t
            off=radius*math.sin(theta)
            along=length*t+radius*.32*(math.cos(theta)-1)
            pts.append((a[0]+ux*along-uy*off, a[1]+uy*along+ux*off))
        self.poly(pts, width, color)

    def resistor(self, a, b, amplitude=3.5, teeth=4, width=1):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length=math.hypot(dx,dy); ux,uy=dx/length,dy/length
        pts=[a]
        for i in range(1,2*teeth+1):
            t=i/(2*teeth+1);off=amplitude*(1 if i%2 else -1)
            pts.append((a[0]+dx*t-uy*off,a[1]+dy*t+ux*off))
        pts.append(b); self.poly(pts,width)

    def battery(self, x, y, vertical=False, label=None):
        if vertical:
            self.line((x-8,y-3),(x+8,y-3),1.1)
            self.line((x-4,y+3),(x+4,y+3),1.1)
        else:
            self.line((x-3,y-8),(x-3,y+8),1.1)
            self.line((x+3,y-4),(x+3,y+4),1.1)
        if label: self.m(label,x,y+21,align='center')

    def meter(self, x, y, label, radius=11, underline=True):
        self.circle(x,y,radius,fill=(1,1,1))
        self.text(label,x,y+4,size=12,align='center')
        if underline:self.line((x-5,y+6),(x+5,y+6),.7)

    def save(self, path):
        # The final asset is a native 232 pt object, independent of the 300 unit
        # authoring coordinate system.  This preserves readable label sizes in
        # a 244.5 pt A4 examination column.
        final = fitz.open()
        ratio = self.native_width / self.w
        page = final.new_page(width=self.native_width, height=self.h*ratio)
        page.show_pdf_page(page.rect,self.doc,0)
        self.doc, self.page, self.w, self.h = final,page,self.native_width,self.h*ratio
        self.doc.set_metadata({'title':path.stem,'author':'HaslaLab native vector redrawing',
                               'subject':'Manually authored geometry and native font text; no raster tracing'})
        self.doc.subset_fonts()
        assert not self.page.get_images(full=True), path
        self.doc.save(path,garbage=4,deflate=True)


def axes(c,x0,y0,x1,y1,xlabel=None,ylabel=None,size=11):
    c.arrow((x0,y0),(x1,y0),head=4)
    c.arrow((x0,y0),(x0,y1),head=4)
    if xlabel:
        if x1+3+c.font.text_length(xlabel,fontsize=size)>c.w-2:
            c.text(xlabel,min(c.w-3,x1+3),y0+18,size,align='right')
        else:c.text(xlabel,x1+3,y0+6,size)
    if ylabel:c.text(ylabel,x0-3,y1-6,size,align='center')


def bar_magnet(c,x,y,w=60,h=22,ns=('N','S')):
    for i,label in enumerate(ns):
        color=RED if label=='N' else (.16,.43,.72)
        c.rect((x+i*w/2,y,x+(i+1)*w/2,y+h),fill=color,width=.5,color=color)
        c.text(label,x+(i+.5)*w/2,y+h*.7,10,'center',color=(1,1,1))
    c.poly([(x,y),(x+6,y-5),(x+w+6,y-5),(x+w,y)],fill=(.18,.44,.69),color=(.18,.44,.69),close=True)
    c.poly([(x+w,y),(x+w+6,y-5),(x+w+6,y+h-5),(x+w,y+h)],fill=(.1,.3,.55),color=(.1,.3,.55),close=True)


def t1b1(c):
    axes(c,40,145,245,24,'시간','이동거리',13)
    c.text('0',32,162,12)
    for x,t in [(100,'t'),(160,'2t'),(220,'3t')]:
        c.line((x,145),(x,34),.7,(.55,.55,.55),'[2 2] 0');c.m(t,x,166,align='center')
    c.poly([(40,145),(100,75),(220,75)],1.7)
    c.line((40,145),(220,40),1.7)
    c.m('A',79,80);c.line((82,83),(77,102),.7)
    c.m('B',181,38);c.line((182,43),(178,63),.7)


def t1b2(c):
    y=c.h-32;cx=168;R=min(95,(c.h-45)/2)
    wall=cx-R;mass=wall+.49*R
    c.line((20,y),(cx,y),1.5);c.arc(cx,y-R,R,R,-90,90,1.7)
    c.line((cx,y-2*R-8),(cx,y+6),.8,(.5,.5,.5),'[2 2] 0')
    c.circle(cx,y-R,2.6,fill=BLACK)
    c.arrow((cx,y-R),(cx+R*.72,y-R-R*.69),head=5);c.m('R',cx+20,y-R-24)
    c.line((wall,y-1),(wall,y-30),3);c.spring((wall+2,y-11),(mass-11,y-11),10,4)
    c.circle(mass,y-11,11,fill=(.22,.22,.22))
    c.arrow((mass+13,y-11),(cx+8,y-11),head=4);c.m('v_0',mass+24,y-18)
    c.m('k',wall+15,y-35)
    c.arrow((wall,y+15),(cx,y+15),head=4,both=True);c.m('R',(wall+cx)/2,y+31,align='center')


def t1b4(c):
    cy=c.h*.55
    c.ellipse((11,cy-42,288,cy+42),fill=(.97,.97,.97),width=.9,color=(.48,.48,.48))
    c.arc(150,cy+8,139,42,0,180,.8,(.45,.45,.45))
    c.line((150,cy+42),(150,c.h-8),2.2,color=(.25,.25,.25))
    c.line((150,cy),(150,18),2.2,color=(.25,.25,.25))
    c.arc(150,27,12,16,180,0,1.3,head=True);c.m(r'\omega_0',157,12)
    c.arrow((150,cy),(65,cy-27),head=5);c.m('2R',98,cy-5)
    c.spring((151,cy-1),(197,cy-15),12,4,1)
    c.circle(214,cy-21,12,fill=BLUE,color=BLUE);c.m('m',214,cy-16,align='center')


def t1b6(c):
    cx=110;cy=18;radius=c.h*.72
    c.rect((20,10,256,19),fill=BLACK)
    c.arc(cx,cy,radius,radius,26,91,.8,(.4,.4,.4),'[2 2] 0')
    for angle,label in [(90,'(ㄱ)'),(69,'(ㄴ)'),(48,'(ㄷ)')]:
        x=cx+radius*math.cos(math.radians(angle));y=cy+radius*math.sin(math.radians(angle))
        c.line((cx,cy),(x,y),1.2)
        c.circle(x,y,20,fill=BLUE,width=.3,color=BLUE);c.text(label,x,y+43,16,'center')


def t1b7(c):
    axes(c,36,c.h-28,278,16,'시간','힘',12);c.text('0',25,c.h-10,11)
    y=c.h-28
    s=c.page.new_shape();s.draw_bezier((36,y),(80,y-8),(144,y-89),(240,y));s.draw_line((240,y),(36,y));s.finish(color=(.48,.67,.8),fill=(.72,.83,.91),width=1,closePath=True);s.commit()
    s=c.page.new_shape();s.draw_bezier((36,y),(54,y-8),(68,28),(76,50));s.draw_bezier((76,50),(81,66),(87,y-12),(107,y));s.draw_line((107,y),(36,y));s.finish(color=(.9,.61,.4),fill=(1,.89,.79),width=1,closePath=True);s.commit()
    c.text('콘크리트 바닥',107,43,13);c.line((107,47),(83,60),.8)
    c.text('스폰지',208,y-48,13);c.line((226,y-42),(174,y-25),.8)


def t1b8(c):
    cy=c.h*.47
    c.line((23,cy),(280,cy),.7,(.5,.5,.5),'[3 2] 0')
    c.circle(27,cy,12,fill=(.65,.65,.65),color=(.65,.65,.65))
    c.circle(265,cy,23,fill=(.4,.4,.4),color=(.4,.4,.4))
    c.bezier((27,cy),(60,cy-25),(104,cy-25),(145,cy),.8,(.45,.45,.45),'[2 2] 0')
    c.bezier((145,cy),(183,cy-25),(218,cy-21),(265,cy),.8,(.45,.45,.45),'[2 2] 0')
    c.arrow((27,cy-15),(27,cy-44),.9,head=4);c.m('v_1',9,cy-34)
    c.arrow((265,cy+29),(265,cy+57),.9,head=4);c.m('v_2',275,cy+47)
    c.m('a',81,cy-17);c.m('b',201,cy-15)


def t1b9(c):
    base=c.h-12;top=18;hh=base-top
    for x in [13,205]:
        c.line((x,top),(x+85,top),.6,(.55,.55,.55),'[2 2] 0')
        c.line((x,base),(x+88,base),.6,(.55,.55,.55),'[2 2] 0')
    s=c.page.new_shape();s.draw_bezier((20,top),(36,top+hh*.38),(69,top+hh*.50),(100,top+hh*.50));s.draw_polyline([(100,top+hh*.50),(100,base),(20,base),(20,top)]);s.finish(color=(.55,.55,.55),fill=(.68,.68,.68),width=.6,closePath=True);s.commit()
    c.poly([(205,top),(270,top+hh*.50),(270,base),(205,base)],fill=(.68,.68,.68),width=.6,close=True,color=(.55,.55,.55))
    for x,label in [(20,'A'),(205,'B')]:c.circle(x,top,2.4,fill=(1,.63,.45),color=(1,.63,.45));c.text(label,x,top-5,8,'center')
    c.arrow((9,top),(9,base),width=.6,head=2,both=True);c.m('h',4,(top+base)/2,10,align='right')
    c.arrow((20,base-12),(100,base-12),width=.6,head=2,both=True);c.m('d',60,base-15,10,align='center')
    c.arrow((205,base-12),(270,base-12),width=.6,head=2,both=True);c.m('d',238,base-15,10,align='center')
    for x in [105,276]:c.arrow((x,top+hh*.50),(x,base),.6,head=2,both=True);c.m(r'h/2',x+2,base-hh*.2,10)


def t1b11(c):
    y=58
    c.rect((12,y,248,c.h-8),fill=(.72,.72,.72))
    c.rect((64,y-45,111,y),fill=(.61,.72,.52),color=(.61,.72,.52));c.m('m_1',88,y-17,align='center')
    c.circle(260,y-7,16,fill=(.66,.66,.66),color=(.45,.45,.45));c.circle(260,y-7,6,fill=(.9,.9,.9),color=(.45,.45,.45))
    c.poly([(111,y-24),(261,y-24),(277,y-7),(277,c.h-50)],1)
    c.line((248,y),(264,y-9),4,(.6,.6,.6))
    c.rect((253,c.h-56,296,c.h-11),fill=(.61,.72,.52),color=(.61,.72,.52));c.m('m_2',274,c.h-28,align='center')


def t1b12(c):
    y=c.h-8
    c.line((4,y),(296,y),.7,(.5,.5,.5))
    c.poly([(16,y),(139,y-26),(139,y)],fill=(.82,.82,.82),color=(.82,.82,.82),close=True)
    c.circle(12,y-6,6,fill=BLUE,color=BLUE)
    c.arrow((13,y-6),(58,y-29),color=BLUE,head=4)
    c.bezier((16,y-7),(46,y-44),(80,y-40),(105,y-26),.7,(.6,.6,.6),'[2 2] 0')
    c.bezier((105,y-26),(136,y-69),(164,y-59),(195,y),.7,(.6,.6,.6),'[2 2] 0')
    c.arc(16,y,25,25,-27,0,.8);c.m(r'\alpha',43,y-14)
    c.arc(16,y,49,22,-16,0,.8);c.m(r'\theta',76,y-6)


def t1b13(c):
    y=c.h-15
    c.line((10,y),(293,y),2)
    c.line((38,y),(38,20),3)
    c.spring((40,y-14),(110,y-14),12,8,1.2)
    c.rect((110,y-43,189,y),fill=(.45,.45,.45),color=(.45,.45,.45))
    c.rect((132,y-78,169,y-43),fill=(.68,.68,.68),color=(.68,.68,.68))
    c.text('A',150,y-16,17,'center');c.text('B',151,y-54,17,'center')


def t1b14(c):
    cx=167;top=58;bot=c.h-10
    # Elliptical metal plate, glass vessel, stopper and two foil leaves.
    c.line((cx,top-8),(cx,top+58),2,(.4,.4,.4))
    c.ellipse((cx-27,top-16,cx+27,top-7),fill=(.82,.82,.82),color=(.45,.45,.45))
    c.ellipse((cx-19,top+7,cx+19,top+17),fill=(.88,.88,.88),color=(.5,.5,.5))
    c.ellipse((cx-17,top+15,cx+17,top+25),fill=BLACK)
    c.bezier((cx-15,top+22),(cx-10,top+54),(cx-40,top+48),(cx-45,top+82),1.2,(.4,.4,.4))
    c.bezier((cx-45,top+82),(cx-49,top+108),(cx-47,bot-11),(cx-26,bot-4),1.2,(.4,.4,.4))
    c.bezier((cx+15,top+22),(cx+10,top+54),(cx+40,top+48),(cx+45,top+82),1.2,(.4,.4,.4))
    c.bezier((cx+45,top+82),(cx+49,top+108),(cx+47,bot-11),(cx+26,bot-4),1.2,(.4,.4,.4))
    c.ellipse((cx-45,bot-15,cx+45,bot+2),width=1,color=(.45,.45,.45))
    # Two separate, diverging metal foils.  There is no horizontal base joining
    # their free ends; the source is an open V, not a filled triangular plate.
    c.line((cx,top+54),(cx,top+76),1)
    for sign in [-1,1]:
        c.poly([(cx,top+75),(cx+sign*19,bot-21),(cx+sign*17,bot-21),(cx+sign*1,top+75)],
               width=.5,fill=(.84,.84,.84),color=(.35,.35,.35),close=True)
    c.poly([(38,top+58),(96,top-5),(102,top+1),(44,top+65)],width=1,fill=(.7,.7,.7),close=True)
    for x,y in [(63,top-6),(81,top-21),(103,top-7),(86,top+11),(67,top+29)]:c.line((x,y),(x+9,y),1.7)
    c.text('금속판',191,24,15);c.line((195,28),(172,top-11),.7)
    c.text('유리',29,top+102,14);c.text('막대',29,top+121,14)
    c.text('금속박',220,top+116,15);c.arrow((217,top+108),(180,top+112),head=3)


def t1b15(c):
    y=c.h*.42
    bar_magnet(c,17,y,76,29);bar_magnet(c,165,y,76,29)
    c.arrow((133,10),(133,c.h-16),width=2.7,color=(.7,.18,.04),head=7)
    c.text('전류의 방향',143,c.h-8,8)
    c.arrow((269,y+18),(298,y+18),width=.6,head=3);c.arrow((269,y+18),(269,y-15),width=.6,head=3)
    c.m('x',297,y+29,10);c.m('y',266,y-20,10)


def t1b16(c):
    top=85;bottom=c.h-38
    c.poly([(18,top),(18,bottom),(282,bottom),(282,top)],1.2)
    c.line((18,top),(50,top),1.2)
    for a,b,end in [(50,83,128),(128,161,206),(206,239,282)]:
        c.resistor((a,top),(b,top));c.line((b,top),(end,top),1.2);c.m('R',(a+b)/2,top-17,align='center')
    # V1 spans R1+R2 and V2 spans R2+R3, exactly as in the source.
    c.poly([(35,top),(35,top+49),(183,top+49),(183,top)],1)
    c.meter(109,top+49,'V',13);c.text('전압계1',109,top+76,10,'center')
    c.poly([(106,top),(106,top-46),(262,top-46),(262,top)],1)
    c.meter(188,top-46,'V',14);c.text('전압계2',188,top-72,10,'center')
    c.battery(154,bottom,label='V');c.meter(229,bottom,'A',14);c.text('전류계',238,bottom+28,10,'center')


def t1b17(c):
    left=48;right=260;top=32;bottom=c.h-30
    c.poly([(left+6,top),(right,top),(right,bottom),(left,bottom),(left,top)],1.1)
    c.rect((141,top-6,178,top+6),fill=(1,1,1),width=0,color=(1,1,1));c.resistor((141,top),(178,top));c.text('10 Ω',159,top-12,11,'center')
    mid=(top+bottom)/2
    c.rect((left-6,mid-19,left+6,mid+19),fill=(1,1,1),width=0,color=(1,1,1));c.resistor((left,mid-19),(left,mid+19));c.text('10 Ω',left-8,mid+4,10,'right')
    c.rect((right-6,mid-19,right+6,mid+19),fill=(1,1,1),width=0,color=(1,1,1));c.resistor((right,mid-19),(right,mid+19));c.text('10 Ω',right+8,mid+4,10)
    c.line((left,top),(139,top+(bottom-top)*.43));c.resistor((139,top+(bottom-top)*.43),(168,top+(bottom-top)*.57));c.line((168,top+(bottom-top)*.57),(right,bottom));c.text('10 Ω',180,mid-6,10)
    c.battery(150,bottom);c.text('10 V',150,bottom-20,11,'center')
    for x,y,label in [(left-15,top,'A'),(right+7,top,'B'),(right+7,bottom+8,'C'),(left-15,bottom+8,'D')]:c.m(label,x,y)


def coil_scene(c):
    # Authoring coordinates are horizontal; PDF geometry is rotated as a group.
    theta=math.radians(28);cx=155;cy=c.h*.54
    def p(x,y):return(cx+x*math.cos(theta)-y*math.sin(theta),cy+x*math.sin(theta)+y*math.cos(theta))
    c.line(p(-146,0),p(144,0),1)
    for x,l in [(-48,'a'),(102,'b')]:
        xx,yy=p(x,0);c.circle(xx,yy,2,fill=BLACK);c.m(l,xx-4,yy+17)
    for i in range(12):
        x=-14+i*5
        pts=[p(x+5*math.cos(t),24*math.sin(t))for t in [2*math.pi*j/70 for j in range(71)]]
        c.poly(pts,width=.8,color=(.25,.25,.25))
    c.poly([p(-12,-23),p(-12,-45),p(2,-45)],.8)
    c.resistor(p(2,-45),p(31,-45),2.8,4,.9);c.line(p(31,-45),p(44,-45),.9);c.line(p(44,-45),p(44,-23),.9)
    tx,ty=p(19,-55);c.text('저항',tx,ty,9)
    # Source monochrome S/N block and approach arrow.
    points=[p(-130,-11),p(-87,-11),p(-87,6),p(-130,6)]
    c.poly(points,fill=(.86,.86,.86),close=True,width=.7)
    a=p(-109,-11);b=p(-109,6);c.line(a,b,.7)
    for x,l in [(-120,'S'),(-99,'N')]:xx,yy=p(x,1);c.text(l,xx,yy,10,'center')
    c.arrow(p(-84,-3),p(-59,-3),head=4)


def t1b18(c):coil_scene(c)


def t1b23(c):
    hot=c.h*.19;cy=c.h*.47;cold=c.h*.80
    c.rect((68,10,232,hot),fill=(1,.81,.66),width=0,color=(1,.81,.66));c.text('고열원',150,(10+hot)/2+5,17,'center')
    c.poly([(137,hot),(163,hot),(163,cy-47),(182,cy-47),(150,cy-23),(118,cy-47),(137,cy-47)],fill=(1,.77,0),color=(1,.77,0),close=True);c.text('Q₁',150,(hot+cy-24)/2+4,14,'center',color=(1,1,1))
    c.ellipse((99,cy-33,201,cy+33),fill=(.68,.82,.93),color=(.42,.61,.76));c.text('열기관',150,cy+6,16,'center')
    c.poly([(200,cy-11),(237,cy-11),(237,cy-19),(255,cy),(237,cy+19),(237,cy+11),(200,cy+11)],fill=(.18,.48,.75),color=(.18,.48,.75),close=True);c.text('60 kJ',239,cy+31,13,'center')
    c.poly([(137,cy+32),(163,cy+32),(163,cold-29),(180,cold-29),(150,cold),(120,cold-29),(137,cold-29)],fill=(.18,.48,.75),color=(.18,.48,.75),close=True);c.text('Q₂',150,(cy+32+cold)/2,14,'center',color=(1,1,1));c.text('300 kJ',202,cold-13,13)
    c.rect((68,cold,232,c.h-7),fill=(.72,.84,.95),width=0,color=(.72,.84,.95));c.text('저열원',150,(cold+c.h-7)/2+6,17,'center')


def t1b25(c):
    left=151;right=274;top=15;bottom=c.h-12
    c.poly([(left,top),(right,top),(right,bottom),(left,bottom),(left,top)],1.5,dash='[5 4] 0')
    for y in [50,105,160,215,270]:
        if y<bottom:c.arrow((10,y),(left,y),width=1.1,color=(.94,.16,.12),head=4)
    c.text('(가)',213,(top+bottom)/2+5,16,'center')


def t1b26(c):
    h=c.h
    def wave(y, transverse):
        pts=[]
        centers=(.10,.50,.90);sigma=.035;amplitude=3.5
        def density_integral(t):
            return t+amplitude*sigma*math.sqrt(math.pi)/2*sum(
                math.erf((t-cc)/sigma)-math.erf(-cc/sigma)for cc in centers)
        normalization=density_integral(1)
        for i in range(1800):
            t=i/1799
            if transverse:
                # Source starts at the midline rising toward its first crest.
                center=-14*math.sin(2*math.pi*2.5*t)
                slope=-14*2*math.pi*2.5*math.cos(2*math.pi*2.5*t)
                norm=math.hypot(270,slope);ux,uy=270/norm,slope/norm
                theta=2*math.pi*60*t
                x=20+270*t+ux*1.7*math.cos(theta)-uy*8*math.sin(theta)
                yy=y+center+uy*1.7*math.cos(theta)+ux*8*math.sin(theta)
            else:
                # Explicit physical coil density, with the same three source
                # compression regions. This is analytic geometry, not tracing.
                theta=2*math.pi*60*density_integral(t)/normalization
                x=20+270*t+2.2*math.cos(theta)
                yy=y+8*math.sin(theta)
            pts.append((x,yy))
        c.poly(pts,.55,(.3,.3,.3))
    y1=h*.36;y2=h*.77
    wave(y1,True);wave(y2,False)
    c.m('A',7,y1+5,13);c.m('B',7,y2+5,13)
    for y in [y1-29,y2-23]:c.text('파동의 진행방향',151,y-6,9,'center');c.arrow((126,y),(178,y),width=1.5,head=5)


def t2b1(c):
    y=c.h-18
    c.rect((7,y,294,y+5),fill=(.83,.83,.83),width=0,color=(.83,.83,.83))
    for x in [58,236]:c.rect((x,y-85,x+12,y),fill=(1,1,1),width=.8,color=(.5,.5,.5))
    c.rect((48,y-106,132,y-85),fill=(1,1,1),width=.8,color=(.5,.5,.5));c.rect((156,y-106,244,y-85),fill=(1,1,1),width=.8,color=(.5,.5,.5))
    c.rect((107,y-128,183,y-106),fill=(.8,.8,.8),color=(.6,.6,.6));c.text('A',145,y-111,13,'center')
    c.ellipse((143,y-19,149,y-5),fill=(1,.82,.26),color=(.65,.6,.4),width=.6)
    c.arrow((146,y-34),(146,y-68),head=5);c.text('B',136,y-7,11,'right')


def spring_box(c,x,y,w,h,slanted=False):
    c.rect((x,y,x+w,y+h),width=2)
    cx=x+w/2;cy=y+h/2
    c.spring((x+1,cy),(cx-5,cy),11,3,.8);c.spring((cx+5,cy),(x+w-1,cy),11,3,.8)
    top=(cx-18,y+1)if slanted else(cx,y+1)
    bottom=(cx-18,y+h-1)if slanted else(cx,y+h-1)
    c.spring(top,(cx,cy-5),10,3,.8);c.spring((cx,cy+5),bottom,10,3,.8)
    c.circle(cx,cy,4,fill=(.62,.62,.62),color=(.45,.45,.45))


def t2b2(c):
    h=c.h*.8;y=(c.h-h)/2
    spring_box(c,8,y,133,h);spring_box(c,159,y,133,h,True)
    c.text('(가)',14,y+13,9);c.text('(나)',165,y+13,9)


def car(c,x,y,color,label):
    c.poly([(x,y+19),(x+5,y+8),(x+16,y+8),(x+23,y),(x+43,y),(x+51,y+10),(x+59,y+13),(x+60,y+24),(x,y+24)],fill=color,color=color,close=True,width=.5)
    c.poly([(x+18,y+9),(x+25,y+2),(x+32,y+2),(x+32,y+9)],fill=(.82,.9,.94),color=(.82,.9,.94),close=True,width=.4)
    c.poly([(x+36,y+2),(x+42,y+2),(x+48,y+10),(x+36,y+10)],fill=(.82,.9,.94),color=(.82,.9,.94),close=True,width=.4)
    for xx in [x+12,x+47]:c.circle(xx,y+24,4.4,fill=(.45,.45,.45),color=(.45,.45,.45))
    c.text(label,x+50,y+20,11,'center')


def t2b3(c):
    y=c.h-32
    c.rect((0,y+3,300,y+8),fill=(.83,.83,.83),color=(.83,.83,.83),width=0)
    car(c,17,y-25,BLUE,'B');car(c,237,y-25,(.96,.8,.23),'A')
    for x,label in [(50,'150 km/h'),(270,'100 km/h')]:c.text(label,x,y-31,10.5,'center');c.arrow((x-9,y-28),(x+14,y-28),width=.6,head=3)
    c.arrow((76,y+15),(296,y+15),width=.45,head=2.5,both=True);c.text('100 km',186,y+29,10.5,'center')
    for x in [76,296]:c.line((x,y+9),(x,y+19),.45)


def t2b4(c):
    cx=150
    c.rect((48,6,252,15),fill=(.79,.79,.79),color=(.79,.79,.79),width=0)
    c.line((cx,15),(cx,41),2)
    c.spring((cx,41),(cx,c.h-94),14,16,2)
    c.line((cx,c.h-94),(cx,c.h-63),2)
    c.rect((118,c.h-63,182,c.h-8),fill=(.56,.56,.56),color=(.56,.56,.56),width=.8);c.m('m',150,c.h-25,43,align='center')


def t2b5(c):
    for index in range(4):
        y=4+index*135;ox=51;by=y+108;xx=277;top=y+31;xp=85;xe=221;end=255
        c.circle(12,y+13,7.3,width=.7);c.text(['ㄱ','ㄴ','ㄷ','ㄹ'][index],12,y+16,10,'center')
        axes(c,ox,by,xx,top-12,None,'속력',11)
        c.text('거리',291,by+5,11,'right');c.text('90 km/h',ox-4,top+3,10.2,'right')
        c.line((ox,top),(xp,top),.35,(.55,.55,.55),'[1 1] 0')
        for pos,lab in [(xp,'450 m'),(xe,'2250 m'),(end,'2700 m')]:c.line((pos,top),(pos,by),.35,(.55,.55,.55),'[1 1] 0');c.text(lab,pos,by+(27 if pos==end else 14),10.5,'center')
        color=(.87,.28,.24)
        if index in [0]:c.bezier((ox,by),(ox+15,by-10),(xp,by-21),(xp,top),.85,color)
        elif index in [1,2]:c.bezier((ox,by),(ox+2,by-19),(xp-8,top),(xp,top),.85,color)
        else:c.line((ox,by),(xp,top),.85,color)
        c.line((xp,top),(xe,top),.85,color)
        if index==0:c.bezier((xe,top),(xe,by-22),(end-12,by-9),(end,by),.85,color)
        elif index in [1,2]:c.bezier((xe,top),(xe+12,top),(end,by-14),(end,by),.85,color)
        else:c.line((xe,top),(end,by),.85,color)


def t2b6(c):
    R=min(56,c.h*.39);y=c.h*.50
    for k,cx in enumerate([77,227]):
        c.circle(cx,y,R,width=.7,color=(.55,.55,.55))
        c.line((cx,y),(cx,y-R),.6,(.55,.55,.55),'[2 2] 0')
        c.bezier((cx+3,y-R+6),(cx+R*.32,y-R*.75),(cx+R*.32,y-R*.25),(cx+3,y-6),.5,(.55,.55,.55),'[1.5 1.5] 0');c.m('R',cx+18,y-R/2)
        angles=[-90,30,150]if k==0 else[-90,90,180]
        points=[(cx+R*math.cos(math.radians(a)),y+R*math.sin(math.radians(a)))for a in angles]
        if k==0:c.poly(points+[points[0]],.6,(.65,.65,.65))
        else:
            c.poly([points[1],points[2],points[0]],.6,(.65,.65,.65))
            c.line(points[0],points[1],.6,(.6,.6,.6),'[2 2] 0')
        c.circle(cx,y,11,fill=(.4,.4,.4),color=(.4,.4,.4));c.text('M',cx,y+4.5,14,'center',color=(1,1,1))
        for x,yy in points:c.circle(x,yy,8.8,fill=(.55,.55,.55),color=(.55,.55,.55));c.m('m',x,yy+4,14.3,align='center')
        # Equality tick marks on each side preserve the two source triangles.
        for j in range(3):
            a=points[j];b=points[(j+1)%3];mx=(a[0]+b[0])/2;my=(a[1]+b[1])/2;dx=b[0]-a[0];dy=b[1]-a[1];L=math.hypot(dx,dy)
            if k==1:
                if j in [1,2]:c.circle(mx,my,1.7,fill=(1,1,1),width=.55,color=(.55,.55,.55))
            else:
                for dd in [-1.2,1.2]:c.line((mx+dd*dx/L-2*dy/L,my+dd*dy/L+2*dx/L),(mx+dd*dx/L+2*dy/L,my+dd*dy/L-2*dx/L),.5,(.55,.55,.55))


def t2b7(c):
    y=c.h-13;top=23;corner=170
    c.poly([(13,top),(corner,y),(292,y)],3)
    c.poly([(13,top),(13,y),(corner,y)],fill=(.81,.81,.81),color=(.81,.81,.81),close=True,width=0)
    c.line((13,top),(corner,y),3)
    # A remains aligned to the slope; B is on the horizontal section.
    c.poly([(24,top-10),(44,top+5),(33,top+20),(13,top+5)],fill=(.65,.65,.65),color=(.65,.65,.65),close=True)
    c.m('A',29,top+6,17,align='center')
    c.rect((228,y-27,261,y),fill=(.65,.65,.65),color=(.65,.65,.65));c.text('B',245,y-7,17,'center')
    c.arrow((38,top+25),(38,y-4),.9,head=4,both=True);c.m('h',27,(top+y)/2,18)


def t2b8(c):
    y=c.h-24;top=20
    c.rect((17,10,26,y+6),fill=(.9,.9,.9),color=(.9,.9,.9),width=0)
    c.poly([(25,top),(112,y),(292,y)],2.2)
    c.poly([(25,top),(112,y),(25,y)],fill=(.88,.88,.88),color=(.88,.88,.88),close=True,width=0)
    c.line((25,top),(112,y),2.2)
    c.poly([(48,top+8),(62,top+18),(54,top+31),(40,top+21)],fill=(.62,.62,.62),color=(.62,.62,.62),close=True);c.m('A',50,top+23,11,align='center')
    c.rect((222,y-15,242,y),fill=(.62,.62,.62),color=(.62,.62,.62));c.text('A',232,y-3,10,'center')
    c.arrow((48,top+32),(48,y),.65,head=3,both=True);c.m('h',37,y-26,13)
    c.arc(112,y,48,30,180,220,.8);c.m(r'\theta',82,y-10,12)
    c.line((57,top+24),(232,y),.6,(.7,.7,.7));c.arc(232,y,60,60,180,199,.6,(.7,.7,.7));c.m(r'\theta/2',166,y-27,11)
    c.arrow((112,y+15),(232,y+15),width=.7,head=3,both=True,dash='[2 2] 0');c.m('s',169,y+27,12,align='center')


def t2b9(c):
    left=50;top=18;right=250;bottom=c.h-89
    c.rect((left,top,right,bottom),fill=(.82,.82,.82),color=(.82,.82,.82),width=0)
    c.bezier((left,top),(90,top-17),(209,top-17),(right,top),.7,(.55,.55,.55));c.m('L',150,top-4,16,align='center')
    c.bezier((left,top),(left-20,70),(left-20,bottom-39),(left,bottom),.7,(.55,.55,.55));c.m('L',left-16,(top+bottom)/2,16,align='center')
    cx=99;cy=c.h-40
    c.arrow((cx,cy+24),(cx,cy-25),1,head=4);c.arrow((cx-25,cy),(cx+25,cy),1,head=4)
    c.poly([(cx-25,cy),(cx,cy-25),(cx,cy)],1.4)
    for dx,dy,lab in [(0,-32,'북'),(-36,4,'서'),(37,4,'동'),(0,37,'남')]:c.text(lab,cx+dx,cy+dy,13,'center')
    c.circle(248,c.h-39,14,fill=(.65,.65,.65),color=(.65,.65,.65));c.m('q',248,c.h-35,16,align='center');c.arrow((248,c.h-56),(248,c.h-88),1.1,head=5);c.m('v',263,c.h-62,17)


def t2b10(c):
    y=20;h=c.h-44
    c.rect((25,y,112,y+h),fill=(.76,.76,.76),color=(.5,.5,.5),width=.8);c.rect((33,y+8,104,y+h-8),fill=(1,1,1),color=(.5,.5,.5),width=.7)
    c.line((69,y+8),(69,y+39),.8);c.circle(69,y+42,7,fill=(.68,.68,.68),color=(.4,.4,.4))
    c.arrow((17,y+57),(17,y+35),width=3,color=(.5,.5,.5),head=6)
    c.text('(가)',9,y-7,11);c.text('(나)',139,y-7,11)
    ox=163;by=y+h-2;ex=277;peak=y+45
    axes(c,ox,by,ex,y+16,'t(s)','v(m/s)',8)
    c.poly([(ox,by),(185,peak),(237,peak),(260,by)],1)
    for x,l in [(185,'3'),(237,'12'),(260,'15')]:c.text(l,x,by+12,8,'center')
    c.text('0',ox-4,by+12,8,'right');c.m(r'\frac35g',ox-8,peak+6,12,align='right')


def bulb(c,x,y,label):
    c.circle(x,y,8.5,fill=(1,1,1),width=.7)
    c.arc(x,y+2,5,5,180,360,.7)
    c.text(label,x,y-12,10,'center')


def t2b11(c):
    # Circuit (가): A in series with parallel B/C; ammeter in B branch.
    c.poly([(8,57),(8,128),(154,128),(154,57),(137,57)],.9)
    c.line((8,57),(53,57),.9)
    c.poly([(53,57),(53,31),(137,31),(137,90),(53,90),(53,57)],.9)
    bulb(c,28,57,'A');bulb(c,77,31,'B');bulb(c,77,90,'C');c.meter(111,31,'A',9)
    c.rect((63,112,121,146),fill=(1,1,1),width=.7)
    c.circle(79,128,2.3,fill=(1,1,1),width=.5);c.circle(106,128,2.3,fill=(1,1,1),width=.5)
    c.line((63,128),(76.7,128),.9);c.line((108.3,128),(121,128),.9)
    c.text('(+)',79,123,7,'center');c.text('(−)',106,123,7,'center');c.text('전원 장치',92,141,8,'center')
    # Native meter enclosure and its two concentric readable scales.
    x0=174;y0=14;w=118;faceh=83
    c.rect((x0,y0,x0+w,y0+faceh),fill=(.96,.96,.96),width=.8,color=(.55,.55,.55))
    c.rect((x0+4,y0+4,x0+w-4,y0+faceh-4),fill=(1,1,1),width=.8,color=(.55,.55,.55))
    cx=x0+w/2;cy=y0+faceh-4;r=49
    c.arc(cx,cy,r,r,207,333,.8);c.arc(cx,cy,r-8,r-8,207,333,.6)
    for i in range(7):
        a=math.radians(210+i*20);p1=(cx+(r-4)*math.cos(a),cy+(r-4)*math.sin(a));p2=(cx+(r+4)*math.cos(a),cy+(r+4)*math.sin(a));c.line(p1,p2,.7)
        px=cx+(r+11)*math.cos(a);py=cy+(r+11)*math.sin(a);c.text(str(i-1),px,py+2,6,'center')
        inner=str((i-1)*100).replace('-','−')
        if i==6:inner+=' mA'
        c.text(inner,cx+(r-14)*math.cos(a),cy+(r-14)*math.sin(a)+2,5,'center')
    c.poly([(cx-2,cy),(cx,cy-51),(cx+2,cy)],fill=BLACK,color=BLACK,close=True,width=.3)
    c.arc(cx,cy,9,7,180,360,.7);c.text('A',x0+w-7,y0+48,6)
    c.poly([(x0,y0+faceh),(x0-5,y0+faceh+45),(x0+w+5,y0+faceh+45),(x0+w,y0+faceh)],fill=(.86,.86,.86),color=(.55,.55,.55),close=True,width=.6)
    for x,label in [(x0+19,'500 mA'),(cx,'5 A'),(x0+w-19,'+')]:
        c.ellipse((x-10,y0+faceh+11,x+10,y0+faceh+20),fill=(.76,.76,.76),color=(.5,.5,.5),width=.5)
        c.rect((x-7,y0+faceh+5,x+7,y0+faceh+16),fill=(.82,.82,.82),color=(.5,.5,.5),width=.5)
        c.ellipse((x-7,y0+faceh+1,x+7,y0+faceh+8),fill=(.9,.9,.9),color=(.5,.5,.5),width=.5)
        c.text(label,x,y0+faceh+33,8,'center')
    c.line((x0+19,y0+faceh+17),(x0+10,c.h-12),2,(.6,.6,.6));c.line((x0+w-19,y0+faceh+17),(x0+w-10,c.h-12),2,(.6,.6,.6))


def t2b12(c):
    A=(150,16);B=(37,c.h-22);C=(269,c.h-22);D=((A[0]+B[0])/2,(A[1]+B[1])/2);E=((A[0]+C[0])/2,(A[1]+C[1])/2);F=((B[0]+C[0])/2,B[1])
    c.poly([A,B,C,A],1,(.4,.4,.4),dash='[3 3] 0');c.poly([D,E,F,D],1,(.4,.4,.4),dash='[3 3] 0')
    for p,label,dx,dy in [(A,'A',0,-2),(B,'B',-12,7),(C,'C',12,7),(D,'D',-19,5),(E,'E',20,5),(F,'F',0,19)]:c.text(label,p[0]+dx,p[1]+dy,13,'center')
    for p in [D,E]:c.circle(*p,8,fill=(1,1,1),color=(.5,.5,.5))
    c.circle(*D,2.3,fill=BLACK)
    c.line((E[0]-5,E[1]-5),(E[0]+5,E[1]+5),.8);c.line((E[0]-5,E[1]+5),(E[0]+5,E[1]-5),.8)


def t2b13(c):
    by=c.h-23
    for x,w,h,label,wl,hl in [(29,50,35,'(가)','4 mm','3 mm'),(135,30,58,'(나)','2 mm','5 mm'),(226,50,47,'(다)','4 mm','4 mm')]:
        c.rect((x,by-h,x+w,by),fill=(.76,.76,.76),width=0,color=(.76,.76,.76))
        c.arrow((x,by-h-7),(x+w,by-h-7),width=.55,head=2.5,both=True);c.text(wl,x+w/2,by-h-11,11,'center')
        c.arrow((x-8,by),(x-8,by-h),width=.55,head=2.5,both=True);c.text(hl,x-11,by-h/2,11,'center',rotate=90)
        c.text(label,x+w/2,by+18,11,'center')


def t2b14(c):
    top=15;cy=c.h*.58
    for cx,ns,label in [(80,('S','N'),'(가)'),(245,('N','S'),'(나)')]:
        c.rect((cx-45,top,cx+45,top+9),fill=(.8,.8,.8),color=(.8,.8,.8),width=0)
        c.line((cx,top+9),(cx,cy-23),.65)
        c.ellipse((cx-14,cy-23,cx+14,cy+23),width=1.5,color=(.68,.33,.04))
        bar_magnet(c,cx-69,cy-8,35,15,ns)
        c.arrow((cx-60,cy-25),(cx-42,cy-25),width=2,head=4)
        c.text(label,cx,c.h-9,10,'center')


def pylon(c,x,y,h=46,w=27):
    top=y-h
    c.poly([(x-w/2,y),(x,top),(x+w/2,y)],.7)
    for t in [.23,.43,.65,.84]:
        yy=top+h*t;ww=w*t/2;c.line((x-ww,yy),(x+ww,yy),.6)
    for a,b in [(.23,.43),(.43,.65),(.65,.84),(.84,1)]:
        ya=top+h*a;yb=top+h*b;c.line((x-w*a/2,ya),(x+w*b/2,yb),.5);c.line((x+w*a/2,ya),(x-w*b/2,yb),.5)
    for yy,ww in [(top+5,12),(top+11,18),(top+18,25)]:c.line((x-ww,yy),(x+ww,yy),.8)


def t2b15(c):
    # The source has two independent outgoing transmission lines (A and B).
    x=50;cy=c.h*.46
    c.poly([(12,cy-16),(50,cy-29),(88,cy-15),(88,cy+26),(12,cy+26),(12,cy-16)],.8)
    c.line((50,cy-29),(50,cy+26),.6)
    for xx in [19,30,41,60,71,81]:c.line((xx,cy-13),(xx,cy+21),.5)
    for xx in [27,50,73]:
        c.rect((xx-5,cy+2,xx+5,cy+20),fill=(.88,.88,.88),width=.45)
        c.spring((xx-2,cy-10),(xx-2,cy+2),4,1.4,.45)
        c.spring((xx+2,cy-10),(xx+2,cy+2),4,1.4,.45)
        c.ellipse((xx-5,cy-1,xx+5,cy+5),fill=(.8,.8,.8),width=.45)
    c.text('변전소',50,cy-35,10,'center')
    pylon(c,183,cy-22,42,24);pylon(c,100,c.h-14,42,25)
    for off in [-5,0,5]:
        c.bezier((86,cy-12+off),(118,cy+3+off),(151,cy-31+off),(183,cy-61+off),.5,(.45,.45,.45))
        c.bezier((36,cy+20+off),(48,cy+36+off),(70,c.h-63+off),(100,c.h-54+off),.5,(.45,.45,.45))
        c.bezier((183,cy-61+off),(194,cy-56+off),(202,cy-52+off),(211,cy-51+off),.5,(.45,.45,.45))
        c.bezier((100,c.h-54+off),(128,c.h-33+off),(170,c.h-29+off),(211,c.h-35+off),.5,(.45,.45,.45))
    c.rect((211,9,294,cy+3),width=.7,color=(.5,.5,.5));c.text('A 지역',252,cy*.55,10,'center')
    c.rect((211,cy+38,294,c.h-9),width=.7,color=(.5,.5,.5));c.text('B 지역',252,(cy+38+c.h-9)/2+4,10,'center')
    c.m(r'P,\ V_A',118,cy-18,13);c.m(r'P,\ V_B',32,cy+44,13)
    c.text('송전선 A',184,cy-8,11,'center');c.text('송전선 B',100,c.h-2,11,'center')
    c.arrow((115,cy-13),(146,cy-28),width=.6,head=3);c.arrow((107,c.h-27),(162,c.h-27),width=.6,head=3)


def t2b16(c):
    top=22;bottom=c.h-28
    for x,level,label in [(15,top+40,'(가)'),(193,top+24,'(나)')]:
        c.rect((x,level,x+102,bottom),fill=BLUE,width=0,color=BLUE)
        c.poly([(x,top),(x+102,top),(x+102,bottom),(x,bottom),(x,top)],1.7)
        c.line((x,level),(x+102,level),.6,(.5,.5,.5));c.text(label,x+51,c.h-7,15,'center')
    c.rect((228,bottom-23,258,bottom),fill=(.71,.71,.71),width=0,color=(.71,.71,.71));c.text('A',243,bottom-6,13,'center',color=(1,1,1))
    c.poly([(146,top+40),(160,top+40),(160,top+31),(171,top+49),(160,top+66),(160,top+57),(146,top+57)],fill=BLACK,color=BLACK,close=True)


def t2b17(c):
    x=84;top=c.h*.46;thick=26
    c.rect((8,8,x,c.h-7),fill=(.5,.36,.04),color=(.35,.25,.05))
    c.rect((x,top,x+204,top+thick),fill=(.81,.81,.81),width=.8,color=(.5,.5,.5))
    c.rect((x,top+thick,x+204,top+2*thick),fill=(1,1,1),width=.8,color=(.5,.5,.5))
    c.text('금속 (가)',182,top+19,15,'center');c.text('금속 (나)',182,top+thick+19,15,'center')
    c.arrow((273,top-12),(273,top-47),width=7,head=13);c.text('A',287,top-24,15)


def t2b19(c):
    ox=27;by=c.h*.53;unit=26;amp=c.h*.31
    axes(c,ox,by,293,15,'진행 거리(m)','위치',10);c.text('(m)',ox-3,34,10,'right')
    pts=[(ox+i*.4,by-amp*math.sin((i*.4/unit)*math.pi/2))for i in range(476)]
    c.poly(pts,1.2)
    labels=[(0,'A'),(1,'B'),(2,'C'),(3,'D'),(4,'E')]
    for n,l in labels:
        x=ox+n*unit;y=by-amp*math.sin(n*math.pi/2);c.circle(x,y,2.7,fill=BLACK);c.text(l,x+(6 if n%2==0 else 0),y+(-8 if n!=3 else 18),12,'center')
    c.text('O',ox-9,by+5,12,'right')
    for n in range(1,7):c.line((ox+n*unit,by-3),(ox+n*unit,by+3),.6);c.text(str(n),ox+n*unit,by+15,11,'center')
    c.text('진행 방향',209,15,12,'center');c.arrow((186,24),(233,24),width=2,head=5)


T2b20_TABLE={
    'source':'KPhE_2023_T2b_KO.pdf','source_page':11,'source_rect':[417,132,742,260],
    'source_crop_width_pt':325,'source_crop_height_pt':128,
    'recommended_width_pt':232,'font':'Gulim','font_size_pt':9,
    'tables':[
        {'caption':'(가) 빛의 삼원색의 합성','column_widths':[.5,.5],
         'rows':[['합성하는 색','보이는 색'],['빨간색+초록색','노란색'],['빨간색+파란색','자홍색'],['초록색+파란색','청록색'],['빨간색+초록색+파란색','A']],
         'header_rows':[0],'shaded_columns':[],'alignment':'center'},
        {'caption':'(나) 조명에 따른 물체의 색','column_widths':[.25,.25,.25,.25],
         'rows':[['조명의 색','빨간색','초록색','파란색'],['빨간색 모자','B','C','D'],['초록색 바지','검은색','초록색','검은색']],
         'header_rows':[],'shaded_columns':[0],'alignment':'center'}]}


def t2b20(c):
    # Intentionally reflow the two native tables vertically at readable 9 pt.
    # No answers are filled into the four placeholders A/B/C/D.
    y=16;fs=9*300/232
    for table in T2b20_TABLE['tables']:
        c.text(table['caption'],3,y,fs+1);y+=12
        rowh=21
        widths=[300*w for w in table['column_widths']]
        for ri,row in enumerate(table['rows']):
            xx=2
            for ci,value in enumerate(row):
                width=widths[ci]-(4 if ci==len(row)-1 else 0)
                if ri in table['header_rows']or ci in table['shaded_columns']:c.rect((xx,y,xx+width,y+rowh),fill=(.87,.87,.87),width=0,color=(.87,.87,.87))
                c.text(value,xx+width/2,y+rowh*.7,fs,'center');xx+=width
            c.line((2,y),(298,y),.55,(.45,.45,.45));y+=rowh
        c.line((2,y),(298,y),.55,(.45,.45,.45))
        xx=2
        for width in widths[:-1]:xx+=width;c.line((xx,y-len(table['rows'])*rowh),(xx,y),.55,(.45,.45,.45))
        y+=27


DRAWINGS = {('T1b',1):t1b1,('T1b',2):t1b2,('T1b',4):t1b4,('T1b',6):t1b6,
('T1b',7):t1b7,('T1b',8):t1b8,('T1b',9):t1b9,('T1b',11):t1b11,
('T1b',12):t1b12,('T1b',13):t1b13,('T1b',14):t1b14,('T1b',15):t1b15,
('T1b',16):t1b16,('T1b',17):t1b17,('T1b',18):t1b18,('T1b',23):t1b23,
('T1b',25):t1b25,('T1b',26):t1b26}
DRAWINGS.update({('T2b',1):t2b1,('T2b',2):t2b2,('T2b',3):t2b3,('T2b',4):t2b4,
('T2b',5):t2b5,('T2b',6):t2b6,('T2b',7):t2b7,('T2b',8):t2b8,('T2b',9):t2b9,
('T2b',10):t2b10,('T2b',11):t2b11,('T2b',12):t2b12,('T2b',13):t2b13,
('T2b',14):t2b14,('T2b',15):t2b15,('T2b',16):t2b16,('T2b',17):t2b17,
('T2b',19):t2b19,('T2b',20):t2b20})


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--math-base-size',type=float,default=15.2)
    parser.add_argument('--part',choices=['all','T1b','T2b'],default='all')
    parser.add_argument('--only',help='Regenerate one existing asset, e.g. T1b:26; preserve the other manifest entries')
    parser.add_argument('--reviewed',action='store_true',help='Apply only after the source/native visual comparison has been reviewed')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);QA.mkdir(parents=True,exist_ok=True)
    idx=json.loads((ROOT/'tools/kphe_figures/index.json').read_text(encoding='utf8'))
    manifest={'version':1,'method':'manually authored native PDF geometry and real font text',
              'raster_images':False,'contour_tracing':False,'math_base_size':args.math_base_size,'figures':{}}
    if args.only and (OUT/'manifest.json').is_file():
        manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf8'))
    for key,g in idx['figures'].items():
        if g['source']not in ['KPhE_2023_T1b_KO.pdf','KPhE_2023_T2b_KO.pdf']:continue
        part,n=g['uses'][0]['part'],g['uses'][0]['number']
        if args.part!='all'and part!=args.part:continue
        if args.only and args.only!=f'{part}:{n}':continue
        if (part,n)not in DRAWINGS:continue
        typography.set_typography(ROOT/'tmp/kphe_archive/originals'/g['source'])
        w=300;h=w*(g['rect'][3]-g['rect'][1])/(g['rect'][2]-g['rect'][0])
        if (part,n)==('T2b',20):h=245
        if (part,n)==('T2b',3):h=96
        if (part,n)==('T2b',5):h=550
        native_width={('T2b',4):80,('T2b',9):185,('T1b',23):200}.get((part,n),232)
        c=Figure(w,h,args.math_base_size,native_width,1.74 if (part,n)==('T2b',11) else 1);DRAWINGS[(part,n)](c)
        if (part,n)==('T2b',11):
            # Keep each panel's native geometry but give the meter scales enough
            # printed size.  Both panels are vector forms, never raster images.
            old=c.doc;stacked=fitz.open();p=stacked.new_page(width=300,height=562)
            p.show_pdf_page(fitz.Rect(10,0,290,259),old,0,clip=fitz.Rect(0,0,160,148))
            p.show_pdf_page(fitz.Rect(10,294,290,548),old,0,clip=fitz.Rect(169,0,300,146))
            c.doc,c.page,c.h=stacked,p,562
            # Caption glyphs are a separate native-font form, avoiding a second
            # CID Gulim font resource after the source panels are imported.
            c.m(r'\mathrm{(가)}',150,276,align='center')
            c.m(r'\mathrm{(나)}',150,555,align='center')
            # Enlargement pointer stays outside the electrical circuit.  Its
            # first bend is above the upper branch, then its entire vertical
            # segment is to the right of the return wire (x=279.5).
            c.bezier((225,24),(251,4),(287,9),(291,43),1.1)
            c.bezier((291,43),(298,105),(298,222),(291,267),1.1)
            c.bezier((291,267),(283,289),(269,307),(250,318),1.1)
            c.arrow((262,310),(250,318),width=1.1,head=6)
        target=OUT/f'{part}-q{n:02d}-{key}.pdf';c.save(target)
        preview=QA/f'native-{key}.png';c.page.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False).save(preview)
        manifest['figures'][key]={'source':g['source'],'page':g['page'],'rect':g['rect'],'part':part,'number':n,
            'file':target.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'width_pt':c.w,'height_pt':c.h,'recommended_width_pt':native_width,
            'source_crop_width_pt':g['rect'][2]-g['rect'][0],
            'source_crop_height_pt':g['rect'][3]-g['rect'][1],
            'source_sha256':g['sourceSha256'],
            'image_xobjects':len(c.page.get_images(full=True)),
            'native_text_characters':len(c.page.get_text()),'status':'verified' if args.reviewed else 'awaiting_visual_review'}
        print(part,n,target.name,flush=True)
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if 'T2b20_TABLE'in globals():(OUT/'T2b20-table.json').write_text(json.dumps(T2b20_TABLE,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
