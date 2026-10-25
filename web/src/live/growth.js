/* AREA w-growth — window.dxGrowth: the live services web/src/growth.js draws with (migrations 0100–0104). The database decides
   every permission (Drugbox admins plan channel posts, make invitations, schedule sessions, import companies; members join, register,
   ask); nothing here trusts the browser. Loaded after the adapter (web/build/live.py: src/live/*.js in name order). */
(function () {
  var L = window.dxLive; if (!L || !L.sb) return;
  var sb = L.sb, G = function () { return L.gw || {}; };
  function me() { return G().me || null; }
  function ok(r) { if (r.error) throw new Error(L.friendly ? L.friendly(r.error) : r.error.message); return r.data; }
  function uuidOfLocal(id) { return id === (window.ME || {}).id ? me() : (L.uuidOf ? L.uuidOf(id) : null); }
  var COURSE_AR = null;

  window.dxGrowth = {
    live: true,
    ready: function () { return !!me(); },
    guest: function (on) { if (G().guest) G().guest(on); },
    signedOut: function () { return G().signedOut ? G().signedOut() : false; },
    feedThera: function (tag) { return G().feedThera(tag); },
    marketThera: function (tag) { return G().marketThera(tag).catch(function (e) { window.DBK.toast(e.message || 'Could not load the listings'); }); },

    channels: {
      templates: async function () { return ok(await sb.from('channel_templates').select('*').order('sort')) || []; },
      next: async function (key) { return ok(await sb.rpc('channel_template_next', { p_key: key })); },
      list: async function () { return ok(await sb.rpc('channel_schedule_list', { p_limit: 200 })) || []; },
      save: async function (o) { return ok(await sb.rpc('channel_schedule_save', { p_id: o.id || null, p_channel: o.channel, p_body: o.body, p_local: o.local || null, p_status: o.status, p_thera: o.thera || [], p_template: o.template || null })); },
      cancel: async function (id) { ok(await sb.rpc('channel_schedule_cancel', { p_id: +id })); },
      publishNow: async function (id) { return ok(await sb.rpc('channel_publish_now', { p_id: +id })); }
    },

    founders: {
      overview: async function () { return ok(await sb.rpc('founder_overview')) || []; },
      create: async function (seg, note, days) { return ok(await sb.rpc('founder_invite_create', { p_segment: seg, p_note: note || null, p_days: days || 60 })); },
      list: async function () { return ok(await sb.rpc('founder_invites_list', { p_limit: 300 })) || []; },
      revoke: async function (id) { ok(await sb.rpc('founder_invite_revoke', { p_id: +id })); },
      quota: async function (seg, n) { ok(await sb.rpc('founder_segment_quota', { p_segment: seg, p_quota: +n })); },
      peek: async function (code) { return ok(await sb.rpc('founder_invite_peek', { p_code: code })); },
      redeem: async function (code, companyId) { return ok(await sb.rpc('founder_redeem', { p_code: code, p_company: companyId ? +companyId : null })); },
      my: async function () { var m = ok(await sb.rpc('my_founder')); return m ? { segment: m.segment, joined_at: m.joined_at, vip_open: !!m.vip_open, vip_company: m.vip_company_id } : null; },
      applyVip: async function (companyId) { return ok(await sb.rpc('founder_apply_vip', { p_company: +companyId })); },
      /* the company pages I run (owner / admin) — the database checks it again when the months are given */
      myCompanies: async function () {
        var r = ok(await sb.from('company_members').select('role, co:companies(id, name)').eq('user_id', me()).eq('accepted', true).in('role', ['owner', 'admin']));
        return (r || []).filter(function (x) { return x.co; }).map(function (x) { return { id: x.co.id, name: x.co.name }; });
      },
      isFounder: async function (localId) { var u = uuidOfLocal(localId); if (!u) return false; var r = ok(await sb.from('founder_members').select('user_id').eq('user_id', u).limit(1)); return (r || []).length > 0; }
    },

    experts: {
      sessions: async function () { return ok(await sb.rpc('expert_sessions_list', { p_limit: 60 })) || []; },
      questions: async function (id) {
        var r = ok(await sb.from('expert_questions').select('id, body, answer, created_at, user_id, who:profiles!expert_questions_user_id_fkey(name)').eq('session_id', +id).order('created_at').limit(200));
        return (r || []).map(function (q) { return { id: q.id, body: q.body, answer: q.answer, who: q.who ? q.who.name : 'Member', mine: q.user_id === me() }; });
      },
      demand: async function () { return ok(await sb.rpc('expert_topic_demand')) || []; },
      request: async function (topic, note) { ok(await sb.from('expert_requests').insert({ topic: topic, note: note || null })); },
      withdraw: async function (topic) { ok(await sb.from('expert_requests').delete().eq('topic', topic).eq('user_id', me())); },
      register: async function (id) { ok(await sb.from('expert_registrations').insert({ session_id: +id })); },
      unregister: async function (id) { ok(await sb.from('expert_registrations').delete().eq('session_id', +id).eq('user_id', me())); },
      link: async function (id) { return ok(await sb.rpc('expert_session_link', { p_id: +id })); },
      ask: async function (id, body) { body = String(body || '').trim(); if (body.length < 5) throw new Error('Write your question (at least 5 characters)'); ok(await sb.from('expert_questions').insert({ session_id: +id, body: body })); },
      adminRequests: async function () { return ok(await sb.rpc('expert_requests_admin')) || []; },
      save: async function (o) { return ok(await sb.rpc('expert_session_save', { p_id: o.id || null, p_topic: o.topic, p_title: o.title, p_title_ar: o.title_ar || null, p_about: o.about || null,
        p_expert_name: o.expert_name, p_expert_line: o.expert_line || null, p_local: o.local, p_minutes: +o.minutes || 60, p_seats: +o.seats || 100, p_join_url: o.link || null, p_expert_user: null })); },
      status: async function (id, st) { ok(await sb.rpc('expert_session_set_status', { p_id: +id, p_status: st })); },
      answer: async function (qid, text) { ok(await sb.rpc('expert_answer', { p_question: +qid, p_answer: text })); },
      full: async function (id) {
        var list = await window.dxGrowth.experts.sessions(), s = list.filter(function (x) { return +x.id === +id; })[0]; if (!s) return null;
        var link = null; try { link = await window.dxGrowth.experts.link(id); } catch (e) {}
        return Object.assign({}, s, { join_url: link });
      }
    },

    directory: {
      run: async function (rows, dry) {
        var out = null;   /* 2,000 rows per call (the database's limit); a bigger file in parts */
        for (var i = 0; i < rows.length; i += 2000) {
          var r = ok(await sb.rpc('admin_import_companies', { p_rows: rows.slice(i, i + 2000), p_dry_run: !!dry }));
          (r.results || []).forEach(function (x) { x.row += i; });
          if (!out) out = r; else { out.rows += r.rows; out.created += r.created; out.duplicates += r.duplicates; out.invalid += r.invalid; out.results = out.results.concat(r.results || []); }
        }
        (out.results || []).forEach(function (x) { if (x.status === 'duplicate' && x.slug) x.of = x.slug; });
        return out;
      }
    },

    /* the six courses' Arabic titles from the database (0104), by their English title */
    coursesAr: function () {
      if (COURSE_AR === null) { COURSE_AR = {}; sb.from('training_courses').select('title, title_ar, description_ar').not('title_ar', 'is', null).limit(200).then(function (r) {
        (r.data || []).forEach(function (c) { COURSE_AR[c.title] = [c.title_ar, c.description_ar || '']; }); }); }
      return COURSE_AR;
    },
    specialtyDue: async function () { return !!ok(await sb.rpc('specialty_prompt_due')); },
    specialtyAnswer: async function (h) { return ok(await sb.rpc('specialty_answer', { p_headline: h || null })); }
  };
})();
