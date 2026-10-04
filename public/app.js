'use strict';
const cityNames = {kashiwa:'柏市',nagareyama:'流山市',abiko:'我孫子市'};
const form = document.querySelector('#search-form');
const results = document.querySelector('#results');
const summary = document.querySelector('#summary');
const button = document.querySelector('#search-button');
const message = document.querySelector('#message');
const statuses = document.querySelector('#source-status');
const dateInput = document.querySelector('#date');
const today = new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
dateInput.min = today;
dateInput.value = today;
let states = {};
let query = null;
let complete = false;
const el = (tag, className, text) => {const node=document.createElement(tag); if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;};

function renderStatus(){
  statuses.replaceChildren();
  for(const [id,state] of Object.entries(states)){
    const container=el('div');
    const labels={loading:'照会中',ok:'確認済み',partial:'一部確認できません',error:'確認できません'};
    container.append(el('div',`source-chip ${state.status}`,`${cityNames[id]} · ${labels[state.status]}${state.courtCount!==undefined ? `（${state.courtCount}面）` : ''}`));
    if(state.errors?.length){
      const detail=el('details','source-detail');detail.append(el('summary','',`確認できなかった内容（${state.errors.length}件）`));
      const list=el('ul');state.errors.forEach(e=>list.append(el('li','',e)));detail.append(list);container.append(detail);
    }
    statuses.append(container);
  }
}

function segmentNode(segment){
  const row=el('div','segment');
  row.append(el('span','use-time',`${segment.useStart}–${segment.useEnd}`),el('span','court-name',segment.court));
  const booking=el('span','booking','必要な予約：');
  booking.append(el('strong','',segment.bookingUnits.map(u=>`${u.start}–${u.end}`).join(' ／ ')));
  row.append(booking);return row;
}

function renderPlans(plans){
  results.replaceChildren();
  const checked=Object.values(states).filter(s=>s.status!=='loading').length;
  const total=Object.keys(states).length;
  summary.textContent=`${query.date} ${query.start}–${query.end} · ${plans.length}施設${complete?'':` · ${checked}/${total}市を確認`}`;
  if(!plans.length){
    const empty=el('div','empty');
    const allFailed=Object.values(states).every(s=>s.status==='error');
    empty.append(el('h3','',complete?(allFailed?'空き状況を確認できませんでした':'希望時間を満たす候補がありません'):'各市の空き状況を確認しています'));
    empty.append(el('p','',complete?'日時を変更するか、公式サイトでご確認ください。確認できなかった施設は「空きなし」とは判定していません。':'確認が終わった市から結果を表示します。'));
    results.append(empty);return;
  }
  for(const plan of plans){
    const card=el('article','result-card');
    const head=el('div','card-head');const label=el('div','facility-label');
    label.append(el('span','city-name',cityNames[plan.city]),el('h3','facility-name',plan.facility));
    head.append(label,el('span',`badge${plan.changes?' switch':''}`,plan.changes?`コート移動 ${plan.changes}回`:'同じコートで連続'));
    const body=el('div','plan-content');plan.segments.forEach(s=>body.append(segmentNode(s)));
    if(plan.extraMinutes)body.append(el('div','extra',`予約枠に合わせて、希望時間より合計${plan.extraMinutes}分長い予約が必要です。`));
    if(plan.alternatives.length){
      const detail=el('details','alternatives');detail.append(el('summary','',`ほかに連続利用できるコート ${plan.alternatives.length}面`));
      for(const alternative of plan.alternatives){const item=el('div','alternative');alternative.segments.forEach(s=>item.append(segmentNode(s)));detail.append(item);}body.append(detail);
    }
    const foot=el('div','card-footer');
    if(plan.notes.length)foot.append(el('p','',plan.notes.join(' ')));
    const link=el('a','','公式サイトで確認');link.href=plan.sourceUrl;link.target='_blank';link.rel='noopener noreferrer';foot.append(link);
    card.append(head,body,foot);results.append(card);
  }
}

form.addEventListener('submit',async event=>{
  event.preventDefault();
  if(!form.reportValidity())return;
  query={date:dateInput.value,start:form.elements.start.value,end:form.elements.end.value,cities:[...form.querySelectorAll('input[name=cities]:checked')].map(i=>i.value)};
  message.hidden=true;
  if(!query.cities.length || query.start>=query.end){message.textContent='検索する市を選び、終了時刻を開始時刻より後にしてください。';message.hidden=false;return;}
  states=Object.fromEntries(query.cities.map(id=>[id,{status:'loading'}]));complete=false;
  let latestPlans=[];
  renderStatus();renderPlans(latestPlans);document.querySelector('#checked-at').textContent='';
  button.disabled=true;button.textContent='空き状況を確認中…';
  form.querySelectorAll('input').forEach(input=>input.disabled=true);
  try{
    const response=await fetch('/api/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(query)});
    if(!response.ok){const body=await response.json();throw new Error(body.error || '検索できませんでした。');}
    const reader=response.body.getReader();const decoder=new TextDecoder('utf-8');let buffer='';let doneEvent=false;
    while(true){
      const {value,done}=await reader.read();buffer+=decoder.decode(value,{stream:!done});
      let boundary;
      while((boundary=buffer.indexOf('\n\n'))!==-1){
        const part=buffer.slice(0,boundary);buffer=buffer.slice(boundary+2);
        const type=part.split('\n').find(line=>line.startsWith('event: '))?.slice(7);
        const data=part.split('\n').filter(line=>line.startsWith('data: ')).map(line=>line.slice(6)).join('\n');
        if(!data)continue;
        const payload=JSON.parse(data);
        if(type==='city'){states[payload.source.id]={...payload.source,courtCount:payload.courtCount};latestPlans=payload.plans;renderStatus();renderPlans(latestPlans);}
        if(type==='done'){complete=true;doneEvent=true;latestPlans=payload.plans;renderPlans(latestPlans);document.querySelector('#checked-at').textContent=`最終確認 ${new Date(payload.checkedAt).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo'})}`;}
      }
      if(done)break;
    }
    if(!doneEvent)throw new Error('通信が途中で終了しました。確認済みの結果だけを表示しています。再検索してください。');
  }catch(error){
    for(const state of Object.values(states))if(state.status==='loading'){state.status='error';state.errors=['照会が完了しませんでした'];}
    complete=true;renderStatus();renderPlans(latestPlans);
    message.textContent=error.message || '通信できませんでした。再度お試しください。';message.hidden=false;
  }finally{
    button.disabled=false;button.textContent='空き状況を検索';form.querySelectorAll('input').forEach(input=>input.disabled=false);
  }
});
