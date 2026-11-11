import {chart} from './charts.js';
const $=id=>document.getElementById(id);
let csrf='',activeRun=null,conversationId=null,identityId=null;
function node(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
async function api(path,body,method){const r=await fetch(path,{method:method||(body===undefined?'GET':'POST'),headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:body===undefined?undefined:JSON.stringify(body)});const v=await r.json();if(!r.ok)throw Error(v.error||v.code||`HTTP ${r.status}`);return v;}
const scenarios=['Underlying concentration','Executive intelligence pack','Indicative pricing draft','Coupon comparison','Client intelligence','Maturities and rollovers','Branch concentration','Regional performance','Digital journey'];
scenarios.forEach((s,i)=>{const b=node('button',`Q${i+1} · ${s}`);b.onclick=()=>{$('question').value=`Q${i+1}: ${s}`;$('question').focus();};$('scenarios').append(b);});
function details(title,value){const d=node('details');d.append(node('summary',title),node('pre',JSON.stringify(value,null,2)));return d;}
function table(rows){const wrap=node('div',undefined,'tablewrap');if(!rows.length){wrap.append(node('p','No results met the defined scope.'));return wrap;}const t=node('table'),head=node('tr'),keys=[...new Set(rows.flatMap(r=>Object.keys(r)))];keys.forEach(k=>head.append(node('th',k)));t.append(head);rows.forEach(r=>{const tr=node('tr');keys.forEach(k=>tr.append(node('td',r[k]===null?'Unknown':typeof r[k]==='object'?JSON.stringify(r[k]):String(r[k]??''))));t.append(tr);});wrap.append(t);return wrap;}
function drawBar(rows){if(!rows.length||rows.length>40)return null;const keys=Object.keys(rows[0]),metric=keys.find(k=>['notional','sales','events','value'].includes(k)),dim=keys.find(k=>!['currency',metric].includes(k));if(!metric||!dim)return null;const values=rows.map(r=>Number(r[metric]));if(values.some(v=>!Number.isFinite(v)||v<0))return null;const max=Math.max(...values);if(!max)return null;const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox',`0 0 700 ${rows.length*32+35}`);svg.setAttribute('role','img');svg.setAttribute('aria-label',`${metric} by ${dim}`);rows.forEach((r,i)=>{const text=document.createElementNS(ns,'text');text.setAttribute('x','0');text.setAttribute('y',String(i*32+20));text.textContent=String(r[dim]);svg.append(text);const rect=document.createElementNS(ns,'rect');rect.setAttribute('x','160');rect.setAttribute('y',String(i*32+5));rect.setAttribute('height','22');rect.setAttribute('width',String(values[i]/max*440));rect.setAttribute('fill','#348771');const title=document.createElementNS(ns,'title');title.textContent=`${r[dim]}: ${r[metric]}`;rect.append(title);svg.append(rect);});return svg;}
async function embed(parent,v){
  const panel=node('div');panel.append(node('h3',v.title),node('p',v.scope_note,'note'));parent.append(panel);
  try{
    // Endpoint re-discovers and reauthorizes this exact view; JWT never enters saved task state.
    const auth=await api('/api/v1/tableau/embed',{dashboard:v.dashboard_key,view_id:v.view_id,filters:v.filters,parameters:v.parameters,highlights:v.highlights});
    const url=new URL(auth.visual.url);if(url.protocol!=='https:')throw Error('Invalid Tableau origin.');
    const sdk=await import(`${url.origin}/javascripts/api/tableau.embedding.3.latest.min.js`);
    const viz=new sdk.TableauViz();viz.src=auth.visual.url;viz.token=auth.token;viz.hideTabs=true;viz.toolbar='bottom';viz.style.width='100%';viz.style.height='620px';
    for(const [field,values] of Object.entries(v.filters||{}))viz.addFilter(field,values.join(','));
    viz.addEventListener(sdk.TableauEventType.FirstInteractive,async()=>{try{
      for(const [field,value] of Object.entries(v.parameters||{}))await viz.workbook.changeParameterValueAsync(field,value);
      const sheet=viz.workbook.activeSheet;
      if(Object.keys(v.highlights||{}).length && sheet.worksheets)throw Error('Highlight needs a separately published worksheet; dashboard membership is not inferred.');
      for(const [field,values] of Object.entries(v.highlights||{}))await sheet.selectMarksByValueAsync(field,values,sdk.SelectionUpdateType.Replace);
    }catch(e){panel.append(node('p',e.message,'error'));}});
    viz.addEventListener(sdk.TableauEventType.VizLoadError,()=>panel.append(node('p','Tableau could not load. Check browser identity, Connected App permissions and allowed domains.','error')));
    panel.append(viz);
  }catch(e){panel.append(node('p',`Original view unavailable: ${e.message}`,'error'));}
}
function render(answer,box){
  box.replaceChildren(node('span',answer.status,'pill'),node('span',(answer.source_modes||[]).join(' + ')||'No numerical evidence','pill'));
  if(answer.message)box.append(node('p',answer.message));
  if(answer.clarification?.type==='document_format'){
    const choices=node('div',undefined,'composer');
    for(const format of answer.clarification.options){const button=node('button',format.toUpperCase());button.type='button';button.onclick=()=>{
      document.querySelectorAll('[name=format]').forEach(n=>n.checked=false);$('question').value=format.toUpperCase();$('chat').requestSubmit();};choices.append(button);}
    box.append(choices);
  }
  for(const key of ['summary','insights','recommended_actions']){const claims=answer.narrative?.[key]||[];if(claims.length)box.append(node('h3',key.replaceAll('_',' ')));for(const c of claims){box.append(node('p',c.text),details('Supporting evidence',answer.evidence.filter(e=>c.evidence_ids.includes(e.id))));}}
  const visuals=node('div',undefined,`visuals ${answer.plan.output.layout}`);box.append(visuals);for(const v of answer.visualizations||[])if(v.type==='tableau')embed(visuals,v);
  for(const [id,out] of Object.entries(answer.analysis?.results||{})){box.append(node('h3',out.operation||id));if(out.rows){const display=out.chart?chart(out):drawBar(out.rows);if(display)box.append(display);box.append(table(out.rows));}else box.append(details('Result',out));}
  for(const w of new Set(answer.warnings||[]))box.append(node('p',w,'warning'));
  const links=node('div',undefined,'downloads');for(const a of answer.artifacts||[]){const url=new URL(a.url,location.origin);if(url.origin===location.origin){const link=node('a',`Download draft ${a.format.toUpperCase()}`);link.href=url.href;links.append(link);}}box.append(links);
  box.append(details('Request requirement coverage',answer.requirement_coverage||{}),details('Evidence and provenance',answer.evidence),details('Business terminology references',answer.knowledge_references||[]),details('Execution plan',answer.plan),details('Run measurements',answer.metrics));
}

function busy(value){$('send').disabled=value;$('cancel').hidden=!value;$('conversation').disabled=value;$('new-chat').disabled=value;$('delete-chat').disabled=value;$('logout').disabled=value;}
async function pollRun(key,box){
  activeRun=key;busy(true);
  try{
    let state;
    do{await new Promise(resolve=>setTimeout(resolve,500));state=await api(`/api/v1/runs/${key}`);box.replaceChildren(node('p',`Run ${state.status}`,'status'),details('Task progress',state.trace));}while(['pending','running'].includes(state.status));
    if(state.answer)render(state.answer,box);else box.replaceChildren(node('p',state.error?.message||`Run ${state.status}`,'error'));
  }catch(error){box.replaceChildren(node('p',error.message,'error'));}
  finally{activeRun=null;busy(false);}
}
async function loadHistory(){
  $('messages').replaceChildren();
  if(!conversationId)return;
  const history=await api(`/api/v1/conversations/${conversationId}`);
  let pending=null;
  for(const turn of history.turns){
    $('messages').append(node('div',turn.question,'message user'));
    const box=node('div',undefined,'message');$('messages').append(box);
    if(turn.answer)render(turn.answer,box);
    else{box.append(node('p',`Request ${turn.status}`,'status'));if(turn.status==='pending'&&turn.run_id)pending={key:turn.run_id,box};}
  }
  if(pending)await pollRun(pending.key,pending.box);
}
async function savedChats(preferred){
  const list=await api('/api/v1/conversations');
  if(!list.conversations.length){const created=await api('/api/v1/conversations',{});return savedChats(created.conversation_id);}
  const saved=preferred||localStorage.getItem(`hkeli-chat:${identityId}`);
  conversationId=list.conversations.some(c=>c.id===saved)?saved:list.conversations[0].id;
  $('conversation').replaceChildren();
  for(const chat of list.conversations){const option=node('option',`Chat ${chat.id.slice(0,8)}`);option.value=chat.id;$('conversation').append(option);}
  $('conversation').value=conversationId;localStorage.setItem(`hkeli-chat:${identityId}`,conversationId);$('chats').hidden=false;
  await loadHistory();
}
$('conversation').onchange=async()=>{if(activeRun)return;conversationId=$('conversation').value;localStorage.setItem(`hkeli-chat:${identityId}`,conversationId);try{await loadHistory();}catch(error){$('messages').append(node('p',error.message,'error'));}};
$('new-chat').onclick=async()=>{if(activeRun)return;try{const created=await api('/api/v1/conversations',{});await savedChats(created.conversation_id);}catch(error){alert(error.message);}};
$('delete-chat').onclick=async()=>{if(activeRun||!conversationId||!confirm('Delete this saved chat and its history?'))return;try{await api(`/api/v1/conversations/${conversationId}`,undefined,'DELETE');localStorage.removeItem(`hkeli-chat:${identityId}`);conversationId=null;await savedChats();}catch(error){alert(error.message);}};
$('logout').onclick=async()=>{if(activeRun)return;await api('/api/logout',{});conversationId=null;identityId=null;$('messages').replaceChildren();$('dashboards').replaceChildren();$('identity').textContent='';$('chats').hidden=true;const state=await api('/api/session');csrf=state.csrf;};
$('login').onsubmit=async event=>{event.preventDefault();if(activeRun)return;$('messages').replaceChildren();try{const result=await api('/api/login',{user_id:$('profile').value});csrf=result.csrf;await loadDashboards();}catch(error){alert(error.message);}};
async function loadDashboards(){
  const data=await api('/api/dashboards');identityId=data.user.id;$('identity').textContent=`${data.user.id} - ${data.user.country}`;
  $('dashboards').replaceChildren(node('h3','Authorized dashboards'));
  for(const value of data.dashboards){const label=node('label'),input=node('input');input.type='checkbox';input.value=value.key;input.name='dashboard';label.append(input,document.createTextNode(value.label));$('dashboards').append(label);}
  await savedChats();
}
$('cancel').onclick=()=>activeRun&&api(`/api/v1/runs/${activeRun}/cancel`,{}).catch(error=>alert(error.message));
$('chat').onsubmit=async event=>{
  event.preventDefault();if(activeRun)return;const question=$('question').value.trim();if(!question)return;
  $('messages').append(node('div',question,'message user'));const box=node('div','Planning...','message');$('messages').append(box);busy(true);
  try{
    const queued=await api('/api/v1/requests',{question,conversation_id:conversationId,
      dashboards:[...document.querySelectorAll('[name=dashboard]:checked')].map(n=>n.value),
      formats:[...document.querySelectorAll('[name=format]:checked')].map(n=>n.value)});
    conversationId=queued.conversation_id;if(identityId)localStorage.setItem(`hkeli-chat:${identityId}`,conversationId);
    $('question').value='';document.querySelectorAll('[name=format]').forEach(n=>n.checked=false);
    await pollRun(queued.run_id,box);
  }catch(error){box.replaceChildren(node('p',error.message,'error'));busy(false);}
};
try{const state=await api('/api/session');csrf=state.csrf;$('mode').textContent=state.mode==='fixture'?'SYNTHETIC FIXTURES':'LIVE INTEGRATIONS';state.profiles.forEach(p=>{const option=node('option',`${p.id} (${p.country})`);option.value=p.id;$('profile').append(option);});$('login').hidden=!state.local_test;try{await loadDashboards();}catch{}}catch(error){$('messages').append(node('p',error.message,'error'));}
