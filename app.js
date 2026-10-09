'use strict';
const ids = ['ka','kd','rmax','concentration','association','dissociation','top','dilution','count'];
const form = document.getElementById('parameters');
const colors = ['#167c80','#4479be','#c98e38','#8766b1','#d06c69','#569443','#a76898','#4a94b5','#ae813f','#626bb6','#bb516d','#608c84'];
const el = id => document.getElementById(id);
const fmt = n => n === 0 ? '0' : (Math.abs(n) < .001 || Math.abs(n) >= 1e5) ? n.toExponential(2) : Number(n.toPrecision(4)).toString();
let current;
function parameters() {
  const p = {mode:el('mode').value, series:el('series').checked};
  ids.forEach(id => { p[id] = el(id).value.trim() === '' ? NaN : Number(el(id).value); });
  return p;
}
function chart(result, p) {
  const w=900,h=430,left=70,right=24,top=28,bottom=60;
  const x=t=>left+t/result.duration*(w-left-right);
  const y=r=>h-bottom-r/(p.rmax*1.1)*(h-top-bottom);
  const path=points=>points.map((a,i)=>`${i?'L':'M'}${x(a.t).toFixed(3)},${y(a.r).toFixed(3)}`).join(' ');
  let svg=`<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg"><title>SPR sensorgram</title><desc>${p.mode === 'lsa' ? '无再生连续进样' : '独立多周期'}，横轴时间（秒），纵轴响应（RU）</desc>`;
  if(p.mode==='multi') svg+=`<rect x="${x(0)}" y="${top}" width="${x(p.association)-x(0)}" height="${h-top-bottom}" fill="#edf7f6"/>`;
  for(let i=0;i<=5;i++) {
    const r=p.rmax*1.1*i/5,t=result.duration*i/5;
    svg+=`<path d="M${left} ${y(r)}H${w-right}" stroke="#e6edf2"/><text x="${left-12}" y="${y(r)+4}" text-anchor="end" font-size="12" fill="#728397">${fmt(r)}</text><text x="${x(t)}" y="${h-bottom+24}" text-anchor="middle" font-size="12" fill="#728397">${fmt(t)}</text>`;
  }
  result.cycles.forEach((c,i)=>{
    svg+=`<path d="M${x(c.offset+p.association)} ${top}V${h-bottom}" stroke="#adc2cd" stroke-dasharray="4 5"/><path d="${path(c.points)}" fill="none" stroke="${colors[i]}" stroke-width="2.5" stroke-linejoin="round"/>`;
  });
  if(p.series) svg+=`<path d="${path(result.reference.points)}" fill="none" stroke="#83919d" stroke-width="1.8" stroke-dasharray="6 4"/>`;
  svg+=`<path d="M${left} ${top}V${h-bottom}H${w-right}" fill="none" stroke="#aab9c7"/><text x="${w/2}" y="${h-10}" text-anchor="middle" font-size="13" fill="#51677c">时间 (s)</text><text transform="translate(18 ${h/2}) rotate(-90)" text-anchor="middle" font-size="13" fill="#51677c">响应 (RU)</text></svg>`;
  el('plot').innerHTML=svg;
  el('legend').innerHTML=result.cycles.map((c,i)=>`<span><i style="background:${colors[i]}"></i>${fmt(c.concentration)} nM</span>`).join('')+(p.series?`<span><i style="background:#83919d"></i>参考 ${fmt(p.concentration)} nM</span>`:'');
}
function update() {
  try {
    const p=parameters(),result=SPR.simulate(p);
    current={p,result}; el('error').textContent=''; el('export').disabled=false;
    el('kd-value').textContent=`${fmt(result.kd*1e9)} nM`;
    el('half-value').textContent=p.kd===0?'∞':`${fmt(Math.LN2/p.kd)} s`;
    el('range-value').textContent=p.series?`${fmt(result.cycles[0].concentration)}–${fmt(p.top)} nM`:`${fmt(p.concentration)} nM`;
    el('cycle-value').textContent=`${result.cycles.length} 个周期 · ${p.mode==='lsa'?'无再生':'每轮归零'}`;
    el('mode-description').textContent=p.mode==='lsa'?'连续时间轴 · 残余响应延续到下一浓度':'对齐时间轴 · 各浓度独立结合与解离';
    chart(result,p);
    el('schedule').innerHTML=result.cycles.map((c,i)=>`<tr><td>${String(i+1).padStart(2,'0')}</td><td>${fmt(c.concentration)}</td><td>${fmt(c.initial)}</td><td>${fmt(c.bound)}</td><td>${fmt(c.end)}</td></tr>`).join('');
  } catch(e) {
    current=null; el('error').textContent=e.message; el('export').disabled=true;
    ['kd-value','half-value','range-value','cycle-value'].forEach(id=>el(id).textContent='—');
    el('plot').innerHTML=''; el('legend').innerHTML=''; el('schedule').innerHTML='';
    el('mode-description').textContent='请修正参数后查看曲线。';
  }
}
form.addEventListener('submit',event=>event.preventDefault());
form.addEventListener('input',update);
el('reset').addEventListener('click',()=>{HTMLFormElement.prototype.reset.call(form);update();});
el('export').addEventListener('click',()=>{
  if(!current)return;
  const rows=['cycle,concentration_nM,time_s,response_RU,phase'];
  current.result.cycles.forEach((c,i)=>c.points.forEach(a=>rows.push(`${i+1},${c.concentration},${a.t},${a.r},${a.phase}`)));
  const url=URL.createObjectURL(new Blob([rows.join('\r\n')],{type:'text/csv;charset=utf-8'}));
  const link=document.createElement('a'); link.href=url;link.download=`spr-${current.p.mode}.csv`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
update();
