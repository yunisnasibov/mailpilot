import json,sqlite3,secrets,threading,csv,io
from pathlib import Path
from datetime import datetime,timezone
from contextlib import contextmanager
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import JSONResponse,FileResponse,Response
from .models import EmailInput,Review,DraftReceipt
from . import ai
from .samples import samples

ROOT=Path(__file__).resolve().parents[1];DB=ROOT/'data/mailpilot.sqlite3';LOCK=threading.Lock()
app=FastAPI(title='MailPilot',docs_url=None,redoc_url=None,openapi_url=None)
def now():return datetime.now(timezone.utc).isoformat()
@contextmanager
def db():
    DB.parent.mkdir(exist_ok=True,parents=True)
    c=sqlite3.connect(DB,timeout=20);c.row_factory=sqlite3.Row
    c.execute('CREATE TABLE IF NOT EXISTS emails(id INTEGER PRIMARY KEY, message_id TEXT UNIQUE, original TEXT NOT NULL, analysis TEXT, draft TEXT NOT NULL DEFAULT "", status TEXT NOT NULL DEFAULT "Pending", source TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0, gmail_draft_id TEXT NOT NULL DEFAULT "", draft_state TEXT NOT NULL DEFAULT "none", error TEXT NOT NULL DEFAULT "", created TEXT NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,email_id INTEGER,action TEXT,created TEXT)')
    try:
        with c:yield c
    finally:c.close()
def event(c,id,action):c.execute('INSERT INTO events(email_id,action,created) VALUES(?,?,?)',(id,action,now()))
def unpack(row):
    d=dict(row);d['original']=json.loads(d['original']);d['analysis']=json.loads(d['analysis']) if d['analysis'] else None
    return d
def get(id):
    with db() as c:r=c.execute('SELECT * FROM emails WHERE id=?',(id,)).fetchone()
    if not r:raise HTTPException(404,'Email not found')
    return unpack(r)
def capture(email,source):
    with db() as c:
        cur=c.execute('INSERT OR IGNORE INTO emails(message_id,original,source,created) VALUES(?,?,?,?)',(email.message_id,json.dumps(email.model_dump()),source,now()))
        r=c.execute('SELECT * FROM emails WHERE message_id=?',(email.message_id,)).fetchone()
        if cur.rowcount:event(c,r['id'],'Email received from '+source)
        return unpack(r),not bool(cur.rowcount)
def run_analysis(id):
    if not LOCK.acquire(blocking=False):raise HTTPException(409,'Analysis is busy. Retry shortly.')
    try:
        r=get(id)
        if r['analysis']:return r
        try:result=ai.analyze(EmailInput(**r['original']))
        except ai.AIError as e:
            with db() as c:
                c.execute('UPDATE emails SET error=?,status="Retry needed" WHERE id=?',(str(e),id));event(c,id,'Analysis failed; original email preserved')
            raise HTTPException(502,str(e))
        with db() as c:
            c.execute('UPDATE emails SET analysis=?,draft=?,status=?,draft_state=?,error="",revision=revision+1 WHERE id=?',
                (json.dumps(result),result['suggested_reply'],'Draft ready' if result['action_required'] else 'No action','ready' if result['action_required'] else 'none',id))
            event(c,id,'Gemini analysis validated and saved')
        return get(id)
    finally:LOCK.release()

@app.middleware('http')
async def local_boundary(request:Request,call_next):
    if request.headers.get('host') not in ('127.0.0.1:4175','localhost:4175','testserver'):
        return JSONResponse({'detail':'Unrecognized host'},status_code=403)
    if request.method not in ('GET','HEAD'):
        if request.headers.get('origin') not in (None,'http://127.0.0.1:4175','http://localhost:4175'):
            return JSONResponse({'detail':'Unrecognized origin'},status_code=403)
        body=await request.body()
        if len(body)>100000:return JSONResponse({'detail':'Payload too large'},status_code=413)
    if request.url.path.startswith('/api/intake'):
        expected=ai.settings()['INTAKE_TOKEN'];actual=request.headers.get('authorization','')
        if not expected or not secrets.compare_digest(actual,'Bearer '+expected):
            return JSONResponse({'detail':'Intake authentication required'},status_code=401)
    response=await call_next(request);response.headers['X-Content-Type-Options']='nosniff';response.headers['Cache-Control']='no-store';return response

@app.get('/api/config')
def config():
    s=ai.settings()
    with db() as c:live=c.execute('SELECT count(*) FROM emails WHERE gmail_draft_id!=""').fetchone()[0]
    return {'gemini_configured':bool(s['GEMINI_API_KEY']),'intake_configured':bool(s['INTAKE_TOKEN']),'gmail_drafts_verified':live,'model':s['GEMINI_MODEL']}
