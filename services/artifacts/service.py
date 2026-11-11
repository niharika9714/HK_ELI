import hashlib
import json
import time
import uuid
from pathlib import Path
from hk_platform.runtime.database import connect


TYPES={'docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
       'pptx':'application/vnd.openxmlformats-officedocument.presentationml.presentation',
       'xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','pdf':'application/pdf'}


class ArtifactService:
    def __init__(self,root,db_path,ttl=900):
        from .templates import TemplateRegistry
        self.templates=TemplateRegistry()
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
        self.db_path=str(db_path);self.ttl=ttl
        with connect(self.db_path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY,owner TEXT,format TEXT,expires REAL,manifest TEXT,hash TEXT)')

    def generate(self,owner,answer,formats,images=None):
        facts={e['id']:e for e in answer.get('evidence',[])}
        for group in ('summary','insights','recommended_actions'):
            for claim in answer.get('narrative',{}).get(group,[]):
                if any(e not in facts for e in claim['evidence_ids']):raise ValueError('Artifact contains ungrounded claim.')
        if not facts:raise ValueError('Reports require verified evidence.')
        report={'title':'HK ELI Intelligence — DRAFT','approval':'draft; business review required',
                'as_of':sorted({e['as_of'] for e in facts.values()}),'source_modes':sorted({e['source_mode'] for e in facts.values()}),
                'disclaimer':'MOCK values are synthetic and indicative. LIVE values cover cited authorized exports only.',
                'narrative':answer.get('narrative',{}),'evidence':list(facts.values()),'warnings':answer.get('warnings',[]),
                'sections':answer.get('report_sections',[]),'image_count':len(images or [])}
        report.update(document_context=answer.get('document_context',{}),
            authorization_context=answer.get('authorization_context'),required_permissions=answer.get('required_permissions',[]),
            selected_dashboards=answer.get('selected_dashboards',[]))
        report.update(mode='MIXED' if len(report['source_modes'])>1 else report['source_modes'][0],
            prepared_by=owner,reporting_period=answer.get('reporting_period','Not supplied'),
            document_plans=answer.get('document_plans',{}))
        report['document_chart_snapshots']=answer.get('document_chart_snapshots',[])
        result=[]
        prepared=[]
        for fmt in dict.fromkeys(formats):
            if fmt not in TYPES:raise ValueError('Unsupported artifact format.')
            selection=report['document_plans'].get(fmt)
            if not selection:raise ValueError('Validated document plan required.')
            manifest=self.templates.get(selection['template_id'],fmt)
            if selection['template_version']!=manifest['version']:raise ValueError('Template version changed; replan document.')
            selected=dict(selection,disclosures=self.templates.disclosures_for(list(facts.values()),manifest))
            asset=manifest['files'][fmt]
            selected['asset_sha256']=hashlib.sha256(self.templates.path(asset).read_bytes()).hexdigest() if asset else None
            selected['instructions_sha256']=hashlib.sha256(manifest['instructions'].encode()).hexdigest()
            prepared.append((fmt,selected))
        staged=[]
        try:
            for fmt,selection in prepared:
                report['template']=selection
                key=uuid.uuid4().hex;path=self.root/(key+'.'+fmt)
                staged.append((key,path))
                self._write(fmt,path,report,images or [])
                if path.stat().st_size>32000000:raise ValueError('Artifact capacity exceeded.')
                digest=hashlib.sha256(path.read_bytes()).hexdigest()
                manifest=json.dumps(report,ensure_ascii=False)
                with connect(self.db_path) as db:
                    db.execute('INSERT INTO artifacts VALUES (?,?,?,?,?,?)',(key,owner,fmt,time.time()+self.ttl,manifest,digest))
                result.append({'id':key,'format':fmt,'status':'draft','url':'/api/v1/artifacts/'+key,'sha256':digest,
                               'template_id':selection['template_id'],'template_version':selection['template_version']})
        except Exception:
            for key,path in staged:
                path.unlink(missing_ok=True)
                with connect(self.db_path) as db:db.execute('DELETE FROM artifacts WHERE id=? AND owner=?',(key,owner))
            raise
        return result

    def _write(self,fmt,path,report,images):
        from .template_renderers import write_template
        return write_template(fmt,path,report,images,self.templates)

    @staticmethod
    def _safe(value):
        value='' if value is None else str(value)
        return "'"+value if value.startswith(('=','+','-','@')) else value

    def get(self,owner,key):
        with connect(self.db_path) as db:
            row=db.execute('SELECT format,expires,manifest,hash FROM artifacts WHERE id=? AND owner=?',(key,owner)).fetchone()
        if not row or row[1]<time.time():raise KeyError('Artifact absent or expired.')
        path=self.root/(key+'.'+row[0])
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=row[3]:raise ValueError('Artifact integrity failed.')
        return path,TYPES[row[0]],json.loads(row[2])

    def cleanup(self):
        with connect(self.db_path) as db:
            expired=db.execute('SELECT id,format FROM artifacts WHERE expires<?',(time.time(),)).fetchall()
            for key,fmt in expired:(self.root/(key+'.'+fmt)).unlink(missing_ok=True)
            db.execute('DELETE FROM artifacts WHERE expires<?',(time.time(),))
