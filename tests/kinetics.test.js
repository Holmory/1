const {test} = require('node:test');
const assert = require('node:assert/strict');
const {simulate,associate,dissociate} = require('../kinetics.js');
const p={ka:1e5,kd:.001,rmax:100,concentration:10,association:120,dissociation:180,top:100,dilution:3,count:5,series:true,mode:'multi'};
const close=(a,b)=>assert.ok(Math.abs(a-b)<1e-10,`${a} != ${b}`);
test('KD and analytical association/dissociation use nM → M',()=>{
  close(simulate(p).kd,1e-8);
  close(associate(120,0,10,p),50*(1-Math.exp(-.002*120)));
  close(dissociate(180,50,p.kd),50*Math.exp(-.18));
});
test('multi-cycle resets, uses ascending dilution series and joins phases continuously',()=>{
  const s=simulate(p);assert.equal(s.cycles.length,5);close(s.cycles[0].concentration,100/81);
  s.cycles.forEach(c=>{assert.equal(c.initial,0);assert.equal(c.offset,0);close(c.points[240].r,c.bound);close(c.points.at(-1).r,c.end);assert.ok(c.points.every(a=>a.r>=0&&a.r<=p.rmax));});
  assert.equal(s.duration,300);
});
test('LSA preserves residual binding and sequential timeline',()=>{
  const s=simulate({...p,mode:'lsa'});assert.equal(s.duration,1500);
  for(let i=1;i<s.cycles.length;i++){close(s.cycles[i].initial,s.cycles[i-1].end);close(s.cycles[i].points[0].t,s.cycles[i-1].points.at(-1).t);close(s.cycles[i].points[0].r,s.cycles[i-1].points.at(-1).r);}
});
test('single concentration and zero-concentration control',()=>{
  const s=simulate({...p,series:false,concentration:0});assert.equal(s.cycles.length,1);assert.ok(s.cycles[0].points.every(a=>a.r===0));
  close(associate(120,70,0,p),70*Math.exp(-.12));
});
test('zero kd retains bound response, saturates at Rmax',()=>{
  const s=simulate({...p,kd:0,association:1e6});assert.equal(s.kd,0);close(s.cycles[0].bound,100);close(s.cycles[0].end,100);
});
test('invalid, blank-equivalent and overflowing parameters rejected',()=>{
  for(const patch of [{ka:0},{kd:-1},{rmax:0},{concentration:-1},{association:0},{dissociation:NaN},{dilution:1},{count:1.5},{count:13},{top:Infinity},{mode:'unknown'},{ka:1e308,top:1e308},{association:1e8}])assert.throws(()=>simulate({...p,...patch}));
});