@app.get('/api/emails')
def emails():
    with db() as c:return [unpack(r) for r in c.execute('SELECT * FROM emails ORDER BY id DESC')]
@app.get('/api/emails/{id}/events')
def events(id:int):
    get(id)
    with db() as c:return [dict(r) for r in c.execute('SELECT action,created FROM events WHERE email_id=? ORDER BY id DESC',(id,))]
@app.post('/api/demo/seed')
def seed():
    for original,analysis in samples():
        r,duplicate=capture(EmailInput(**original),'Sample')
        if not duplicate:
            with db() as c:c.execute('UPDATE emails SET analysis=?,draft=?,status=? WHERE id=?',(json.dumps(analysis),analysis['suggested_reply'],'Draft ready' if analysis['action_required'] else 'No action',r['id']))
    return {'ok':True}
@app.post('/api/demo/analyze')
def demo_analyze(email:EmailInput):
    if not email.sender_email.endswith('@example.com'):raise HTTPException(400,'Demo requests must use an example.com sender.')
    email.message_id='manual-'+email.message_id
    r,_=capture(email,'Gemini demo');return run_analysis(r['id'])
@app.post('/api/emails/{id}/retry')
def retry(id:int):return run_analysis(id)
@app.post('/api/emails/{id}/review')
def review(id:int,value:Review):
    with db() as c:
        c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM emails WHERE id=?',(id,)).fetchone()
        if not row:raise HTTPException(404,'Email not found')
        if row['revision']!=value.revision:raise HTTPException(409,'This record changed. Reopen it before editing.')
        if not row['analysis']:raise HTTPException(409,'Wait for analysis before reviewing.')
        if value.action=='approve' and not value.draft.strip():raise HTTPException(400,'An empty draft cannot be approved.')
        status={'save':'Draft ready','approve':'Approved','complete':'Complete'}[value.action]
        c.execute('UPDATE emails SET draft=?,status=?,revision=revision+1 WHERE id=?',(value.draft,status,id));event(c,id,{'save':'Draft edited locally','approve':'Draft approved locally — not sent','complete':'Marked complete'}[value.action])
    return get(id)
@app.post('/api/intake/email')
def intake(email:EmailInput):
    if email.message_id.startswith(('demo-','manual-')):raise HTTPException(400,'Reserved message ID')
    r,duplicate=capture(email,'Gmail');r=run_analysis(r['id'])
    return {**r,'duplicate':duplicate}
@app.post('/api/intake/{id}/claim-draft')
def claim(id:int):
    with db() as c:
        c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM emails WHERE id=?',(id,)).fetchone()
        if not r:raise HTTPException(404,'Email not found')
        claimed=r['source']=='Gmail' and r['draft_state']=='ready' and bool(r['draft'])
        if claimed:
            c.execute('UPDATE emails SET draft_state="reserved" WHERE id=?',(id,));event(c,id,'Gmail draft creation reserved')
    return {'create_draft':claimed,'email':get(id)}
@app.post('/api/intake/{id}/draft-created')
def receipt(id:int,value:DraftReceipt):
    with db() as c:
        c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM emails WHERE id=?',(id,)).fetchone()
        if not r:raise HTTPException(404,'Email not found')
        if r['gmail_draft_id'] and r['gmail_draft_id']!=value.gmail_draft_id:raise HTTPException(409,'A different Gmail draft is already recorded.')
        if r['draft_state'] not in ('reserved','created'):raise HTTPException(409,'Draft was not reserved.')
        if not r['gmail_draft_id']:
            c.execute('UPDATE emails SET gmail_draft_id=?,draft_state=? WHERE id=?',(value.gmail_draft_id,'created',id));event(c,id,'Real Gmail draft created — not sent')
    return get(id)
@app.get('/api/export')
def export():
    buf=io.StringIO();w=csv.writer(buf);w.writerow(['Sender','Subject','Category','Priority','Summary','Status'])
    for r in emails():
        a=r['analysis'] or {};vals=[r['original']['sender'],r['original']['subject'],a.get('category',''),a.get('priority',''),a.get('summary',''),r['status']]
        w.writerow(["'"+v if v.lstrip().startswith(('=','+','-','@')) else v for v in vals])
    return Response(buf.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=mailpilot.csv'})
@app.get('/{path:path}')
def frontend(path:str):
    dist=ROOT/'frontend/dist';target=(dist/path).resolve()
    if not target.is_relative_to(dist.resolve()):raise HTTPException(404)
    if target.is_file():return FileResponse(target)
    if path.startswith('api/'):raise HTTPException(404)
    if (dist/'index.html').exists():return FileResponse(dist/'index.html')
    return JSONResponse({'detail':'Build the frontend first.'},status_code=503)
