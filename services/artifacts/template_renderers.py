"""Fixed layouts: models choose evidence, never coordinates, formulas or file paths."""
import io
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from xml.sax.saxutils import escape


def fact_line(e):
    return f"{e.get('metric') or e['calculation_id']}: {e['value'] if e['value'] is not None else 'Information unavailable'} {e['unit']} | {e['as_of']} | {e['source_mode']} [{e['id']}]"


def evidence_line(e):
    return fact_line(e)+' | Source: '+e['source_id']+' | filters: '+json.dumps(e.get('filters',{}))+' | grain: '+e.get('grain','unknown')+' | metric version: '+e.get('metric_version','unknown')


def section_lines(section, report, rules):
    key=section['section_id'];facts={e['id']:e for e in report['evidence']}
    if key=='limitations':
        return report['warnings'] or ['No additional limitations were recorded. Evidence scope and reporting dates still apply.']
    if key=='scope':
        return [f"{e['source_id']} | {e['source_mode']} | {e['as_of']} | grain: {e.get('grain','unknown')} | filters: {json.dumps(e.get('filters',{}))}" for e in report['evidence'][:rules['max_items']]]
    if key=='definitions':
        return ['Information unavailable: approved formula/owner definitions are not included in the saved evidence. Metric versions are listed in the evidence register.']
    group={'summary':'summary','actions':'recommended_actions'}.get(key)
    if group:
        claims=report['narrative'].get(group,[])
        selected=set(section['evidence_ids'])
        lines=[c['text']+' ['+', '.join(c['evidence_ids'])+']' for c in claims if set(c['evidence_ids'])<=selected]
        if lines:return lines
        if key=='actions':return ['Information unavailable: no evidence-supported actions, owners or timings were provided.']
    lines=[fact_line(facts[e]) for e in section['evidence_ids']]
    return lines or ['Information unavailable: no verified evidence was selected for this section. Run an authorized analysis covering this topic.']


def chunks(lines, capacity=1100, max_items=5):
    """Paginate all content without silently dropping text."""
    pages=[];page=[];size=0
    for line in lines:
        if len(line)>capacity: raise ValueError('Document text exceeds layout capacity; narrow the report.')
        if page and (size+len(line)>capacity or len(page)>=max_items):pages.append(page);page=[];size=0
        page.append(line);size+=len(line)
    if page:pages.append(page)
    return pages


