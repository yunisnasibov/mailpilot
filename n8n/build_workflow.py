"""Generate a credential-free n8n workflow for import."""
import json
from pathlib import Path

nodes=[]
def node(name,type,version,parameters,x):
    nodes.append(dict(id=name.replace(' ','-'),name=name,type='n8n-nodes-base.'+type,typeVersion=version,position=[x,300],parameters=parameters))
node('Test Gmail inbox','gmailTrigger',1.4,dict(pollTimes={'item':[{'mode':'everyMinute'}]},simple=False,maxResults=5,filters={'q':'in:inbox subject:MailPilot-Test -in:drafts','readStatus':'both'},options={'downloadAttachments':False}),0)
node('Normalize email','code',2,{'mode':'runOnceForEachItem','jsCode':"const m=$json; const f=m.from?.value?.[0]; if(!f?.address) throw new Error('Missing sender address'); return {json:{message_id:m.id,thread_id:m.threadId||'',sender:f.name||f.address,sender_email:f.address,subject:m.subject||'(No subject)',body:(m.text||m.html||'').slice(0,24000),received_at:m.date||''}};"},230)
def http(name,url,body,x):
    node(name,'httpRequest',4.2,dict(method='POST',url=url,authentication='genericCredentialType',genericAuthType='httpHeaderAuth',sendBody=True,specifyBody='json',jsonBody=body,options={'timeout':60000}),x)
http('Analyze and save','http://127.0.0.1:4175/api/intake/email','={{ JSON.stringify($json) }}',460)
http('Reserve draft','=http://127.0.0.1:4175/api/intake/{{ $json.id }}/claim-draft','={}',690)
node('Needs Gmail draft','if',2.2,{'conditions':{'options':{'caseSensitive':True,'leftValue':'','typeValidation':'strict','version':2},'conditions':[{'id':'draft-check','leftValue':'={{ $json.create_draft }}','rightValue':True,'operator':{'type':'boolean','operation':'true','singleValue':True}}],'combinator':'and'},'options':{}},920)
node('Create Gmail draft','gmail',2.2,dict(resource='draft',operation='create',subject='={{ "Re: " + $json.email.original.subject }}',emailType='text',message='={{ $json.email.draft }}',options={'sendTo':'={{ $json.email.original.sender_email }}','threadId':'={{ $json.email.original.thread_id }}'}),1150)
http('Record Gmail draft','=http://127.0.0.1:4175/api/intake/{{ $("Reserve draft").item.json.email.id }}/draft-created','={{ JSON.stringify({gmail_draft_id:$json.id}) }}',1380)
connections={}
for left,right in zip(nodes,nodes[1:]):connections[left['name']]={'main':[[{'node':right['name'],'type':'main','index':0}]]}
workflow=dict(id='mailpilotGmailV1',name='MailPilot — Gmail triage and human-reviewed drafts',nodes=nodes,connections=connections,active=False,settings={'executionOrder':'v1'},pinData={})
Path(__file__).with_name('mailpilot-gmail.json').write_text(json.dumps(workflow,indent=2),encoding='utf-8')
