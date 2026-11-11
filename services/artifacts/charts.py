"""Compact generated bar previews; original Tableau views use their REST PNG instead."""
import io
from decimal import Decimal,InvalidOperation

def bar_image(data):
    rows=data.get('rows',[])
    if not rows or len(rows)>30:return None
    metric=next((k for k in ('notional','sales','events','value') if k in rows[0]),None)
    label=next((k for k in rows[0] if k not in (metric,'currency')),None)
    if not metric or not label:return None
    try:values=[Decimal(str(r[metric])) for r in rows]
    except (InvalidOperation,KeyError):return None
    if any(not v.is_finite() or v<0 for v in values) or max(values)==0:return None
    from PIL import Image,ImageDraw
    image=Image.new('RGB',(1100,120+len(rows)*36),'white');draw=ImageDraw.Draw(image)
    draw.text((20,20),f"{data.get('operation','Authorized result')} - {metric} - {data.get('source_mode','LIVE export')}",fill='#183333')
    for i,(row,value) in enumerate(zip(rows,values)):
        y=70+i*36;draw.text((20,y+4),str(row[label])[:26],fill='#183333')
        width=int(value/max(values)*650);draw.rectangle((240,y,240+width,y+24),fill='#348771')
        draw.text((900,y+4),str(value),fill='#183333')
    stream=io.BytesIO();image.save(stream,format='PNG');return stream.getvalue()
