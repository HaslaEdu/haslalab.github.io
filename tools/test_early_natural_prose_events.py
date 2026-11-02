"""Font-boundary event-order regressions for original numerical prose faces."""
from izho_natural_spacing import baseline_lines,boundary_gap,authored_fragment
class Page:
 def __init__(self,traces):self.traces=traces
 def get_texttrace(self):return self.traces

def trace(font,text,xs,y=50,size=10):
 return dict(font=font,size=size,type=0,seqno=0,dir=(1,0),color=(0,0,0),opacity=1,
  chars=[(ord(c),ord(c),(x,y),(x,y-8,x+5,y+2))for c,x in zip(text,xs)])
def check(traces,text,width=200,predicate=None):
 p=dict(text=text,point=[20,50],width=width)
 ls=baseline_lines(Page(traces),allowed_line_rects=[[10,35,250,60]],prose_placements=[p],prose_trace_predicate=predicate)
 assert len(ls)==1 and len(ls[0]['tokens'])==1,ls
 actual=ls[0]['tokens'][0]['text']
 assert actual==text,(actual,text)
 return actual

def run():
 cases=[]
 cases.append(check([trace('NotoSerifCJKkr-Regular','제회 결선 문제',[20,46,56,61,71,81,86,96]),trace('TimesNewRomanPSMT','22',[30,38])],'제22회 결선 문제'))
 cases.append(check([trace('NotoSerifCJKkr-Regular','쪽 / 총 쪽',[30,40,45,50,60,70,100]),trace('TimesNewRomanPSMT','12',[20,90])],'1쪽 / 총 2쪽'))
 cases.append(check([trace('SimSun','Page of ',[20,25,30,35,40,60,65,70]),trace('TimesNewRomanPSMT','12',[50,80])],'Page 1 of 2',predicate=lambda rs:True))
 assert authored_fragment('문제를 풀기 위해 아래 그림을 그리자.','문제를풀기위해아래그림을그리자')=='문제를 풀기 위해 아래 그림을 그리자'
 a=dict(text='S。',kind='native',size=10,x1=35);b=dict(text='B',kind='native',size=10,x0=60)
 assert boundary_gap(a,b)==2.5
 a['text']='x+1';assert boundary_gap(a,b)==25
 return dict(passed=True,event_order_cases=cases,unique_authored_fragment=True,sentence_period_gap=True,internal_native_gap_preserved=True)
if __name__=='__main__':
 import json;print(json.dumps(run(),ensure_ascii=False))
