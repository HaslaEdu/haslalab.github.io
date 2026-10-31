"""Make dashed SVG strokes explicit for MuPDF's SVG-to-PDF renderer.

MuPDF accepts SVG dash attributes but currently paints these paths solid.
Separate M/L segments preserve the original dash geometry in both SVG and PDF.
Only straight paths/polylines and basic closed shapes are rewritten; unsupported
curves are retained unchanged rather than being approximated silently.
"""
import math,re,xml.etree.ElementTree as ET
ET.register_namespace('','http://www.w3.org/2000/svg')
ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
NUMBER=r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?'

def path_points(value):
    tokens=re.findall(NUMBER+r'|[A-Za-z]',value);i=0;command=None;current=(0.,0.);start=None;paths=[];points=[]
    while i<len(tokens):
        if re.fullmatch('[A-Za-z]',tokens[i]):command=tokens[i];i+=1
        if command is None:return None
        if command.upper() not in {'M','L','H','V','Z'}:return None
        if command.upper()=='Z':
            if start is not None:points.append(start)
            if points:paths.append(points);points=[]
            command=None;continue
        count=1 if command.upper() in {'H','V'} else 2
        if i+count>len(tokens) or any(re.fullmatch('[A-Za-z]',v) for v in tokens[i:i+count]):return None
        values=[float(v) for v in tokens[i:i+count]];i+=count;x,y=current
        if command.upper() in {'M','L'}:
            nx,ny=values
            if command.islower():nx+=x;ny+=y
        elif command.upper()=='H':nx=values[0]+(x if command.islower() else 0);ny=y
        else:nx=x;ny=values[0]+(y if command.islower() else 0)
        current=(nx,ny)
        if command.upper()=='M':
            if points:paths.append(points)
            points=[current];start=current;command='l' if command.islower() else 'L'
        else:points.append(current)
    if points:paths.append(points)
    return paths

def shape_points(element,minimum):
    tag=element.tag.rsplit('}',1)[-1];a=element.attrib
    if tag=='path':return path_points(a.get('d',''))
    if tag in {'polyline','polygon'}:
        values=[float(v) for v in re.findall(NUMBER,a.get('points',''))]
        if len(values)%2:return None
        points=list(zip(values[::2],values[1::2]))
        if tag=='polygon' and points:points.append(points[0])
        return [points]
    if tag=='line':return [[(float(a.get('x1',0)),float(a.get('y1',0))),(float(a.get('x2',0)),float(a.get('y2',0)))]]
    if tag=='rect':
        if float(a.get('rx',0)) or float(a.get('ry',0)):return None
        x,y,w,h=[float(a.get(k,0)) for k in ['x','y','width','height']]
        return [[(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)]]
    if tag in {'circle','ellipse'}:
        x,y=float(a.get('cx',0)),float(a.get('cy',0))
        rx=float(a.get('r',a.get('rx',0)));ry=float(a.get('r',a.get('ry',0)))
        count=max(240,min(4096,math.ceil(2*math.pi*max(rx,ry)/max(.1,minimum/4))))
        return [[(x+rx*math.cos(j*2*math.pi/count),y+ry*math.sin(j*2*math.pi/count)) for j in range(count+1)]]
    return None

def dashed(points,pattern,offset):
    if len(points)<2:return ''
    if len(pattern)%2:pattern=pattern*2
    total=sum(pattern);phase=offset%total;part=0
    while phase>=pattern[part]:phase-=pattern[part];part=(part+1)%len(pattern)
    remaining=pattern[part]-phase;result=[]
    for a,b in zip(points,points[1:]):
        length=math.hypot(b[0]-a[0],b[1]-a[1])
        if length<1e-9:continue
        used=0
        while used<length-1e-8:
            step=min(remaining,length-used)
            if part%2==0:
                p=(a[0]+(b[0]-a[0])*used/length,a[1]+(b[1]-a[1])*used/length)
                q=(a[0]+(b[0]-a[0])*(used+step)/length,a[1]+(b[1]-a[1])*(used+step)/length)
                result.append(f'M{p[0]:.4f} {p[1]:.4f} L{q[0]:.4f} {q[1]:.4f}')
            used+=step;remaining-=step
            if remaining<1e-8:part=(part+1)%len(pattern);remaining=pattern[part]
    return ' '.join(result)

def explicit_strokes(value):
    root=ET.fromstring(value)
    for element in root.iter():
        style=dict((item.split(':',1)[0].strip(),item.split(':',1)[1].strip()) for item in element.get('style','').split(';') if ':' in item)
        pattern=element.get('stroke-dasharray',style.get('stroke-dasharray',''))
        if not pattern or pattern=='none':continue
        values=[max(.001,float(v)) for v in re.findall(NUMBER,pattern)]
        if not values:continue
        paths=shape_points(element,min(values))
        if paths is None:continue
        offset=float(element.get('stroke-dashoffset',style.get('stroke-dashoffset','0')))
        for key in ['d','points','x','y','x1','y1','x2','y2','width','height','cx','cy','rx','ry','r','stroke-dasharray','stroke-dashoffset']:
            element.attrib.pop(key,None)
        style.pop('stroke-dasharray',None);style.pop('stroke-dashoffset',None)
        if style:element.set('style',';'.join(k+':'+v for k,v in style.items()))
        else:element.attrib.pop('style',None)
        namespace=element.tag.rsplit('}',1)[0]+'}' if '}' in element.tag else ''
        element.tag=namespace+'path';element.set('d',' '.join(dashed(points,values,offset) for points in paths));element.set('fill','none')
    return ET.tostring(root,encoding='unicode')
