"""Measure complete 2023 questions before placing them in the official columns."""
import re
from kphe_template import TOP, BOTTOM, equation_pdf
from kphe_redraw import native_figure, dimensions

def values(value):
    return [value] if isinstance(value,str) else value

def figure_list(question):
    return question.get('figures',[]) or ([question['figure']] if question.get('figure') else [])

def measure_question(flow,question,part):
    total=0.
    for value in values(question.get('paragraphs',question.get('statement',[]))):
        if re.fullmatch(r'\s*\$[^$]+\$\s*',value):
            _,_,height,_=equation_pdf(value.strip()[1:-1],9.81)
            total+=height+18
        else:total+=flow.paragraph_height(value)
    for figure in figure_list(question):
        _,item=native_figure(figure['source'],figure['page'],figure['rect'])
        total+=dimensions(item,flow.width,155,flow.figure_scale)[1]+8
    for value in question.get('after_figure',[]):total+=flow.paragraph_height(value)
    givens=values(question.get('givens',[]))
    if givens:
        inset=flow.right_inset;flow.right_inset=5
        total+=29+sum(flow.paragraph_height(value,gap=0) for value in givens)
        flow.right_inset=inset
    indent=flow.indent;flow.indent=0 if part[-1]=='d' else 4
    for i,value in enumerate(question.get('options',question.get('choices',[]))):
        total+=flow.paragraph_height('①②③④⑤'[i]+' '+value,gap=0)
    flow.indent=indent
    return total

def plan_question(flow,question,part):
    flow.indent=12.3;flow.right_inset=0
    tested=[]
    for size,scale in [(9.8,1.),(9.8,.95),(9.8,.9),(9.03,1.),(9.03,.95),(9.03,.9),(8.14,1.),(8.14,.9),(8.14,.8)]:
        flow.body_size=size;flow.figure_scale=scale
        height=measure_question(flow,question,part)
        tested.append({'body_point':size,'figure_scale':scale,'height':round(height,3)})
        if height<=BOTTOM-TOP-2:
            return dict(tested[-1],available_height=round(BOTTOM-TOP,3))
    raise ValueError(f'Question {question["number"]} cannot fit one column: {tested}')

def render_question(flow,question,part):
    flow.problem_start(question['number'])
    for value in values(question.get('paragraphs',question.get('statement',[]))):
        if re.fullmatch(r'\s*\$[^$]+\$\s*',value):flow.display_math(value)
        else:flow.paragraph(value)
    import pymupdf as fitz
    from kphe_template import INPUT
    for figure in figure_list(question):
        source=fitz.open(INPUT/figure['source'])
        flow.figure(source,figure['page'],figure['rect'],max_height=155)
    for value in question.get('after_figure',[]):flow.paragraph(value)
    flow.boxed_givens(values(question.get('givens',[])))
    indent=flow.indent;flow.indent=0 if part[-1]=='d' else 4
    for i,value in enumerate(question.get('options',question.get('choices',[]))):
        flow.paragraph('①②③④⑤'[i]+' '+value,gap=0)
    flow.indent=indent
