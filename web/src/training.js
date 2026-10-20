/* Training — courses people can study and finish (T-01, J-COMMUNITY-35 … 40): topic / level filters and a search above the approved
   course cards, the course window (syllabus, instructor, level, hours, price, what you get, how many enrolled), Enroll / Unenroll for a
   free course and the checkout for a paid one, lessons (video, PDF, text) with progress kept, a final quiz against the course's pass
   mark, a certificate with a unique code, a QR code and a public verify link (?cert=CODE, signed out too), My courses, the
   certificates on a profile, and Admin → Training for Drugbox (courses, lessons, quiz) without SQL.
   Demo: the approved six courses with sample lessons and quiz kept in this browser (DBK.store). Live: window.dxTraining, set by the
   data adapter, does the same against the database — this file only draws, in the approved visual language (the course card is
   the template; windows are the kit's). */
(function () {
  var C = window.dxCore, D = window.DBK; if (!C || !D) return;
  var esc = D.esc;
  function T(s) { return s; }   /* English here: the interface translates what it shows */
  function toast(m) { D.toast(m); }
  function ar() { return document.documentElement.lang === 'ar'; }
  function live() { var s = window.dxTraining; return !!(s && s.live && s.ready && s.ready()); }
  function S() { return live() ? window.dxTraining : DEMO; }
  function egp(n) { return window.dxCheckout ? window.dxCheckout.egp(n) : 'EGP ' + Math.round(n).toLocaleString('en'); }
  function day(t) { var d = t ? new Date(t) : new Date(); return isNaN(d) ? '' : d.toLocaleDateString(ar() ? 'ar-EG-u-nu-latn' : 'en-GB', { day: 'numeric', month: 'long', year: 'numeric' }); }
  var TOPICS = [['all', 'All courses'], ['gmp', 'GMP'], ['regulatory', 'Regulatory'], ['formulation', 'Formulation'], ['quality', 'Quality'], ['market', 'Market access']];
  var TOPIC = { gmp: '🏭 GMP', regulatory: '📋 Regulatory', formulation: '🧪 Formulation', quality: '✅ Quality', market: '🌍 Market access', other: '🎓 General' };
  var KIND = { video: '🎬', pdf: '📄', text: '📖' };
  var VAT = 0.14;

  /* ── demo: the approved six courses, sample lessons and quiz (the owner's real content comes later) ───────────────────── */
  var SAMPLE_VIDEO = '__LESSON_WEBM__';
  function L(title, kind, min, body) { return { title: title, kind: kind, minutes: min, body: body || '' }; }
  var SEED = [
    { id: 1, title: 'GMP Fundamentals', desc: 'Good Manufacturing Practices for pharmaceutical production and quality systems.', emoji: '🏭', duration: '4 hours', hours: 4, level: 'Beginner', topic: 'gmp', enrolled: 214,
      lessons: [L('Why GMP exists', 'video', 12), L('The GMP principles at a glance', 'pdf', 20, 'Quality is built in, not tested in: documented procedures, trained people, qualified premises and equipment, controlled materials, and records that show what really happened.'),
        L('Documentation and data integrity', 'text', 35, 'ALCOA+: records are attributable, legible, contemporaneous, original and accurate — and complete, consistent, enduring and available. A record written after the fact is not a GMP record.'),
        L('Premises, equipment and cleaning', 'text', 40, 'Qualify before use (DQ, IQ, OQ, PQ), clean to validated limits, and keep the status of every room and machine visible.'),
        L('Deviations and CAPA', 'text', 45, 'Record the deviation at once, assess its impact on the batch, find the root cause, and close it with a corrective and a preventive action that are checked for effectiveness.'),
        L('Batch release and the QP', 'text', 30, 'Only a qualified person releases a batch, after reviewing the batch record, the test results and every open deviation.')],
      quiz: [['What does GMP stand for?', ['Good Manufacturing Practice', 'General Medicine Process', 'Global Market Permit'], 0],
             ['Who releases a batch for sale?', ['The production supervisor', 'The qualified person', 'The sales manager'], 1],
             ['A record written two days after the work is…', ['acceptable if signed', 'not contemporaneous', 'required by ALCOA'], 1]] },
    { id: 2, title: 'EDA Registration Process', desc: 'Complete guide to Egyptian Drug Authority dossier preparation and submission.', emoji: '📋', duration: '6 hours', hours: 6, level: 'Intermediate', topic: 'regulatory', enrolled: 168,
      lessons: [L('The registration pathway', 'video', 15), L('The CTD structure', 'pdf', 30, 'Module 1 regional, Module 2 summaries, Module 3 quality, Module 4 non-clinical, Module 5 clinical.'),
        L('Pricing and the box', 'text', 40, 'Pricing follows the reference-price rules; the box and the leaflet are reviewed with the file.'), L('Stability for Zone IVb', 'text', 45, 'Long-term 30 °C / 75 % RH; accelerated 40 °C / 75 % RH.'),
        L('Variations after approval', 'text', 50, 'Classify the change, prepare the supporting data and submit before implementing.'), L('Answering EDA comments', 'text', 40, 'Answer each comment by number, with the evidence attached.')],
      quiz: [['Which CTD module holds the quality data?', ['Module 1', 'Module 3', 'Module 5'], 1], ['Zone IVb long-term storage is…', ['25 °C / 60 % RH', '30 °C / 75 % RH', '40 °C / 75 % RH'], 1]] },
    { id: 3, title: 'ICH Guidelines', desc: 'International Conference on Harmonisation Q1-Q14 guidelines.', emoji: '⚗️', duration: '8 hours', hours: 8, level: 'Advanced', topic: 'quality', enrolled: 97,
      lessons: [L('The ICH families', 'video', 15), L('Q1: stability', 'pdf', 60, 'Q1A(R2) stress and storage conditions; Q1E evaluation of stability data.'), L('Q2 and Q3: validation and impurities', 'text', 75, 'Validate what the method must do; set impurity limits on the reporting, identification and qualification thresholds.'),
        L('Q8, Q9, Q10: the quality system', 'text', 90, 'Design space, risk management and the pharmaceutical quality system work together.'), L('Q11 and Q12: substance and lifecycle', 'text', 80, 'Established conditions decide what needs a variation.'), L('Q14: analytical procedure development', 'text', 60, 'The analytical target profile guides the method and its changes.')],
      quiz: [['Which guideline covers stability testing?', ['Q1', 'Q7', 'Q10'], 0], ['Quality risk management is…', ['Q9', 'Q3', 'Q12'], 0], ['Q10 describes…', ['the pharmaceutical quality system', 'impurities', 'bioequivalence'], 0]] },
    { id: 4, title: 'Cosmetics Regulation', desc: 'EDA and GCC cosmetic product notification, labeling, and compliance.', emoji: '🧴', duration: '3 hours', hours: 3, level: 'Beginner', topic: 'regulatory', enrolled: 131,
      lessons: [L('What counts as a cosmetic', 'video', 10), L('The notification file', 'pdf', 25, 'Formula, specifications, safety assessment, label and the manufacturer\'s GMP certificate.'), L('Labels and claims', 'text', 30, 'A claim must be supported by evidence; medicinal claims make the product a drug.'),
        L('Banned and restricted ingredients', 'text', 30, 'Check the annexes before formulating.'), L('GCC notification', 'text', 35, 'Each GCC state keeps its own portal; the file is close to the EDA one.'), L('Keeping on the market', 'text', 20, 'Cosmetovigilance and renewals.')],
      quiz: [['A medicinal claim on a cream makes it…', ['a cosmetic', 'a drug', 'a supplement'], 1], ['A claim must be…', ['supported by evidence', 'in English', 'approved by the factory'], 0]] },
    { id: 5, title: 'Stability Studies', desc: 'Designing Zone IVa/IVb stability protocols per ICHQ1A/Q1E.', emoji: '🔬', duration: '5 hours', hours: 5, level: 'Intermediate', topic: 'formulation', enrolled: 88,
      lessons: [L('Why stability', 'video', 12), L('Designing the protocol', 'pdf', 45, 'Batches, packs, conditions, time points and tests.'), L('Climatic zones', 'text', 40, 'Zone IVa 30 °C / 65 % RH, Zone IVb 30 °C / 75 % RH.'),
        L('Photostability', 'text', 35, 'ICH Q1B light exposure.'), L('Evaluating the data', 'text', 50, 'Q1E: regression and pooling decide the shelf life.'), L('Writing the report', 'text', 30, 'Summarise, conclude, propose the shelf life and storage statement.')],
      quiz: [['Zone IVb long-term conditions are…', ['30 °C / 65 % RH', '30 °C / 75 % RH', '25 °C / 60 % RH'], 1], ['Shelf-life evaluation is described in…', ['Q1E', 'Q3A', 'Q8'], 0]] },
    { id: 6, title: 'GCC Market Access', desc: 'Registration pathways in Saudi Arabia, UAE, Kuwait, Bahrain, Qatar.', emoji: '🌍', duration: '4 hours', hours: 4, level: 'Intermediate', topic: 'market', enrolled: 59, price: 1500,
      lessons: [L('The GCC landscape', 'video', 12), L('SFDA in Saudi Arabia', 'pdf', 45, 'eCTD, the GMP inspection and pricing.'), L('MOHAP and DHA in the UAE', 'text', 40, 'Federal and emirate-level steps.'),
        L('Kuwait, Bahrain and Qatar', 'text', 45, 'Smaller markets, similar files.'), L('The GCC centralised procedure', 'text', 40, 'One file, several approvals.'), L('Pricing and tenders', 'text', 30, 'Reference prices and the tender calendar.')],
      quiz: [['The Saudi regulator is…', ['SFDA', 'EDA', 'MOHAP'], 0], ['The UAE federal regulator is…', ['MOHAP', 'SFDA', 'JFDA'], 0]] }
  ];
  function dget(k, d) { return D.store.get(k, d); }
  function dset(k, v) { D.store.set(k, v); }
  function demoCourses() {   /* the six, with Drugbox's own edits and new courses (Admin → Training) */
    var ov = dget('trCourses', {}), out = [];
    SEED.forEach(function (s) { var o = ov[s.id] || {}; out.push(Object.assign({}, s, { price: s.price || 0, instructor: 'Drugbox Academy', instructorTitle: 'Course team', passMark: 70, active: true }, o, { id: s.id })); });
    Object.keys(ov).forEach(function (k) { if (+k > 6) out.push(Object.assign({ lessons: [], quiz: [], enrolled: 0, price: 0, emoji: '🎓', level: 'Beginner', topic: 'other', passMark: 70, active: true }, ov[k], { id: +k })); });
    return out;
  }
  function pub(c) {   /* what a card and a window need of a course */
    return { id: c.id, title: c.title, desc: c.desc || '', emoji: c.emoji || '🎓', duration: c.duration || (c.hours ? c.hours + ' hours' : ''), hours: c.hours || null, level: c.level || 'Beginner',
      topic: c.topic || 'other', instructor: c.instructor || '', instructorTitle: c.instructorTitle || '', price: +c.price || 0, enrolled: +c.enrolled || 0, active: c.active !== false,
      passMark: c.passMark || 70, lessons: (c.lessons || []).length, questions: (c.quiz || []).length };
  }
  function mineD() { return dget('trMine', {}); }
  function course(id) { return demoCourses().filter(function (c) { return c.id === +id; })[0]; }
  var DEMO = {
    live: false,
    list: function () { return Promise.resolve(demoCourses().filter(function (c) { return c.active !== false || mineD()[c.id]; }).map(function (c) {
      var p = pub(c), m = mineD()[c.id]; if (m) p.enrolled += 1; return p; })); },
    mine: function () { var m = mineD(), out = {}; Object.keys(m).forEach(function (k) { var c = course(k); if (!c) return;
      out[k] = { status: m[k].status, paid: !!m[k].paid, done: m[k].done || [], total: (c.lessons || []).length, cert: m[k].cert || null, completed_at: m[k].completed_at || null }; }); return Promise.resolve(out); },
    lessons: function (id) { var c = course(id); return Promise.resolve(((c && c.lessons) || []).map(function (l, i) { return { id: id + ':' + (i + 1), position: i + 1, title: l.title, kind: l.kind, minutes: l.minutes }; })); },
    open: function (lid) { var p = String(lid).split(':'), c = course(p[0]), l = c && c.lessons[+p[1] - 1];
      if (!l) return Promise.reject(new Error('This lesson is no longer available'));
      if (!mineD()[c.id] && !(window.ME && ME.role === 'admin')) return Promise.reject(new Error('Enroll in the course to open its lessons'));
      return Promise.resolve({ id: lid, position: +p[1], title: l.title, kind: l.kind, minutes: l.minutes, body: l.body || '', url: l.url || (l.kind === 'video' ? SAMPLE_VIDEO : l.kind === 'pdf' ? pdfUrl(c, l) : null) }); },
    done: function (lid) { var p = String(lid).split(':'), m = mineD(), e = m[p[0]]; if (!e) return Promise.reject(new Error('Enroll in the course first'));
      e.done = e.done || []; if (e.done.indexOf(lid) < 0) e.done.push(lid); dset('trMine', m); return Promise.resolve(); },
    enroll: function (id) { var c = course(id); if (!c) return Promise.reject(new Error('This course is no longer available'));
      if (c.price > 0) return Promise.reject(new Error('This is a paid course — buy it to enrol'));
      var m = mineD(); if (!m[id]) m[id] = { status: 'enrolled', done: [], at: new Date().toISOString() }; dset('trMine', m); return Promise.resolve(); },
    unenroll: function (id) { var m = mineD(); if (m[id] && m[id].paid) return Promise.reject(new Error('A paid course stays yours')); delete m[id]; dset('trMine', m); return Promise.resolve(); },
    quote: function (id) { var c = course(id); return Promise.resolve({ amount_egp: c.price, vat_egp: Math.round(c.price * VAT * 100) / 100, total_egp: Math.round(c.price * (1 + VAT) * 100) / 100 }); },
    pay: function (id) {   /* the demo has no payment provider: the payment is shown as confirmed at once */
      var m = mineD(); m[id] = { status: 'enrolled', done: [], paid: true, at: new Date().toISOString() }; dset('trMine', m); return Promise.resolve({ demo: true }); },
    quiz: function (id) { var c = course(id); if (!mineD()[id]) return Promise.reject(new Error('Enroll in the course first'));
      return Promise.resolve((c.quiz || []).map(function (q, i) { return { id: i + 1, prompt: q[0], options: q[1] }; })); },
    submit: function (id, answers) {
      var c = course(id), m = mineD(), e = m[id]; if (!e) return Promise.reject(new Error('Enroll in the course first'));
      if (e.status === 'completed') return Promise.resolve({ passed: true, already: true, code: e.cert });
      var n = (c.lessons || []).length, d = (e.done || []).length; if (d < n) return Promise.reject(new Error('Finish all the lessons first (' + d + ' of ' + n + ' done)'));
      var at = (e.attempts || []).filter(function (t) { return Date.now() - t < 3600000; }); if (at.length >= 5) return Promise.reject(new Error('Five attempts in an hour — review the lessons and try again later'));
      at.push(Date.now()); e.attempts = at;
      var qs = c.quiz || [], right = qs.filter(function (q, i) { return answers[i] === q[2]; }).length, sc = qs.length ? Math.round(100 * right / qs.length) : 100, ok = sc >= (c.passMark || 70), code = null;
      if (ok) { code = 'DBX-' + Array.apply(null, Array(10)).map(function () { return '0123456789ABCDEF'[Math.floor(Math.random() * 16)]; }).join('');
        e.status = 'completed'; e.completed_at = new Date().toISOString(); e.cert = code;
        var certs = dget('trCerts', {}); certs[code] = { code: code, name: (window.ME && ME.name) || 'Drugbox member', course: c.title, hours: c.hours, issued_at: e.completed_at, uid: window.ME && ME.id }; dset('trCerts', certs); }
      dset('trMine', m); return Promise.resolve({ passed: ok, score: sc, correct: right, total: qs.length, pass_mark: c.passMark || 70, code: code });
    },
    cert: function (code) { var c = dget('trCerts', {})[String(code || '').toUpperCase()]; return Promise.resolve(c ? Object.assign({ valid: true }, c) : { valid: false, code: code }); },
    certsOf: function (uid) { var all = dget('trCerts', {}); return Promise.resolve(Object.keys(all).map(function (k) { return all[k]; }).filter(function (c) { return String(c.uid) === String(uid); })); },
    /* Admin → Training (the demo keeps Drugbox's edits in this browser) */
    adminList: function () { return Promise.resolve(demoCourses().map(function (c) { var p = pub(c); p.lessonList = c.lessons || []; return p; })); },
    saveCourse: function (c) { var ov = dget('trCourses', {}), id = c.id || Math.max.apply(null, [6].concat(Object.keys(ov).map(Number))) + 1;
      ov[id] = Object.assign(ov[id] || {}, { title: c.title, desc: c.desc, topic: c.topic, level: c.level, duration: c.duration, hours: c.hours, price: c.price, instructor: c.instructor, instructorTitle: c.instructorTitle, emoji: c.emoji, passMark: c.passMark, active: c.active });
      dset('trCourses', ov); return Promise.resolve(id); },
    setActive: function (id, on) { var ov = dget('trCourses', {}); ov[id] = Object.assign(ov[id] || {}, { active: on }); dset('trCourses', ov); return Promise.resolve(); },
    adminLessons: function (id) { return Promise.resolve((course(id).lessons || []).map(function (l, i) { return { id: id + ':' + (i + 1), position: i + 1, title: l.title, kind: l.kind, minutes: l.minutes }; })); },
    addLesson: function (id, l) { var ov = dget('trCourses', {}), c = course(id); ov[id] = ov[id] || {}; ov[id].lessons = (c.lessons || []).concat([{ title: l.title, kind: l.kind, minutes: l.minutes, body: l.body || '', url: l.file ? null : null }]); dset('trCourses', ov); return Promise.resolve(); },
    removeLesson: function (lid) { var p = String(lid).split(':'), ov = dget('trCourses', {}), c = course(p[0]); ov[p[0]] = ov[p[0]] || {}; ov[p[0]].lessons = (c.lessons || []).filter(function (x, i) { return i !== +p[1] - 1; }); dset('trCourses', ov); return Promise.resolve(); },
    adminQuiz: function (id) { return Promise.resolve((course(id).quiz || []).map(function (q, i) { return { id: id + ':' + (i + 1), position: i + 1, prompt: q[0], options: q[1], answer: q[2] }; })); },
    addQuestion: function (id, q) { var ov = dget('trCourses', {}), c = course(id); ov[id] = ov[id] || {}; ov[id].quiz = (c.quiz || []).concat([[q.prompt, q.options, q.answer]]); dset('trCourses', ov); return Promise.resolve(); },
    removeQuestion: function (qid) { var p = String(qid).split(':'), ov = dget('trCourses', {}), c = course(p[0]); ov[p[0]] = ov[p[0]] || {}; ov[p[0]].quiz = (c.quiz || []).filter(function (x, i) { return i !== +p[1] - 1; }); dset('trCourses', ov); return Promise.resolve(); }
  };
  /* the demo's lesson notes as a real PDF (one page of text, made here) */
  function pdfUrl(c, l) {
    var lines = [c.title, 'Lesson: ' + l.title, ''].concat(String(l.body || 'Lesson notes.').match(/.{1,86}(\s|$)/g) || []).concat(['', 'Drugbox Training - sample lesson notes']);
    var txt = lines.map(function (s, i) { return 'BT /F1 ' + (i === 0 ? 18 : 11) + ' Tf 56 ' + (780 - i * 18) + ' Td (' + String(s).replace(/[^\x20-\x7e]/g, '-').replace(/[()\\]/g, '\\$&') + ') Tj ET'; }).join('\n');
    var objs = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [3 0 R] /Count 1 >>', '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
                '<< /Length ' + txt.length + ' >>\nstream\n' + txt + '\nendstream', '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>'];
    var out = '%PDF-1.4\n', off = []; objs.forEach(function (o, i) { off.push(out.length); out += (i + 1) + ' 0 obj\n' + o + '\nendobj\n'; });
    var x = out.length; out += 'xref\n0 ' + (objs.length + 1) + '\n0000000000 65535 f \n' + off.map(function (o) { return ('000000000' + o).slice(-10) + ' 00000 n \n'; }).join('') + 'trailer\n<< /Size ' + (objs.length + 1) + ' /Root 1 0 R >>\nstartxref\n' + x + '\n%%EOF';
    return URL.createObjectURL(new Blob([out], { type: 'application/pdf' }));
  }

  /* ── state on screen ─────────────────────────────────────────────────────────────────────────────────────────────── */
  var V = { list: null, mine: {}, topic: 'all', level: '', q: '', tpl: null, at: 0, loading: false };
  function refresh(force) {
    if (V.loading && !force) return Promise.resolve();
    V.loading = true;
    return Promise.all([S().list(), S().mine()]).then(function (r) { V.err = false; V.list = (r[0] || []).filter(function (c) { return c.active !== false || (r[1] || {})[c.id]; }); V.mine = r[1] || {}; V.at = Date.now(); V.loading = false; paint(); }, function (e) { V.loading = false; V.err = true; paint(); toast((e && e.message) || 'Courses could not be loaded'); });
  }
  function state(c) { var m = V.mine[c.id]; if (!m) return c.price > 0 ? 'buy' : 'enroll'; if (m.status === 'completed') return 'done';
    var d = (m.done || []).length; return m.total && d >= m.total ? 'quiz' : d ? 'continue' : 'start'; }
  function pct(m) { return m && m.total ? Math.round(100 * (m.done || []).length / m.total) : 0; }
  function priceLabel(c) { return c.price > 0 ? egp(c.price * (1 + VAT)) + ' ' + T('incl. VAT') : T('Free'); }
  var BTN = { enroll: 'Enroll Now', buy: '🔒 Buy course', start: '▶ Start', continue: '▶ Continue', quiz: '📝 Final quiz', done: '🎓 Certificate' };

  /* ── the page: filters, the cards, My courses ───────────────────────────────────────────────────────────────────── */
  function bar() {
    return '<div class="tr-bar"><div class="cat-filter tr-chips" role="group" aria-label="Topic">' + TOPICS.map(function (t) {
      return '<button type="button" class="cf-tag' + (V.topic === t[0] ? ' on' : '') + '" aria-pressed="' + (V.topic === t[0]) + '" data-trt="' + t[0] + '">' + esc(t[1]) + '</button>'; }).join('') + '</div>' +
      '<div class="tr-tools"><input type="search" class="tr-q" placeholder="Search courses…" aria-label="Search courses" value="' + esc(V.q) + '">' +
      '<select class="tr-level" aria-label="Level"><option value="">All levels</option>' + ['Beginner', 'Intermediate', 'Advanced'].map(function (l) { return '<option value="' + l + '"' + (V.level === l ? ' selected' : '') + '>' + l + '</option>'; }).join('') + '</select>' +
      '<button type="button" class="btn-p tr-my">📚 My courses</button></div></div>';
  }
  function match(c) {
    if (V.topic !== 'all' && c.topic !== V.topic) return false;
    if (V.level && c.level !== V.level) return false;
    var q = V.q.trim().toLowerCase(); if (!q) return true;
    var hay = (c.title + ' ' + c.desc + ' ' + (TOPIC[c.topic] || '') + ' ' + c.instructor).toLowerCase();
    return q.split(/\s+/).every(function (w) { return hay.indexOf(w) >= 0; });
  }
  function card(c) {
    var el = document.createElement('div'); el.innerHTML = V.tpl; el = el.firstElementChild; el.dataset.course = c.id;
    var m = V.mine[c.id], st = state(c);
    el.querySelector('.tr-hero').textContent = c.emoji;
    var ti = el.querySelector('.tr-title'); ti.textContent = c.title; ti.setAttribute('role', 'button'); ti.setAttribute('tabindex', '0'); ti.dataset.tro = c.id; ti.setAttribute('data-noi18n', '');
    var de = el.querySelector('.tr-desc'); de.textContent = c.desc; de.setAttribute('data-noi18n', '');
    var mt = el.querySelector('.tr-meta'), sp = mt.querySelectorAll('span'); if (sp[0]) sp[0].textContent = '⏱ ' + c.duration; if (sp[1]) sp[1].textContent = c.level;
    mt.insertAdjacentHTML('beforeend', '<span class="tr-price' + (c.price > 0 ? ' paid' : '') + '">' + esc(priceLabel(c)) + '</span>');
    var info = '<div class="tr-info"><span>' + esc(TOPIC[c.topic] || TOPIC.other) + '</span><span>👥 ' + c.enrolled.toLocaleString('en') + ' enrolled</span></div>';
    if (m) info += '<div class="tr-state"><b>' + (st === 'done' ? '🎓 Completed' : '✅ Enrolled') + '</b><span>' + (m.done || []).length + ' / ' + (m.total || 0) + ' lessons · ' + pct(m) + '%</span></div>' +
      '<div class="tr-prog" role="progressbar" aria-valuenow="' + pct(m) + '" aria-valuemin="0" aria-valuemax="100"><i style="width:' + pct(m) + '%"></i></div>';
    mt.insertAdjacentHTML('afterend', info);
    var b = el.querySelector('button'); b.removeAttribute('onclick'); b.removeAttribute('style'); b.className = 'btn-p tr-go' + (st === 'done' ? ' tr-done' : m ? ' tr-in' : ''); b.dataset.trgo = c.id; b.textContent = BTN[st];
    if (m && st !== 'done' && !m.paid) b.insertAdjacentHTML('afterend', '<button type="button" class="tr-leave" data-trleave="' + c.id + '">Unenroll</button>');
    else if (!m) b.insertAdjacentHTML('afterend', '<button type="button" class="tr-leave" data-tro="' + c.id + '">Details</button>');
    return el;
  }
  function paint() {
    var root = document.querySelector('#content .training-grid'); if (!root || document.body.getAttribute('data-page') !== 'training') return;
    var first = root.querySelector('.tr-card'); if (first && !V.tpl) V.tpl = first.outerHTML;
    if (!V.tpl) return;
    var wrap = root.parentNode; if (!wrap.querySelector('.tr-bar')) root.insertAdjacentHTML('beforebegin', bar());
    else { wrap.querySelectorAll('.tr-chips .cf-tag').forEach(function (t) { t.classList.toggle('on', t.dataset.trt === V.topic); t.setAttribute('aria-pressed', String(t.dataset.trt === V.topic)); }); }
    if (!V.list) { root.innerHTML = '<div class="dbk-empty">' + (V.err ? esc(T('Courses could not be loaded')) + '<br><button type="button" class="btn-p" data-trretry="1">↺ Try again</button>' : esc(T('Loading courses…'))) + '</div>'; return; }
    var shown = V.list.filter(match); root.innerHTML = '';
    shown.forEach(function (c) { root.appendChild(card(c)); });
    if (!shown.length) root.innerHTML = '<div class="dbk-empty">' + esc(V.list.length ? T('No course matches — try another word or topic.') : T('No courses yet.')) +
      (V.list.length ? '<br><button type="button" class="btn-p" data-trclear="1">✕ Clear filters</button>' : '') + '</div>';
    var my = wrap.querySelector('.tr-my'); if (my) { var n = Object.keys(V.mine).length; my.textContent = '📚 My courses' + (n ? ' (' + n + ')' : ''); }
    var pill = document.querySelector('#content .dg-pill-page'); if (pill && window.dgPillText) { var pt = window.dgPillText('training'); if (pill.textContent !== pt) pill.textContent = pt; }
    if (window.dxI18nAdopt) window.dxI18nAdopt(wrap);
  }
  var oPill = window.dgPillText;
  window.dgPillText = function (page) {
    if (page === 'training') return (V.list ? V.list.length : '…') + ' COURSES  /  GMP  /  REGULATORY  /  FORMULATION';
    return oPill ? oPill.apply(this, arguments) : '';
  };
  var oRender = window.renderTraining;
  window.renderTraining = function (c) {
    var r = oRender.apply(this, arguments);
    var grid = c && c.querySelector('.training-grid'), first = grid && grid.querySelector('.tr-card'); if (first && !V.tpl) V.tpl = first.outerHTML;
    paint(); if (!V.list || Date.now() - V.at > 3000) refresh();
    return r;
  };
  window.dxTrainingUI = { refresh: refresh, open: function (id) { detail(id); }, mine: myCourses, verify: verify, cert: function (c) { certificate(c); }, state: function () { return V; } };

  /* ── one course: its window ─────────────────────────────────────────────────────────────────────────────────────── */
  function byId(id) { return (V.list || []).filter(function (c) { return String(c.id) === String(id); })[0]; }
  function detail(id) {
    var c = byId(id); if (!c) { toast('This course is no longer available'); return; }
    var m = V.mine[c.id], st = state(c);
    S().lessons(c.id).then(function (ls) {
      var done = (m && m.done) || [];
      var rows = ls.map(function (l) { var ok = done.indexOf(l.id) >= 0 || done.indexOf(String(l.id)) >= 0;
        return '<li class="tr-les' + (ok ? ' ok' : '') + '"' + (m ? ' role="button" tabindex="0" data-trl="' + esc(l.id) + '" data-trc="' + c.id + '"' : '') + '><span class="tr-les-n">' + (ok ? '✓' : l.position) + '</span>' +
          '<span class="tr-les-t"><span>Lesson ' + l.position + '</span> · <span data-noi18n>' + esc(l.title) + '</span></span><span class="tr-les-m">' + KIND[l.kind] + ' ' + l.minutes + ' min</span></li>'; }).join('');
      var mins = ls.reduce(function (a, l) { return a + (+l.minutes || 0); }, 0);
      var body = '<div class="tr-d">' +
        '<div class="tr-d-top"><span class="tr-d-ic">' + esc(c.emoji) + '</span><div><div class="tr-d-tags"><span>' + esc(TOPIC[c.topic] || TOPIC.other) + '</span><span>' + esc(c.level) + '</span></div>' +
        '<div class="tr-d-by">👤 <span>Instructor</span>: <b data-noi18n>' + esc(c.instructor || 'Drugbox Academy') + '</b>' + (c.instructorTitle ? ' — <span data-noi18n>' + esc(c.instructorTitle) + '</span>' : '') + '</div></div></div>' +
        '<p class="tr-d-desc" data-noi18n>' + esc(c.desc) + '</p>' +
        '<div class="tr-d-grid"><div><span>Level</span><b>' + esc(c.level) + '</b></div><div><span>Duration</span><b>' + esc(c.duration || (Math.round(mins / 6) / 10 + ' hours')) + '</b></div>' +
        '<div><span>Lessons</span><b>' + ls.length + '</b></div><div><span>Price</span><b>' + esc(priceLabel(c)) + '</b></div>' +
        '<div><span>Enrolled</span><b>' + c.enrolled.toLocaleString('en') + ' enrolled</b></div><div><span>You get</span><b>🎓 Certificate of completion</b></div></div>' +
        (m ? '<div class="tr-state"><b>' + (st === 'done' ? '🎓 Completed' : '✅ Enrolled') + '</b><span>' + done.length + ' / ' + ls.length + ' lessons · ' + pct(m) + '%</span></div>' : '') +
        '<div class="tr-d-h">📚 Syllabus</div>' + (rows ? '<ol class="tr-les-list">' + rows + '</ol>' : '<p class="tr-muted">The lessons of this course are being prepared.</p>') +
        '<div class="tr-d-quiz"><span>📝 <span>Final quiz</span> · <span>pass mark</span> ' + c.passMark + '%</span>' +
        (m ? '<button type="button" class="dbk-btn s" data-trquiz="' + c.id + '">' + (st === 'done' ? '🎓 Certificate' : '📝 Take the final quiz') + '</button>' : '') + '</div>' +
        (m && !m.paid && st !== 'done' ? '<div class="tr-d-more"><button type="button" class="tr-leave" data-trleave="' + c.id + '">Unenroll</button></div>' : '') + '</div>';
      var md = D.modal({ title: c.title, body: body, secondary: 'Close', primary: { label: BTN[st], onClick: function (bx, close) { close(); go(c.id); return false; } } });
      var hd = md.el.querySelector('.dbk-hd b'); if (hd) hd.setAttribute('data-noi18n', '');
      if (window.dxI18nAdopt) window.dxI18nAdopt(md.el);
    }, function (e) { toast(e.message); });
  }
  /* the card's / window's main step */
  function go(id) {
    var c = byId(id); if (!c) return; var st = state(c), m = V.mine[c.id];
    if (st === 'enroll') { S().enroll(c.id).then(function () { toast('Enrolled in ' + c.title + '!'); return refresh(true); }, function (e) { toast(e.message); }); return; }
    if (st === 'buy') { checkout(c); return; }
    if (st === 'quiz') { quiz(c.id); return; }
    if (st === 'done') { certificate(m.cert); return; }
    S().lessons(c.id).then(function (ls) { var done = (m && m.done) || [], nx = ls.filter(function (l) { return done.indexOf(l.id) < 0 && done.indexOf(String(l.id)) < 0; })[0] || ls[0];
      if (!nx) { toast('The lessons of this course are being prepared'); return; } lesson(c.id, nx.id, ls); });
  }
  function unenroll(id) {
    var c = byId(id); if (!c) return;
    D.modal({ title: 'Leave this course?', body: '<div>' + esc(T('Your progress is kept if you enrol again.')) + '</div>', secondary: 'Keep the course', primary: { label: 'Unenroll', danger: true, onClick: function () {
      S().unenroll(c.id).then(function () { toast('You left ' + c.title); return refresh(true); }, function (e) { toast(e.message); }); } } });
  }

  /* ── a paid course: the checkout (live: the server's price and the payment providers; demo: shown, then confirmed at once) ── */
  function checkout(c) {
    S().quote(c.id).then(function (q) {
      var methods = window.dxCheckout ? window.dxCheckout.methods('dxPayCourse') : '';
      var md = D.modal({ title: 'Buy course', body: '<div class="tr-co"><div class="tr-co-t"><span>' + esc(c.emoji) + '</span> <b data-noi18n>' + esc(c.title) + '</b></div>' +
        '<table class="cp-spec tr-co-tbl"><tr><td>Course fee</td><td>' + esc(egp(q.amount_egp)) + '</td></tr><tr><td>VAT (14%)</td><td>' + esc(egp(q.vat_egp)) + '</td></tr><tr><td><b>Total</b></td><td><b>' + esc(egp(q.total_egp)) + '</b></td></tr></table>' +
        '<p class="tr-muted">The course opens as soon as the payment is confirmed — you will get a notification.</p>' + methods + '</div>',
        primary: { label: '🔒 Pay ' + egp(q.total_egp), onClick: function (bx, close) {
          var method = window.dxCheckout ? window.dxCheckout.chosen(bx, 'dxPayCourse') : 'card', ok = bx.parentNode.querySelector('[data-a=ok]');
          if (!live()) { S().pay(c.id).then(function () { close(); toast('Payment received — you can start ' + c.title + ' now'); refresh(true); }); return false; }
          window.dxCheckout.start({ product: 'course_' + c.id, method: method }, ok, function () { close(); });
          return false; } } });
      if (window.dxI18nAdopt) window.dxI18nAdopt(md.el);
    }, function (e) { toast((e && e.message) || 'The price could not be loaded — please try again'); });
  }

  /* ── a lesson ───────────────────────────────────────────────────────────────────────────────────────────────────── */
  function lesson(cid, lid, ls) {
    S().open(lid).then(function (l) {
      var i = ls.map(function (x) { return String(x.id); }).indexOf(String(lid)), m = V.mine[cid] || { done: [] }, done = (m.done || []).map(String), ok = done.indexOf(String(lid)) >= 0;
      var media = l.kind === 'video' ? (l.url ? '<video class="tr-video" src="' + esc(l.url) + '" controls playsinline preload="metadata"></video>' : '<p class="tr-muted">The video of this lesson is being prepared.</p>')
        : l.kind === 'pdf' ? (l.url ? '<button type="button" class="btn-p tr-pdf" data-trpdf="' + esc(l.url) + '">📄 Open the lesson PDF</button>' : '<p class="tr-muted">The PDF of this lesson is being prepared.</p>') : '';
      var prog = function () { var n = done.length; return n + ' / ' + ls.length + ' · ' + (ls.length ? Math.round(100 * n / ls.length) : 0) + '%'; };
      var body = '<div class="tr-lesson"><div class="tr-l-head"><span>' + esc(T('Lesson')) + ' ' + (i + 1) + ' ' + esc(T('of')) + ' ' + ls.length + '</span> · <span>' + KIND[l.kind] + ' ' + l.minutes + ' min</span>' +
        '<span class="tr-l-prog">' + esc(prog()) + '</span></div>' + media + (l.body ? '<div class="tr-l-body" data-noi18n>' + esc(l.body).replace(/\n/g, '<br>') + '</div>' : '') +
        '<div class="tr-l-nav">' + (i > 0 ? '<button type="button" class="dbk-btn s" data-trnav="' + esc(ls[i - 1].id) + '">← Previous</button>' : '<span></span>') +
        (i < ls.length - 1 ? '<button type="button" class="dbk-btn s" data-trnav="' + esc(ls[i + 1].id) + '">Next lesson →</button>' : '<button type="button" class="dbk-btn s" data-trquiz="' + cid + '">📝 Final quiz</button>') + '</div></div>';
      var md = D.modal({ title: 'Lesson ' + (i + 1) + ': ' + l.title, body: body, secondary: 'Close', primary: ok ? null : { label: '✓ Mark complete', onClick: function (bx, close) {
        S().done(lid).then(function () {
          if (V.mine[cid]) { V.mine[cid].done = (V.mine[cid].done || []).concat([lid]); }
          done.push(String(lid)); var p = md.el.querySelector('.tr-l-prog'); if (p) p.textContent = prog();
          var b = md.el.querySelector('[data-a=ok]'); if (b) b.remove();
          toast(done.length >= ls.length ? 'All lessons done — the final quiz is open' : 'Lesson ' + (i + 1) + ' complete');
          refresh(true);
        }, function (e) { toast(e.message); }); return false; } } });
      md.el.dataset.trLesson = lid; md.el.dataset.trCourse = cid; md.el.__ls = ls;
      if (window.dxI18nAdopt) window.dxI18nAdopt(md.el);
    }, function (e) { toast(e.message); });
  }

  /* ── the final quiz ─────────────────────────────────────────────────────────────────────────────────────────────── */
  function quiz(cid) {
    var c = byId(cid); if (!c) return;
    S().quiz(cid).then(function (qs) {
      if (!qs.length) { submit(cid, []); return; }
      var body = '<div class="tr-quiz"><p class="tr-muted"><span>Pass mark</span> ' + c.passMark + '% · ' + qs.length + ' <span>questions</span></p>' + qs.map(function (q, i) {
        return '<fieldset class="tr-q"><legend><b>' + (i + 1) + '.</b> <span data-noi18n>' + esc(q.prompt) + '</span></legend>' + q.options.map(function (o, k) {
          return '<label><input type="radio" name="trq' + i + '" value="' + k + '"> <span data-noi18n>' + esc(o) + '</span></label>'; }).join('') + '</fieldset>'; }).join('') + '</div>';
      var md = D.modal({ title: 'Final quiz: ' + c.title, body: body, primary: { label: 'Submit answers', onClick: function (bx, close) {
        var ans = qs.map(function (q, i) { var r = bx.querySelector('input[name=trq' + i + ']:checked'); return r ? +r.value : -1; });
        if (ans.indexOf(-1) >= 0) { toast('Answer every question'); return false; }
        close(); submit(cid, ans); return false; } } });
      if (window.dxI18nAdopt) window.dxI18nAdopt(md.el);
    }, function (e) { toast(e.message); });
  }
  function submit(cid, ans) {
    var c = byId(cid);
    S().submit(cid, ans).then(function (r) {
      refresh(true);
      if (r.passed) { var md = D.modal({ title: '✅ Passed', body: '<div class="tr-res ok"><b>' + (r.score != null ? r.score + '%' : '') + '</b><p>' + esc(T('You completed the course. Your certificate is ready.')) + '</p></div>',
        secondary: 'Close', primary: { label: '🎓 View certificate', onClick: function (bx, close) { close(); certificate(r.code); return false; } } }); if (window.dxI18nAdopt) window.dxI18nAdopt(md.el); return; }
      var mf = D.modal({ title: '❌ Not passed yet', body: '<div class="tr-res"><b>' + r.score + '%</b><p><span>' + esc(T('You need')) + '</span> ' + r.pass_mark + '% · ' + r.correct + ' / ' + r.total + ' <span>' + esc(T('correct')) + '</span></p><p class="tr-muted">' +
        esc(T('Review the lessons and try again — the course is not completed until you pass.')) + '</p></div>', secondary: 'Close', primary: { label: '↺ Try again', onClick: function (bx, close) { close(); quiz(cid); return false; } } });
      if (window.dxI18nAdopt) window.dxI18nAdopt(mf.el);
    }, function (e) { toast(e.message); });
  }

  /* ── the certificate, its verify link, its PDF ──────────────────────────────────────────────────────────────────── */
  function verifyUrl(code) { return location.origin + location.pathname + '?cert=' + encodeURIComponent(code); }
  function qr(text) { if (!window.qrcode) return ''; try { var q = window.qrcode(0, 'M'); q.addData(text); q.make(); return q.createSvgTag({ cellSize: 3, margin: 6, scalable: true }); } catch (e) { return ''; } }
  function certHtml(c) {
    return '<div class="tr-cert"><div class="tr-cert-k">DRUGBOX TRAINING</div><div class="tr-cert-t">Certificate of completion</div>' +
      '<div class="tr-cert-l">This certifies that</div><div class="tr-cert-n" data-noi18n>' + esc(c.name) + '</div><div class="tr-cert-l">has completed</div>' +
      '<div class="tr-cert-c" data-noi18n>' + esc(c.course) + '</div><div class="tr-cert-m"><span>' + (c.hours ? esc(String(+c.hours)) + ' <span>hours</span> · ' : '') + '</span><span data-noi18n>' + esc(day(c.issued_at)) + '</span></div>' +
      '<div class="tr-cert-f"><div class="tr-cert-qr">' + qr(verifyUrl(c.code)) + '</div><div><div class="tr-cert-l">Certificate ID</div><b class="tr-cert-id" data-noi18n>' + esc(c.code) + '</b></div></div></div>';
  }
  function certificate(code) {
    if (!code) { toast('The certificate is being issued — open it again in a moment'); return; }
    S().cert(code).then(function (c) {
      if (!c || !c.valid) { toast('This certificate could not be found'); return; }
      var link = verifyUrl(c.code);
      var md = D.modal({ title: '🎓 Certificate', body: certHtml(c) + '<div class="dbk-f"><label for="trVerify">Verify link (anyone can open it)</label><input id="trVerify" readonly value="' + esc(link) + '" data-noi18n></div>' +
        '<div class="tr-cert-acts"><button type="button" class="dbk-btn s" data-trcopy="' + esc(link) + '">🔗 Copy link</button><button type="button" class="dbk-btn s" data-trprint="' + esc(c.code) + '">⬇ Download PDF</button></div>', secondary: 'Close' });
      md.el.__cert = c; if (window.dxI18nAdopt) window.dxI18nAdopt(md.el);
    });
  }
  function printCert(c) {   /* the browser's own "Save as PDF" keeps Arabic names right */
    var w = window.open('', '_blank'); if (!w) { toast('Allow pop-ups to download the certificate'); return; }
    var css = Array.prototype.map.call(document.querySelectorAll('style'), function (s) { return /tr-cert/.test(s.textContent) ? s.textContent : ''; }).join('\n');
    w.document.write('<!doctype html><html lang="' + (ar() ? 'ar' : 'en') + '" dir="' + (ar() ? 'rtl' : 'ltr') + '"><head><meta charset="utf-8"><title>' + esc(c.code) + '</title><style>' + css +
      ' body{margin:0;padding:24px;font-family:Inter,system-ui,sans-serif;background:#fff}@page{size:A4 landscape;margin:12mm}</style></head><body>' + certHtml(c).replace('class="tr-cert"', 'class="tr-cert tr-cert-print"') +
      '<p style="text-align:center;font:12px Inter,sans-serif;color:#64748b">' + esc(verifyUrl(c.code)) + '</p><script>setTimeout(function(){print()},300)<\/script></body></html>');
    w.document.close();
  }
  /* ?cert=CODE — the public check (signed out too) */
  function verify(code) {
    var svc = window.dxTraining && window.dxTraining.live ? window.dxTraining : DEMO;   /* signed out too: the live app asks the database */
    svc.cert(code).then(function (c) {
      var ok = c && c.valid;
      var md = D.modal({ title: ok ? '✅ Valid certificate' : (c && c.revoked ? '⚠️ Certificate withdrawn' : '❌ Certificate not found'), secondary: 'Close',
        body: ok ? certHtml(c) + '<p class="tr-muted">' + esc(T('Issued by Drugbox Training. This page checks the certificate against Drugbox\'s records.')) + '</p>'
          : '<p>' + esc(T('No valid Drugbox certificate has this ID:')) + ' <b data-noi18n>' + esc(String(code).slice(0, 40)) + '</b></p>' });
      if (window.dxI18nAdopt) window.dxI18nAdopt(md.el);
    }, function () { toast('The certificate could not be checked — try again'); });
  }
  (function () { var m = /[?&]cert=([A-Za-z0-9-]{4,40})/.exec(location.search); if (!m) return; var tries = 0;
    (function wait() { if (!document.body || ((window.dxLive || window.DRUGBOX_CONFIG) && !window.dxTraining && ++tries < 40)) return setTimeout(wait, 250); setTimeout(function () { verify(m[1]); }, 900); })(); })();

  /* ── My courses ─────────────────────────────────────────────────────────────────────────────────────────────────── */
  function myCourses() {
    var ids = Object.keys(V.mine);
    var rows = ids.map(function (id) { var c = byId(id), m = V.mine[id]; if (!c) return ''; var st = state(c);
      return '<div class="tr-my-row"><span class="tr-my-ic">' + esc(c.emoji) + '</span><div class="tr-my-b"><b data-noi18n>' + esc(c.title) + '</b><span>' + (m.done || []).length + ' / ' + (m.total || 0) + ' lessons · ' + pct(m) + '%' +
        (st === 'done' ? ' · 🎓 Completed' + (m.completed_at ? ' ' + esc(day(m.completed_at)) : '') : '') + '</span><div class="tr-prog"><i style="width:' + pct(m) + '%"></i></div></div>' +
        '<button type="button" class="btn-p" data-trgo="' + c.id + '">' + BTN[st] + '</button></div>'; }).join('');
    var md = D.modal({ title: '📚 My courses', secondary: 'Close', body: rows || '<div class="dbk-empty">' + esc(T('You are not enrolled in a course yet — pick one from Training.')) + '</div>' });
    if (window.dxI18nAdopt) window.dxI18nAdopt(md.el);
  }

  /* ── clicks ─────────────────────────────────────────────────────────────────────────────────────────────────────── */
  function onPage(e) { return e.target.closest && e.target; }
  document.addEventListener('click', function (e) {
    var t = onPage(e); if (!t) return;
    var x;
    if ((x = t.closest('[data-trt]')) && x.closest('.tr-bar')) { e.preventDefault(); V.topic = x.dataset.trt; paint(); return; }
    if ((x = t.closest('[data-trretry]'))) { e.preventDefault(); V.err = false; paint(); refresh(true); return; }
    if ((x = t.closest('[data-trclear]'))) { e.preventDefault(); V.topic = 'all'; V.level = ''; V.q = ''; var bq = document.querySelector('#content .tr-q'), bl = document.querySelector('#content .tr-level'); if (bq) bq.value = ''; if (bl) bl.value = ''; paint(); return; }
    if ((x = t.closest('.tr-bar .tr-my'))) { e.preventDefault(); myCourses(); return; }
    if ((x = t.closest('[data-trgo]'))) { e.preventDefault(); e.stopPropagation(); var ov = x.closest('.dbk-ov'); if (ov) ov.querySelector('.dbk-x').click(); go(x.dataset.trgo); return; }
    if ((x = t.closest('[data-trleave]'))) { e.preventDefault(); e.stopPropagation(); var ov2 = x.closest('.dbk-ov'); if (ov2) ov2.querySelector('.dbk-x').click(); unenroll(x.dataset.trleave); return; }
    if ((x = t.closest('[data-tro]'))) { e.preventDefault(); e.stopPropagation(); detail(x.dataset.tro); return; }
    if ((x = t.closest('.tr-les[data-trl]'))) { e.preventDefault(); var cid = x.dataset.trc, lid = x.dataset.trl; x.closest('.dbk-ov').querySelector('.dbk-x').click(); S().lessons(cid).then(function (ls) { lesson(cid, isNaN(+lid) ? lid : +lid, ls); }); return; }
    if ((x = t.closest('[data-trnav]'))) { e.preventDefault(); var o = x.closest('.dbk-ov'), ls = o.__ls, cid2 = o.dataset.trCourse, nid = x.dataset.trnav; o.querySelector('.dbk-x').click(); lesson(cid2, isNaN(+nid) ? nid : +nid, ls); return; }
    if ((x = t.closest('[data-trquiz]'))) { e.preventDefault(); var o3 = x.closest('.dbk-ov'), qc = x.dataset.trquiz, cc = byId(qc); if (o3) o3.querySelector('.dbk-x').click();
      if (cc && state(cc) === 'done') certificate(V.mine[qc].cert); else if (cc && state(cc) !== 'quiz') toast('Finish all the lessons first (' + ((V.mine[qc] || {}).done || []).length + ' of ' + ((V.mine[qc] || {}).total || 0) + ' done)'); else quiz(qc); return; }
    if ((x = t.closest('[data-trpdf]'))) { e.preventDefault(); window.open(x.dataset.trpdf, '_blank', 'noopener'); return; }
    if ((x = t.closest('[data-trcopy]'))) { e.preventDefault(); var u = x.dataset.trcopy; (navigator.clipboard ? navigator.clipboard.writeText(u) : Promise.reject()).then(function () { toast('Link copied!'); }, function () { var i = document.getElementById('trVerify'); if (i) { i.select(); try { document.execCommand('copy'); toast('Link copied!'); } catch (er) {} } }); return; }
    if ((x = t.closest('[data-trprint]'))) { e.preventDefault(); var oc = x.closest('.dbk-ov'); if (oc && oc.__cert) printCert(oc.__cert); return; }
  }, true);
  document.addEventListener('keydown', function (e) { if (e.key !== 'Enter' && e.key !== ' ') return; var x = e.target.closest && e.target.closest('[data-tro][role=button], .tr-les[data-trl]'); if (x) { e.preventDefault(); x.click(); } }, true);
  document.addEventListener('input', function (e) {
    if (e.target.classList && e.target.classList.contains('tr-q') && e.target.closest('.tr-bar')) { V.q = e.target.value; if (V.q.trim()) V.topic = 'all'; clearTimeout(V.qt); V.qt = setTimeout(paint, 150); }
  }, true);
  document.addEventListener('change', function (e) { if (e.target.classList && e.target.classList.contains('tr-level')) { V.level = e.target.value; paint(); } }, true);

  /* ── a profile's certificates ───────────────────────────────────────────────────────────────────────────────────── */
  function profileCerts() {
    var c = document.getElementById('content'); if (!c || c.querySelector('.tr-pcerts')) return;
    var tabs = c.querySelector('.profile-tabs'), uid = window._profUser && window._profUser.id != null ? window._profUser.id : (window.ME && ME.id); if (!tabs) return;
    var box = document.createElement('div'); box.className = 'card tr-pcerts'; box.hidden = true; tabs.parentNode.insertBefore(box, tabs);   /* above the profile's tabs */
    S().certsOf(uid).then(function (list) {
      list = (list || []).filter(function (x) { return x && x.valid !== false; }); if (!list.length || !box.isConnected) return;
      box.innerHTML = '<div class="tr-pc-h">🎓 <span>Certificates</span></div>' + list.map(function (x) {
        return '<div class="tr-pc-row" role="button" tabindex="0" data-trcert="' + esc(x.code) + '"><b data-noi18n>' + esc(x.course) + '</b><span><span>Drugbox Training</span> · <span data-noi18n>' + esc(day(x.issued_at)) + '</span> · <span data-noi18n>' + esc(x.code) + '</span></span></div>'; }).join('');
      box.hidden = false; if (window.dxI18nAdopt) window.dxI18nAdopt(box);
    });
  }
  document.addEventListener('click', function (e) { var x = e.target.closest && e.target.closest('[data-trcert]'); if (x) { e.preventDefault(); certificate(x.dataset.trcert); } }, true);
  var oProfile = window.renderProfile;   /* my profile and anyone's (gotoProfile draws it directly) */
  if (typeof oProfile === 'function') window.renderProfile = function () { var r = oProfile.apply(this, arguments); setTimeout(profileCerts, 0); return r; };

  /* ── Admin → Training (Drugbox): courses, lessons, the quiz ─────────────────────────────────────────────────────── */
  var oAdmin = window.renderAdmin;
  if (typeof oAdmin === 'function') window.renderAdmin = function () {
    var r = oAdmin.apply(this, arguments);
    var nav = document.querySelector('.admin-nav'); if (nav && !nav.querySelector('[data-tradm]')) {
      var it = document.createElement('div'); it.className = 'admin-nav-item' + (window.adminTab === 'training' ? ' active' : ''); it.dataset.tradm = '1'; it.textContent = '🎓 Training';
      it.setAttribute('onclick', "switchAdminTab('training')"); var after = nav.querySelector('[onclick*="posts"]'); if (after && after.nextSibling) nav.insertBefore(it, after.nextSibling); else nav.appendChild(it);
    }
    return r;
  };
  var oTab = window.renderAdminTab;
  if (typeof oTab === 'function') window.renderAdminTab = function (tab) { if (tab === 'training') { var c = document.getElementById('adminContent'); if (c) adminTraining(c); return; } return oTab.apply(this, arguments); };
  function sel(id, opts, cur) { return '<select id="' + id + '">' + opts.map(function (o) { return '<option value="' + esc(o[0]) + '"' + (String(o[0]) === String(cur) ? ' selected' : '') + '>' + esc(o[1]) + '</option>'; }).join('') + '</select>'; }
  function adminTraining(c) {
    c.innerHTML = '<div class="tr-adm"><div class="tr-adm-h"><h2>🎓 Training</h2><button type="button" class="btn-p" data-tradd="1">+ Add course</button></div><div class="tr-adm-list"><div class="dbk-empty">' + esc(T('Loading courses…')) + '</div></div></div>';
    S().adminList().then(function (list) {
      var box = c.querySelector('.tr-adm-list'); if (!box) return;
      box.innerHTML = list.length ? '<table class="tr-adm-tbl"><thead><tr><th>Course</th><th>Topic</th><th>Level</th><th>Price</th><th>Lessons</th><th>Enrolled</th><th>Status</th><th></th></tr></thead><tbody>' + list.map(function (x) {
        return '<tr data-trid="' + x.id + '"><td><b data-noi18n>' + esc(x.emoji + ' ' + x.title) + '</b></td><td>' + esc(TOPIC[x.topic] || TOPIC.other) + '</td><td>' + esc(x.level) + '</td><td>' + esc(x.price > 0 ? egp(x.price) : T('Free')) + '</td>' +
          '<td>' + x.lessons + '</td><td>' + x.enrolled + '</td><td>' + (x.active ? '<span class="tr-live">● Live</span>' : '<span class="tr-off">Hidden</span>') + '</td>' +
          '<td class="tr-adm-acts"><button type="button" class="dbk-btn s" data-tredit="' + x.id + '">✏️ Edit</button><button type="button" class="dbk-btn s" data-trles="' + x.id + '">📚 Lessons</button>' +
          '<button type="button" class="dbk-btn s" data-trqz="' + x.id + '">📝 Quiz</button><button type="button" class="dbk-btn s" data-tract="' + x.id + '" data-on="' + (x.active ? 0 : 1) + '">' + (x.active ? 'Hide' : 'Publish') + '</button></td></tr>'; }).join('') + '</tbody></table>'
        : '<div class="dbk-empty">' + esc(T('No courses yet.')) + '</div>';
      c.__list = list; if (window.dxI18nAdopt) window.dxI18nAdopt(c);
    }, function (e) { toast(e.message); });
  }
  function courseForm(x) {
    x = x || { topic: 'gmp', level: 'Beginner', price: 0, emoji: '🎓', passMark: 70, active: true };
    var md = D.modal({ title: x.id ? 'Edit course' : 'Add course', body:
      '<div class="dbk-f"><label for="trT">Title *</label><input id="trT" data-req maxlength="160" value="' + esc(x.title || '') + '"></div>' +
      '<div class="dbk-f"><label for="trDs">Description</label><textarea id="trDs" maxlength="2000">' + esc(x.desc || '') + '</textarea></div>' +
      '<div class="dbk-row"><div class="dbk-f"><label for="trTp">Topic</label>' + sel('trTp', TOPICS.slice(1).concat([['other', 'General']]), x.topic) + '</div>' +
      '<div class="dbk-f"><label for="trLv">Level</label>' + sel('trLv', [['Beginner', 'Beginner'], ['Intermediate', 'Intermediate'], ['Advanced', 'Advanced']], x.level) + '</div></div>' +
      '<div class="dbk-row"><div class="dbk-f"><label for="trDu">Duration</label><input id="trDu" maxlength="40" placeholder="e.g. 4 hours" value="' + esc(x.duration || '') + '"></div>' +
      '<div class="dbk-f"><label for="trHr">Hours (on the certificate)</label><input id="trHr" type="number" min="0.5" max="500" step="0.5" value="' + esc(x.hours || '') + '"></div></div>' +
      '<div class="dbk-row"><div class="dbk-f"><label for="trPr">Price (EGP before VAT, 0 = free)</label><input id="trPr" type="number" min="0" max="100000" step="1" value="' + esc(x.price || 0) + '"></div>' +
      '<div class="dbk-f"><label for="trPm">Pass mark (%)</label><input id="trPm" type="number" min="50" max="100" value="' + esc(x.passMark || 70) + '"></div></div>' +
      '<div class="dbk-row"><div class="dbk-f"><label for="trIn">Instructor</label><input id="trIn" maxlength="120" value="' + esc(x.instructor || '') + '"></div>' +
      '<div class="dbk-f"><label for="trIt">Instructor\'s qualifications</label><input id="trIt" maxlength="160" value="' + esc(x.instructorTitle || '') + '"></div></div>' +
      '<div class="dbk-f"><label for="trEm">Icon</label><input id="trEm" maxlength="4" value="' + esc(x.emoji || '🎓') + '"></div>',
      primary: { label: x.id ? 'Save' : 'Publish', onClick: function (bx, close) {
        if (!D.requireFields(bx)) return false;
        var v = function (id) { return bx.querySelector('#' + id).value.trim(); };
        var o = { id: x.id, title: v('trT'), desc: v('trDs'), topic: v('trTp'), level: v('trLv'), duration: v('trDu'), hours: v('trHr') ? +v('trHr') : null, price: Math.max(0, +v('trPr') || 0),
          passMark: Math.min(100, Math.max(50, +v('trPm') || 70)), instructor: v('trIn'), instructorTitle: v('trIt'), emoji: v('trEm') || '🎓', active: x.id ? x.active : true };
        if (o.title.length < 3) { toast('The title needs at least 3 characters'); return false; }
        S().saveCourse(o).then(function () { close(); toast(x.id ? 'Course saved' : 'Course published'); refresh(true); var c = document.getElementById('adminContent'); if (c) adminTraining(c); }, function (e) { toast(e.message); });
        return false; } } });
    if (window.dxI18nAdopt) window.dxI18nAdopt(md.el);
  }
  function lessonsAdmin(id) {
    S().adminLessons(id).then(function (ls) {
      var md = D.modal({ title: '📚 Lessons', secondary: 'Close', body: '<ol class="tr-les-list">' + (ls.map(function (l) { return '<li class="tr-les"><span class="tr-les-n">' + l.position + '</span><span class="tr-les-t" data-noi18n>' + esc(l.title) + '</span><span class="tr-les-m">' + KIND[l.kind] + ' ' + l.minutes + ' min</span>' +
          '<button type="button" class="tr-leave" data-trlrm="' + esc(l.id) + '" data-trcid="' + id + '">Remove</button></li>'; }).join('') || '<p class="tr-muted">No lessons yet.</p>') + '</ol>' +
        '<div class="tr-d-h">+ Add a lesson</div><div class="dbk-f"><label for="trLt">Lesson title *</label><input id="trLt" maxlength="160"></div>' +
        '<div class="dbk-row"><div class="dbk-f"><label for="trLk">Kind</label>' + sel('trLk', [['text', '📖 Text'], ['video', '🎬 Video'], ['pdf', '📄 PDF']], 'text') + '</div>' +
        '<div class="dbk-f"><label for="trLm">Minutes</label><input id="trLm" type="number" min="1" max="600" value="10"></div></div>' +
        '<div class="dbk-f"><label for="trLb">Text</label><textarea id="trLb" maxlength="20000"></textarea></div>' +
        '<div class="dbk-f"><label for="trLf">File (video: MP4/WebM; PDF)</label><input id="trLf" type="file" accept="video/mp4,video/webm,application/pdf"></div>',
        primary: { label: 'Add lesson', onClick: function (bx, close) {
          var t = bx.querySelector('#trLt').value.trim(); if (t.length < 2) { toast('Give the lesson a title'); return false; }
          var f = bx.querySelector('#trLf').files[0], k = bx.querySelector('#trLk').value;
          if (f && f.size > 200 * 1048576) { toast('The file is larger than 200 MB'); return false; }
          if (f && !(/^video\/(mp4|webm)$/.test(f.type) || f.type === 'application/pdf')) { toast('Use an MP4 or WebM video, or a PDF'); return false; }
          S().addLesson(id, { title: t, kind: k, minutes: Math.max(1, +bx.querySelector('#trLm').value || 10), body: bx.querySelector('#trLb').value, file: f || null })
            .then(function () { close(); toast('Lesson added'); lessonsAdmin(id); refresh(true); }, function (e) { toast(e.message); });
          return false; } } });
      if (window.dxI18nAdopt) window.dxI18nAdopt(md.el);
    }, function (e) { toast(e.message); });
  }
  function quizAdmin(id) {
    S().adminQuiz(id).then(function (qs) {
      var md = D.modal({ title: '📝 Final quiz', secondary: 'Close', body: '<ol class="tr-les-list">' + (qs.map(function (q) { return '<li class="tr-les"><span class="tr-les-n">' + q.position + '</span><span class="tr-les-t"><span data-noi18n>' + esc(q.prompt) + '</span><br><small data-noi18n>' +
          q.options.map(function (o, i) { return (i === q.answer ? '✓ ' : '') + esc(o); }).join(' · ') + '</small></span><button type="button" class="tr-leave" data-trqrm="' + esc(q.id) + '" data-trcid="' + id + '">Remove</button></li>'; }).join('') || '<p class="tr-muted">No questions yet — without a quiz, finishing the lessons completes the course.</p>') + '</ol>' +
        '<div class="tr-d-h">+ Add a question</div><div class="dbk-f"><label for="trQp">Question *</label><input id="trQp" maxlength="500"></div>' +
        '<div class="dbk-f"><label for="trQo">Answers (one per line, 2–6)</label><textarea id="trQo"></textarea></div>' +
        '<div class="dbk-f"><label for="trQa">Number of the right answer</label><input id="trQa" type="number" min="1" max="6" value="1"></div>',
        primary: { label: 'Add question', onClick: function (bx, close) {
          var p = bx.querySelector('#trQp').value.trim(), o = bx.querySelector('#trQo').value.split('\n').map(function (s) { return s.trim(); }).filter(Boolean), a = (+bx.querySelector('#trQa').value || 1) - 1;
          if (p.length < 3) { toast('Write the question'); return false; } if (o.length < 2 || o.length > 6) { toast('Give 2 to 6 answers, one per line'); return false; } if (a < 0 || a >= o.length) { toast('The right answer must be one of the answers'); return false; }
          S().addQuestion(id, { prompt: p, options: o, answer: a }).then(function () { close(); toast('Question added'); quizAdmin(id); }, function (e) { toast(e.message); });
          return false; } } });
      if (window.dxI18nAdopt) window.dxI18nAdopt(md.el);
    }, function (e) { toast(e.message); });
  }
  document.addEventListener('click', function (e) {
    var x = e.target.closest && e.target.closest('[data-tradd],[data-tredit],[data-trles],[data-trqz],[data-tract],[data-trlrm],[data-trqrm]'); if (!x) return;
    e.preventDefault(); e.stopPropagation();
    var adm = document.getElementById('adminContent'), list = (adm && adm.__list) || [];
    if (x.dataset.tradd) return courseForm();
    if (x.dataset.tredit) return courseForm(list.filter(function (c) { return String(c.id) === x.dataset.tredit; })[0]);
    if (x.dataset.trles) return lessonsAdmin(x.dataset.trles);
    if (x.dataset.trqz) return quizAdmin(x.dataset.trqz);
    if (x.dataset.tract) { S().setActive(x.dataset.tract, x.dataset.on === '1').then(function () { toast(x.dataset.on === '1' ? 'Course published' : 'Course hidden from the catalog — its learners keep it'); if (adm) adminTraining(adm); refresh(true); }, function (er) { toast(er.message); }); return; }
    var ov = x.closest('.dbk-ov'), cid = x.dataset.trcid;
    if (x.dataset.trlrm) { S().removeLesson(isNaN(+x.dataset.trlrm) ? x.dataset.trlrm : +x.dataset.trlrm).then(function () { if (ov) ov.querySelector('.dbk-x').click(); toast('Lesson removed'); lessonsAdmin(cid); refresh(true); }, function (er) { toast(er.message); }); return; }
    if (x.dataset.trqrm) { S().removeQuestion(isNaN(+x.dataset.trqrm) ? x.dataset.trqrm : +x.dataset.trqrm).then(function () { if (ov) ov.querySelector('.dbk-x').click(); toast('Question removed'); quizAdmin(cid); }, function (er) { toast(er.message); }); }
  }, true);

  /* the live service may arrive after this file (the adapter loads later): draw again with the real data */
  C.onRender('training', function () { if (document.body.getAttribute('data-page') === 'training' && !document.querySelector('#content .tr-bar')) paint(); });
  window.addEventListener('dx:training', function () { V.list = null; V.mine = {}; V.at = 0; if (document.body.getAttribute('data-page') === 'training') refresh(true); });
})();

