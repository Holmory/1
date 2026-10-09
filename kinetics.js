(function (root) {
  'use strict';
  function validate(p) {
    for (const key of ['ka', 'kd', 'rmax', 'concentration', 'association', 'dissociation', 'top', 'dilution', 'count']) {
      if (!Number.isFinite(p[key])) throw new Error('所有参数必须为有限数值。');
    }
    if (p.ka <= 0 || p.kd < 0 || p.rmax <= 0) throw new Error('ka 和 Rmax 必须大于 0；kd 不得小于 0。');
    if (p.concentration < 0 || p.top < 0) throw new Error('浓度不得小于 0。');
    if (p.association <= 0 || p.dissociation <= 0) throw new Error('结合时间和解离时间必须大于 0。');
    if (!Number.isFinite(p.association + p.dissociation) || (p.association + p.dissociation) > 1e7) throw new Error('单周期总时间不得超过 10⁷ 秒。');
    if (p.dilution <= 1) throw new Error('稀释倍数必须大于 1。');
    if (!Number.isInteger(p.count) || p.count < 1 || p.count > 12) throw new Error('浓度数量必须为 1–12 的整数。');
    if (!['multi', 'lsa'].includes(p.mode)) throw new Error('未知实验模式。');
    const highest = Math.max(p.top, p.concentration) * 1e-9;
    if (!Number.isFinite(p.ka * highest + p.kd) || !Number.isFinite(p.kd / p.ka)) throw new Error('参数超出计算范围，请降低数值。');
  }
  function associate(t, initial, concentrationNM, p) {
    const on = p.ka * (concentrationNM * 1e-9);
    const rate = on + p.kd;
    if (rate === 0) return initial;
    const eq = p.rmax * (on / rate);
    return initial + (eq - initial) * (-Math.expm1(-rate * t));
  }
  function dissociate(t, initial, kd) { return initial * Math.exp(-kd * t); }
  function cycle(concentration, initial, offset, p) {
    const points = [];
    const bound = associate(p.association, initial, concentration, p);
    for (let i = 0; i <= 240; i++) {
      const t = p.association * i / 240;
      points.push({t: offset + t, r: associate(t, initial, concentration, p), phase: 'association'});
    }
    for (let i = 1; i <= 240; i++) {
      const t = p.dissociation * i / 240;
      points.push({t: offset + p.association + t, r: dissociate(t, bound, p.kd), phase: 'dissociation'});
    }
    return {concentration, initial, bound, end: dissociate(p.dissociation, bound, p.kd), offset, points};
  }
  function simulate(p) {
    validate(p);
    const concentrations = p.series ? Array.from({length:p.count}, (_, i) => p.top / Math.pow(p.dilution, p.count - 1 - i)) : [p.concentration];
    let initial = 0;
    const duration = p.association + p.dissociation;
    const cycles = concentrations.map((c, i) => {
      const result = cycle(c, p.mode === 'lsa' ? initial : 0, p.mode === 'lsa' ? i * duration : 0, p);
      initial = result.end;
      return result;
    });
    return {cycles, reference:cycle(p.concentration, 0, 0, p), duration:duration * (p.mode === 'lsa' ? cycles.length : 1), kd:p.kd / p.ka};
  }
  const api = {validate, associate, dissociate, simulate};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.SPR = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
