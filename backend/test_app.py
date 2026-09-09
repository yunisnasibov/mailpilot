import pytest
from fastapi.testclient import TestClient
from . import main

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'DB',tmp_path/'test.sqlite3')
    monkeypatch.setenv('INTAKE_TOKEN','test-token')
    return TestClient(main.app)

def test_seed_and_review(client):
    for _ in range(2):assert client.post('/api/demo/seed').status_code==200
    rows=client.get('/api/emails').json()
    assert len(rows)==15
    row=next(r for r in rows if r['draft'])
    payload={'revision':row['revision'],'draft':'Reviewed reply','action':'approve'}
    result=client.post(f"/api/emails/{row['id']}/review",json=payload)
    assert result.json()['status']=='Approved'
    assert result.json()['gmail_draft_id']==''
    assert client.post(f"/api/emails/{row['id']}/review",json=payload).status_code==409

def test_boundaries(client):
    assert client.post('/api/intake/email',json={}).status_code==401
    assert client.post('/api/demo/seed',headers={'Origin':'https://evil.example'}).status_code==403
    assert client.get('/api/emails',headers={'Host':'evil.example'}).status_code==403

def test_intake_idempotency(client,monkeypatch):
    calls=[]
    def analyze(email):
        calls.append(email.message_id)
        return dict(category='Sales',priority='High',sentiment='Positive',summary='Customer requests a quote.',action_required=True,suggested_reply='Thanks for your inquiry.')
    monkeypatch.setattr(main.ai,'analyze',analyze)
    headers={'Authorization':'Bearer test-token'}
    payload=dict(message_id='gmail-123',sender='John',sender_email='john@example.com',subject='Quote',body='Please send a quote')
    first=client.post('/api/intake/email',headers=headers,json=payload).json()
    second=client.post('/api/intake/email',headers=headers,json=payload).json()
    assert second['duplicate'] and first['id']==second['id'] and len(calls)==1
    url=f"/api/intake/{first['id']}"
    assert client.post(url+'/claim-draft',headers=headers).json()['create_draft']
    assert not client.post(url+'/claim-draft',headers=headers).json()['create_draft']
    for _ in range(2):assert client.post(url+'/draft-created',headers=headers,json={'gmail_draft_id':'draft-123'}).status_code==200
    assert client.post(url+'/draft-created',headers=headers,json={'gmail_draft_id':'different'}).status_code==409

def test_failed_analysis_preserves_email(client,monkeypatch):
    def fail(email):raise main.ai.AIError('Temporary failure')
    monkeypatch.setattr(main.ai,'analyze',fail)
    payload=dict(message_id='failed-123',sender='John',sender_email='john@example.com',subject='Quote',body='Please send a quote')
    assert client.post('/api/demo/analyze',json=payload).status_code==502
    row=client.get('/api/emails').json()[0]
    assert row['original']['body']==payload['body'] and row['status']=='Retry needed'
    assert row['gmail_draft_id']==''
