import pymupdf, sys
f='eot/out/Eotvos_2025_T_KO.pdf'
d=pymupdf.open(f); p=d[0]
pix=p.get_pixmap(dpi=300, clip=pymupdf.Rect(590,250,592,252)); c=pix.pixel(2,2); col=tuple(v/255 for v in c[:3])
r=pymupdf.Rect(593.5,252.0,609.5,259.4)
p.draw_rect(r, color=None, fill=col, overlay=True)
p.insert_font(fontname='hb', fontfile='C:/Windows/Fonts/HANBatang.ttf')
p.insert_text((590.2,258.3), '질량 중심', fontname='hb', fontsize=6.6)
d.saveIncr() if False else d.save(f+'.tmp', garbage=4, deflate=True)
import os; d.close(); os.replace(f+'.tmp', f)
print('ok', col)
