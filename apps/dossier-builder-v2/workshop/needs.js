// «Needs you» (Part 2, step 2.7): one list of everything only a person can settle, each with its problem, its rule and the source
// that says it, what the program or Claude suggests, and the actions that fit it — open it in its program, let Claude fix it (the
// company's own papers only), upload a new version, accept it with a reason (kept in the dossier's log). The rest the program does.
const ACTIONS = {
  program: 'افتحه في البرنامج', claude: 'خلّي Claude يصلّحه', upload: 'ارفع نسخة جديدة', accept: 'اقبله كده (بسبب)',
  place: 'اختار مكانه', cut: 'اتأكد من التقطيع', create: 'اعمل المسودة', fill: 'كمّل بيانات الشركة', pdf: 'اعمله PDF',
  design: 'اعمله في برنامج التصميم', text: 'اعمله طبقة نص',
};
export const actionName = a => ACTIONS[a] || a;
// A count in Arabic as it is said: one, two, three to ten (plural), eleven and more (singular).
export const count = (n, one, two, few, many = one) => (n === 1 ? one : n === 2 ? two : n <= 10 ? `${n} ${few}` : `${n} ${many}`);

export function needsOf(d, board, findings, { drafts = {} } = {}) {
  const out = [];
  const placeOf = id => board.places.find(p => p.id === id);
  const docs = d.docs.filter(x => !x.dup && !x.split);
  // 1. documents the program could not place, or placed without being sure
  for (const doc of docs) {
    if (doc.unread || doc.placeBy === 'you' || d.decisions?.[`place-${doc.id}`]) continue;
    if (!doc.place || !doc.sure) {
      const maybe = [doc.place, ...(doc.maybe || [])].filter(Boolean).filter((x, i, a) => a.indexOf(x) === i).map(placeOf).filter(Boolean);
      out.push({ id: `place-${doc.id}`, kind: 'place', level: doc.place ? 'amber' : 'red', doc: doc.id,
                 title: doc.place ? `اتأكد من مكان «${doc.name}»` : `«${doc.name}»: البرنامج مش عارف مكانه`,
                 detail: doc.place ? `${doc.placeBy === 'claude' ? 'Claude' : 'القواعد'} ${doc.placeBy === 'claude' ? 'حطّه' : 'حطّته'} في ${placeOf(doc.place)?.ctd} ${placeOf(doc.place)?.title.ar}، من غير ما ${doc.placeBy === 'claude' ? 'يكون متأكد' : 'تكون متأكدة'}.${doc.claudeWhy ? ` (${doc.claudeWhy})` : ''}`
                                   : 'مالقاش في أول صفحاته كلام يعرّف نوعه. اختار المكان من القايمة، أو خلّي Claude يقراه.',
                 suggestion: maybe.map(p => ({ id: p.id, ctd: p.ctd, ar: p.title.ar })), actions: ['place', 'accept'], rule: null });
    }
  }
  // 2. cuts the program is not sure of
  for (const doc of d.docs.filter(x => x.split && x.cut && !x.cut.sure && !d.decisions?.[`cut-${x.id}`])) {
    out.push({ id: `cut-${doc.id}`, kind: 'cut', level: 'amber', doc: doc.id, title: `اتأكد من تقطيع «${doc.name}»`,
               detail: `البرنامج قطّعه ${doc.cut.segments.length} مستندات: ${doc.cut.segments.map(([a, b]) => (a === b ? `ص ${a}` : `ص ${a}–${b}`)).join('، ')}. فيه قطعة مش متأكد منها.`,
               actions: ['cut', 'accept'], rule: null });
  }
  // 3. the findings a person must act on (what the program fixes by itself is not here, unless its fix failed)
  const missing = [];
  for (const f of findings) {
    if (f.accepted) continue;
    if (f.kind === 'missing') {
      if (f.fix?.auto === 'create' && !d.decisions?.[f.id]) { if (!drafts[f.place]) out.push({ ...need(f), actions: ['create', 'upload', 'accept'] }); continue; }
      missing.push(f);
      continue;
    }
    if (f.fix?.auto && !f.fixFailed) continue;
    out.push({ ...need(f), actions: f.fix?.human || ['upload', 'accept'] });
  }
  if (missing.length) {
    out.push({ id: 'missing', kind: 'missing', level: 'red', title: count(missing.length, 'مكان مطلوب فاضي', 'مكانين مطلوبين فاضيين', 'أماكن مطلوبة فاضية', 'مكان مطلوب فاضي'),
               detail: 'المستندات دي مطلوبة للمنتج ده ومش في الملف. ارفع كل واحد في مكانه، أو اكتب سبب إنه مش مطلوب.',
               places: missing.map(f => ({ id: f.place, ctd: placeOf(f.place)?.ctd, ar: placeOf(f.place)?.title.ar, finding: f.id })),
               actions: ['upload', 'accept'], rule: missing[0].rule });
  }
  // 4. the drafts the program wrote: their gaps, and the signature they still need
  for (const [place, draft] of Object.entries(drafts)) {
    const doc = d.docs.find(x => x.id === draft.doc);
    if (!doc || d.decisions?.[`draft-${doc.id}`]) continue;
    out.push({ id: `draft-${doc.id}`, kind: 'draft', level: draft.gaps.length ? 'amber' : 'amber', doc: doc.id, place,
               title: `${placeOf(place)?.ctd} ${draft.ar}: مسودة ${draft.gaps.length ? `فيها ${count(draft.gaps.length, 'خانة ناقصة', 'خانتين ناقصين', 'خانات ناقصة', 'خانة ناقصة')}` : 'جاهزة للتوقيع'}`,
               detail: (draft.gaps.length ? `الناقص: ${draft.gaps.slice(0, 8).join('، ')}${draft.gaps.length > 8 ? '…' : ''}. ` : '') + 'بعد ما تكمّلها: اطبعها على ورق الشركة، وامضيها واختمها، وارفع النسخة الممسوحة مكانها.',
               actions: ['fill', 'program', 'claude', 'upload', 'accept'], rule: null });
  }
  const rank = n => ({ red: 0, amber: 1 }[n.level] ?? 2);
  return out.sort((a, b) => rank(a) - rank(b));
}

const need = f => ({ id: f.id, kind: f.kind, level: f.level, doc: f.doc, place: f.place, title: f.title, detail: f.detail, evidence: f.evidence, rule: f.rule, finding: f.id });

// The person's decision on an item: accepted as it is, with the reason (never without one).
export function accept(d, id, reason, by = 'you') {
  const r = String(reason || '').trim();
  if (r.length < 3) throw new Error('اكتب السبب (كلمتين على الأقل)');
  d.decisions = d.decisions || {};
  d.decisions[id] = { reason: r, at: new Date().toISOString(), by };
  d.log.push({ n: d.log.length + 1, at: d.decisions[id].at, what: 'accepted', item: id, reason: r });
}