def write_template(fmt,path,report,images,registry):
    selection=report['template'];manifest=registry.get(selection['template_id'],fmt)
    report['warnings']=list(report['warnings'])
    freshness=manifest.get('freshness_days')
    if freshness is not None:
        from datetime import datetime,timezone,timedelta
        if type(freshness) is not int or not 0<=freshness<=3650:raise ValueError('Invalid configured freshness limit.')
        today=datetime.now(timezone(timedelta(hours=8))).date()
        for asof in report['as_of']:
            try:
                if (today-date.fromisoformat(asof)).days>freshness:report['warnings'].append('Stale: as of '+asof)
            except ValueError:report['warnings'].append('Freshness unavailable: unrecognized reporting date '+asof)
    facts={e['id']:e for e in report['evidence']}
    from .templates import DocumentPlan
    registry.validate_plan(DocumentPlan.model_validate(selection['plan']),manifest,facts,len(images))
    rules={s['id']:s for s in manifest['sections']}
    sections=[(rules[s['section_id']],s) for s in selection['plan']['sections']]
    meta=[report['title'],'Reporting period: '+report.get('reporting_period','Not supplied'),
          'As of: '+', '.join(report['as_of'])+' | Business timezone: Asia/Hong_Kong',
          'Audience: '+manifest['audience'],'Prepared by: '+report['prepared_by'],
          'DRAFT | '+report['mode']+' | '+manifest['classification']]
    if fmt=='pptx':
        from pptx import Presentation
        from pptx.util import Inches,Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import MSO_AUTO_SIZE
        prs=Presentation(registry.path(manifest['files'][fmt]))
        layout=manifest['pptx_layout']
        if len(prs.slides):raise ValueError('PPTX shell must contain no example slides.')
        def text(slide,x,y,w,h,value,size=16,color='1A1A1A',bold=False,box=None):
            box=box if box is not None else slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
            box.left=Inches(x);box.top=Inches(y);box.width=Inches(w);box.height=Inches(h);tf=box.text_frame
            tf.word_wrap=True;tf.auto_size=MSO_AUTO_SIZE.NONE
            for i,line in enumerate(value.split('\n')):
                p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=line
                p.font.name=layout['font'];p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=RGBColor.from_string(color)
                p.space_after=Pt(12)
            return box
        def slide(title,body=None):
            s=prs.slides.add_slide(prs.slide_layouts[5]);text(s,*layout['title_box'],title,layout['title_size'],layout['title_color'],True,box=s.shapes.title)
            if body:text(s,*layout['body_box'],'\n'.join(body),layout['body_size'],layout['body_color'])
            text(s,*layout['footer_box'],f"DRAFT | {report['mode']} | {manifest['classification']} | {len(prs.slides)}",10,layout['caption_color'])
            return s
        slide(manifest['title']+' — DRAFT',meta[1:])
        body_count=1
        for rule,section in sections:
            if rule['id']=='evidence':continue
            lines=section_lines(section,report,rule)
            pages=chunks(lines,max_items=min(rule['max_items'],5))
            for page in pages:slide(rule['title'],page);body_count+=1
            for index in section['image_indices']:
                from PIL import Image
                s=slide(rule['title']);raw=images[index]
                with Image.open(io.BytesIO(raw)) as im:w,h=im.size
                scale=min(11.9/w,4.5/h)
                s.shapes.add_picture(io.BytesIO(raw), Inches(.7), Inches(1.7),width=Inches(w*scale),height=Inches(h*scale))
                body_count+=1
        if body_count>manifest['limits']['max_body_slides']:raise ValueError('Executive body exceeds slide budget; narrow the report.')
        for page in chunks([evidence_line(e) for e in report['evidence']],capacity=1300,max_items=8):
            s=slide('Evidence appendix')
            text(s,.7,1.7,11.9,4.7,'\n'.join(page),12)
        for page in chunks([d['code']+': '+d['text'] for d in selection['disclosures']],max_items=4):slide('Important information',page)
        if len(prs.slides)>manifest['limits']['max_total_slides']:raise ValueError('Evidence appendix exceeds slide budget.')
        prs.save(path)
    elif fmt=='docx':
        from docx import Document
        from docx.shared import Inches
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        doc=Document(registry.path(manifest['files'][fmt]))
        if [p.text for p in doc.paragraphs]!=['{{document_body}}']:raise ValueError('DOCX body placeholder invalid.')
        doc.paragraphs[0].text=''
        header=doc.sections[0].header.paragraphs[0];header.text=manifest['title']+' | '+', '.join(report['as_of'])
        footer=doc.sections[0].footer.paragraphs[0];footer.text=manifest['classification']+' | DRAFT | Page '
        for field in ('PAGE','NUMPAGES'):
            if field=='NUMPAGES':footer.add_run(' of ')
            node=OxmlElement('w:fldSimple');node.set(qn('w:instr'),field);footer._p.append(node)
        doc.add_heading(meta[0],0)
        for line in meta[1:]:doc.add_paragraph(line)
        for rule,section in sections:
            doc.add_heading(rule['title'],1)
            lines=[evidence_line(e) for e in report['evidence']] if rule['id']=='evidence' else section_lines(section,report,rule)
            for line in lines:doc.add_paragraph(line)
            for index in section['image_indices']:doc.add_picture(io.BytesIO(images[index]),width=Inches(6))
        doc.add_heading('Important information',1)
        for d in selection['disclosures']:doc.add_paragraph(d['code']+': '+d['text'])
        # Word pagination depends on installed fonts. Bound the input; disclose visual acceptance separately.
        if sum(len(p.text) for p in doc.paragraphs)>40000:raise ValueError('DOCX text budget exceeded.')
        doc.save(path)
    elif fmt=='xlsx':
        from openpyxl import load_workbook
        from openpyxl.styles import Font,PatternFill,Alignment
        from openpyxl.worksheet.table import Table,TableStyleInfo
        from .service import ArtifactService
        wb=load_workbook(registry.path(manifest['files'][fmt]))
        if set(wb.sheetnames)!={'README','Summary','Evidence','Limitations'}:raise ValueError('Workbook shell sheets invalid.')
        for ws in wb:
            if ws.max_row>1:raise ValueError('Workbook shell contains example data.')
            ws.delete_rows(1,ws.max_row)
        for line in meta+[d['code']+': '+d['text'] for d in selection['disclosures']]:wb['README'].append([ArtifactService._safe(line)])
        wb['README'].append(['Stored derived values are executed snapshots. No unapproved Excel formulas are created.'])
        headers=['Evidence ID','Metric','Value','Unit','As of','Source mode','Source','Status']
        wb['Summary'].append(headers)
        data=wb.create_sheet('Data_Evidence');data.append(headers)
        def numeric(e):
            if e['value'] is None:return None,'Missing: value not provided'
            try:
                n=Decimal(str(e['value']))
                if not n.is_finite():raise InvalidOperation()
                if len(n.as_tuple().digits)>15:return str(e['value']),'Text retained to preserve precision beyond Excel numeric capacity'
                return int(n) if n==n.to_integral_value() else float(n),''
            except (InvalidOperation,ValueError):return ArtifactService._safe(e['value']),'Non-numeric evidence'
        for e in report['evidence']:
            value,status=numeric(e)
            try:asof=date.fromisoformat(e['as_of'])
            except ValueError:asof=ArtifactService._safe(e['as_of'])
            row=[ArtifactService._safe(e['id']),ArtifactService._safe(e.get('metric') or e['calculation_id']),value,ArtifactService._safe(e['unit']),asof,e['source_mode'],ArtifactService._safe(e['source_id']),status]
            for name in ('Summary','Data_Evidence'):wb[name].append(row)
        ev=wb['Evidence'];ev.append(['ID','Source','Mode','As of','Filters','Grain','Definition version','Calculation','Full manifest'])
        for e in report['evidence']:ev.append([ArtifactService._safe(e.get(k,'')) for k in ('id','source_id','source_mode','as_of')]+[ArtifactService._safe(json.dumps(e.get('filters',{}))),ArtifactService._safe(e.get('grain')),ArtifactService._safe(e.get('metric_version')),ArtifactService._safe(e.get('calculation_id')),ArtifactService._safe(json.dumps(e))])
        from openpyxl.drawing.image import Image
        for i,image in enumerate(images):
            sheet=wb.create_sheet('Chart '+str(i+1));sheet.append(['DRAFT | '+report['mode']+' | Authorized snapshot; see Evidence for scope and dates.'])
            sheet.add_image(Image(io.BytesIO(image)),'A3')
        wb['Limitations'].append(['Limitations'])
        for line in report['warnings']+['Data_Evidence contains verified scalar evidence, not a reconstructed position list or unseen underlying rows.']:wb['Limitations'].append([ArtifactService._safe(line)])
        for ws in wb:
            if ws.max_row>manifest['limits']['max_rows_per_sheet']+1:raise ValueError('Workbook row budget exceeded.')
            ws.freeze_panes='A2';ws.sheet_state='visible';ws.sheet_properties.tabColor='C00000' if report['mode']!='LIVE' else '141414'
            for cell in ws[1]:cell.font=Font(name='Arial',bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='C00000')
            for row in ws:
                for cell in row:
                    cell.alignment=Alignment(wrap_text=True,vertical='top')
                    if isinstance(cell.value,date):cell.number_format='dd mmm yyyy'
            for col in ws.columns:ws.column_dimensions[col[0].column_letter].width=30
            if ws.title not in ('README','Limitations') and not ws.title.startswith('Chart ') and ws.max_row>1:
                table=Table(displayName=ws.title.replace('_','')+'Table',ref=ws.dimensions)
                table.tableStyleInfo=TableStyleInfo(name='TableStyleMedium2',showRowStripes=True)
                ws.add_table(table)
        wb.save(path)
    else:
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,PageBreak
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.colors import HexColor
        from reportlab.lib.pagesizes import A4
        from PIL import Image as PILImage
        styles=getSampleStyleSheet();styles['BodyText'].fontName='Helvetica';styles['Heading1'].textColor=HexColor('#C00000')
        story=[]
        def paragraph(line,style='BodyText'):story.extend([Paragraph(escape(str(line)),styles[style]),Spacer(1,8)])
        for line in meta:paragraph(line)
        for rule,section in sections:
            paragraph(rule['title'],'Heading1')
            lines=[evidence_line(e) for e in report['evidence']] if rule['id']=='evidence' else section_lines(section,report,rule)
            for line in lines:paragraph(line)
            for index in section['image_indices']:
                with PILImage.open(io.BytesIO(images[index])) as im:w,h=im.size
                scale=min(450/w,560/h);story.append(Image(io.BytesIO(images[index]),width=w*scale,height=h*scale))
        paragraph('Important information','Heading1')
        for d in selection['disclosures']:paragraph(d['code']+': '+d['text'])
        def footer(canvas,doc):
            if doc.page>manifest['limits']['max_pages']:raise ValueError('PDF page budget exceeded.')
            canvas.saveState();canvas.setFont('Helvetica',8)
            canvas.drawString(45,25,f"DRAFT | {report['mode']} | Page {doc.page}");canvas.restoreState()
        SimpleDocTemplate(str(path),pagesize=A4,leftMargin=62,rightMargin=62,topMargin=62,bottomMargin=62).build(story,onFirstPage=footer,onLaterPages=footer)