/* ===== AREA community: training — Arabic (the interface translates as it draws; course titles and lessons stay as Drugbox wrote them) ===== */
(function () {
  if (!window.dxI18nExtend) return;
  window.dxI18nExtend({
    'All courses': 'كل الدورات', 'GMP': 'GMP', 'Regulatory': 'التسجيل', 'Formulation': 'التركيبات', 'Quality': 'الجودة', 'Market access': 'دخول الأسواق', 'General': 'عام',
    '🏭 GMP': '🏭 GMP', '📋 Regulatory': '📋 التسجيل', '🧪 Formulation': '🧪 التركيبات', '✅ Quality': '✅ الجودة', '🌍 Market access': '🌍 دخول الأسواق', '🎓 General': '🎓 عام',
    'Search courses…': 'ابحث في الدورات…', 'Search courses': 'ابحث في الدورات', 'All levels': 'كل المستويات', 'Level': 'المستوى', 'Topic': 'الموضوع',
    '📚 My courses': '📚 دوراتي', 'My courses': 'دوراتي', 'Enroll Now': 'سجّل الآن', '🔒 Buy course': '🔒 اشترِ الدورة', '▶ Start': '▶ ابدأ', '▶ Continue': '▶ متابعة',
    '📝 Final quiz': '📝 الاختبار النهائي', '🎓 Certificate': '🎓 الشهادة', 'Unenroll': 'إلغاء التسجيل', 'Details': 'التفاصيل', '✅ Enrolled': '✅ مسجّل', '🎓 Completed': '🎓 مكتملة',
    'Free': 'مجاني', 'incl. VAT': 'شامل الضريبة', 'Instructor': 'المحاضر', 'Duration': 'المدة', 'Lessons': 'الدروس', 'Price': 'السعر', 'Enrolled': 'المسجّلون', 'You get': 'ستحصل على',
    '🎓 Certificate of completion': '🎓 شهادة إتمام', '📚 Syllabus': '📚 المنهج', 'Final quiz': 'الاختبار النهائي', 'pass mark': 'درجة النجاح', 'Pass mark': 'درجة النجاح', 'questions': 'أسئلة',
    '📝 Take the final quiz': '📝 ادخل الاختبار النهائي', 'The lessons of this course are being prepared.': 'دروس هذه الدورة قيد الإعداد.', 'Loading courses…': 'جارٍ تحميل الدورات…',
    'No course matches — try another word or topic.': 'لا توجد دورة مطابقة — جرّب كلمة أو موضوعاً آخر.', 'No courses yet.': 'لا توجد دورات بعد.', '✕ Clear filters': '✕ امسح الفلاتر',
    'Leave this course?': 'إلغاء التسجيل في هذه الدورة؟', 'Keep the course': 'الإبقاء على الدورة', 'Your progress is kept if you enrol again.': 'يُحفظ تقدّمك إن سجّلت مرة أخرى.',
    'Buy course': 'شراء الدورة', 'Course fee': 'رسوم الدورة', 'VAT (14%)': 'ضريبة القيمة المضافة (14%)', 'Total': 'الإجمالي',
    'The course opens as soon as the payment is confirmed — you will get a notification.': 'تُفتح الدورة فور تأكيد الدفع — سيصلك إشعار.',
    'Lesson': 'الدرس', 'of': 'من', '← Previous': 'السابق →', 'Next lesson →': 'الدرس التالي ←', '✓ Mark complete': '✓ تم الإنجاز', 'Close': 'إغلاق',
    '📄 Open the lesson PDF': '📄 افتح ملف الدرس PDF', 'The video of this lesson is being prepared.': 'فيديو هذا الدرس قيد الإعداد.', 'The PDF of this lesson is being prepared.': 'ملف هذا الدرس قيد الإعداد.',
    'All lessons done — the final quiz is open': 'أنهيت كل الدروس — الاختبار النهائي متاح', 'Submit answers': 'أرسل الإجابات', 'Answer every question': 'أجب عن كل الأسئلة',
    '✅ Passed': '✅ ناجح', '❌ Not passed yet': '❌ لم تنجح بعد', 'You completed the course. Your certificate is ready.': 'أكملت الدورة. شهادتك جاهزة.', '🎓 View certificate': '🎓 اعرض الشهادة',
    'You need': 'تحتاج', 'correct': 'إجابة صحيحة', 'Review the lessons and try again — the course is not completed until you pass.': 'راجع الدروس وحاول مرة أخرى — لا تكتمل الدورة إلا بالنجاح.', '↺ Try again': '↺ حاول مرة أخرى',
    'DRUGBOX TRAINING': 'تدريب DRUGBOX', 'Certificate of completion': 'شهادة إتمام', 'This certifies that': 'تشهد Drugbox بأن', 'has completed': 'أتمّ بنجاح', 'hours': 'ساعات', 'Certificate ID': 'رقم الشهادة',
    'Verify link (anyone can open it)': 'رابط التحقق (يفتحه أي شخص)', '🔗 Copy link': '🔗 انسخ الرابط', '⬇ Download PDF': '⬇ تنزيل PDF', 'Link copied!': 'تم نسخ الرابط!',
    '✅ Valid certificate': '✅ شهادة صحيحة', '⚠️ Certificate withdrawn': '⚠️ الشهادة مسحوبة', '❌ Certificate not found': '❌ الشهادة غير موجودة',
    'Issued by Drugbox Training. This page checks the certificate against Drugbox\'s records.': 'صادرة عن تدريب Drugbox. هذه الصفحة تتحقق من الشهادة في سجلات Drugbox.',
    'No valid Drugbox certificate has this ID:': 'لا توجد شهادة صحيحة من Drugbox بهذا الرقم:', 'The certificate could not be checked — try again': 'تعذّر التحقق من الشهادة — حاول مرة أخرى',
    'You are not enrolled in a course yet — pick one from Training.': 'لم تسجّل في أي دورة بعد — اختر واحدة من التدريب.', '🎓 Certificates': '🎓 الشهادات', 'Certificates': 'الشهادات', 'Drugbox Training': 'تدريب Drugbox',
    'Allow pop-ups to download the certificate': 'اسمح بالنوافذ المنبثقة لتنزيل الشهادة', 'This certificate could not be found': 'تعذّر العثور على هذه الشهادة',
    'The certificate is being issued — open it again in a moment': 'الشهادة قيد الإصدار — افتحها بعد لحظات', 'This course is no longer available': 'هذه الدورة لم تعد متاحة',
    'This is a paid course — buy it to enrol': 'هذه دورة مدفوعة — اشترِها لتسجّل', 'A paid course stays yours': 'الدورة المدفوعة تبقى لك', 'Enroll in the course first': 'سجّل في الدورة أولاً',
    'Enroll in the course to open its lessons': 'سجّل في الدورة لتفتح دروسها', 'The lessons of this course are being prepared': 'دروس هذه الدورة قيد الإعداد',
    'Five attempts in an hour — review the lessons and try again later': 'خمس محاولات في ساعة — راجع الدروس وحاول لاحقاً',
    'The price could not be loaded — please try again': 'تعذّر تحميل السعر — حاول مرة أخرى', 'Courses could not be loaded': 'تعذّر تحميل الدورات',
    /* Admin → Training */
    '🎓 Training': '🎓 التدريب', '+ Add course': '+ إضافة دورة', 'Course': 'الدورة', 'Status': 'الحالة', '● Live': '● منشورة', 'Hidden': 'مخفية', '✏️ Edit': '✏️ تعديل',
    '📚 Lessons': '📚 الدروس', '📝 Quiz': '📝 الاختبار', 'Hide': 'إخفاء', 'Publish': 'نشر', 'Edit course': 'تعديل الدورة', 'Add course': 'إضافة دورة', 'Title *': 'العنوان *', 'Description': 'الوصف',
    'Hours (on the certificate)': 'الساعات (على الشهادة)', 'Price (EGP before VAT, 0 = free)': 'السعر (ج.م قبل الضريبة، 0 = مجاني)', 'Pass mark (%)': 'درجة النجاح (%)',
    'Instructor\'s qualifications': 'مؤهلات المحاضر', 'Icon': 'الأيقونة', 'Save': 'حفظ', 'Course saved': 'تم حفظ الدورة', 'Course published': 'تم نشر الدورة',
    'Course hidden from the catalog — its learners keep it': 'أُخفيت الدورة من الكتالوج — يحتفظ بها المسجّلون', 'The title needs at least 3 characters': 'العنوان يحتاج 3 أحرف على الأقل',
    '+ Add a lesson': '+ إضافة درس', 'Lesson title *': 'عنوان الدرس *', 'Kind': 'النوع', '📖 Text': '📖 نص', '🎬 Video': '🎬 فيديو', '📄 PDF': '📄 PDF', 'Minutes': 'الدقائق', 'Text': 'النص',
    'File (video: MP4/WebM; PDF)': 'ملف (فيديو MP4/WebM أو PDF)', 'Add lesson': 'إضافة الدرس', 'Lesson added': 'تمت إضافة الدرس', 'Lesson removed': 'تم حذف الدرس', 'Remove': 'حذف', 'No lessons yet.': 'لا توجد دروس بعد.',
    'Give the lesson a title': 'اكتب عنواناً للدرس', 'The file is larger than 200 MB': 'الملف أكبر من 200 ميجابايت', 'Use an MP4 or WebM video, or a PDF': 'استخدم فيديو MP4 أو WebM أو ملف PDF',
    '📝 Final quiz ': '📝 الاختبار النهائي', '+ Add a question': '+ إضافة سؤال', 'Question *': 'السؤال *', 'Answers (one per line, 2–6)': 'الإجابات (سطر لكل إجابة، 2–6)',
    'Number of the right answer': 'رقم الإجابة الصحيحة', 'Add question': 'إضافة السؤال', 'Question added': 'تمت إضافة السؤال', 'Question removed': 'تم حذف السؤال', 'Write the question': 'اكتب السؤال',
    'Give 2 to 6 answers, one per line': 'اكتب من 2 إلى 6 إجابات، سطر لكل إجابة', 'The right answer must be one of the answers': 'الإجابة الصحيحة يجب أن تكون إحدى الإجابات',
    'No questions yet — without a quiz, finishing the lessons completes the course.': 'لا توجد أسئلة بعد — بدون اختبار، إنهاء الدروس يكمل الدورة.', 'Only the Drugbox team manages courses': 'فريق Drugbox فقط يدير الدورات'
  }, [
    [/^👥 ([\d,]+) enrolled$/, function (m) { return '👥 ' + m[1] + ' متدرب'; }], [/^([\d,]+) enrolled$/, function (m) { return m[1] + ' مسجلاً'; }],   /* the card says learners, not "enrolled" (that is your own state) */
    [/^(\d+) \/ (\d+) lessons · (\d+)%(.*)$/, function (m) { return m[1] + ' / ' + m[2] + ' دروس · ' + m[3] + '%' + (m[4] ? m[4].replace('Completed', 'مكتملة') : ''); }],
    [/^📚 My courses \((\d+)\)$/, function (m) { return '📚 دوراتي (' + m[1] + ')'; }],
    [/^Lesson (\d+): (.+)$/, function (m) { return 'الدرس ' + m[1] + ': ' + m[2]; }], [/^Lesson (\d+)$/, function (m) { return 'الدرس ' + m[1]; }],
    [/^Lesson (\d+) complete$/, function (m) { return 'أنجزت الدرس ' + m[1]; }], [/^(\d+) min$/, function (m) { return m[1] + ' دقيقة'; }], [/^(🎬|📄|📖) (\d+) min$/, function (m) { return m[1] + ' ' + m[2] + ' دقيقة'; }],
    [/^Final quiz: (.+)$/, function (m) { return 'الاختبار النهائي: ' + m[1]; }], [/^🔒 Pay (.+)$/, function (m) { return '🔒 ادفع ' + m[1]; }],
    [/^Enrolled in (.+)!$/, function (m) { return 'تم تسجيلك في ' + m[1] + '!'; }], [/^You left (.+)$/, function (m) { return 'ألغيت تسجيلك في ' + m[1]; }],
    [/^Payment received — you can start (.+) now$/, function (m) { return 'تم استلام الدفع — يمكنك بدء ' + m[1] + ' الآن'; }],
    [/^Payment received — you can start "(.+)" now$/, function (m) { return 'تم استلام الدفع — يمكنك بدء "' + m[1] + '" الآن'; }],
    [/^Your certificate for "(.+)" is ready$/, function (m) { return 'شهادتك لدورة "' + m[1] + '" جاهزة'; }],
    [/^Finish all the lessons first \((\d+) of (\d+) done\)$/, function (m) { return 'أنهِ كل الدروس أولاً (' + m[1] + ' من ' + m[2] + ')'; }],
    [/^(\d+) hours$/, function (m) { return m[1] + ' ساعات'; }], [/^⏱ (\d+(?:\.\d)?) hours$/, function (m) { return '⏱ ' + m[1] + ' ساعات'; }]
  ]);
})();
