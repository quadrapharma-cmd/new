/* Profile → Activity shows the person's posts as full post cards (the same renderPost the Home feed uses):
   author, full text, images, files, category, reactions, comments, share and save. Other tabs are unchanged. */
(function () {
  var C = window.dxCore; if (!C || typeof window.renderProfileTab !== 'function' || typeof window.renderPost !== 'function') return;
  var orig = window.renderProfileTab;
  window.renderProfileTab = function (tab) {
    if (tab !== 'activity') return orig.apply(this, arguments);
    try {
      var u = window._profUser || window.ME || {}, uid = u.id, posts = (window.POSTS || []).filter(function (p) { return p.uid === uid; });   /* live list: includes posts published after the profile opened */
      window._profPosts = posts;
      var own = !window._profUser || uid === (window.ME || {}).id;
      var comp = own && typeof window.renderComposer === 'function' ? '<div class="dx-pp-comp">' + window.renderComposer() + '</div>' : '';
      if (!posts.length) return comp ? comp + '<div class="dx-pp-empty">You haven’t posted yet — share an update, a product or a job with your network.</div>' : orig.apply(this, arguments);
      var head = '<div class="dx-pp-h"><b>Posts</b><span>' + posts.length + (posts.length === 1 ? ' post' : ' posts') + '</span></div>';
      return comp + head + '<div class="dx-pp">' + posts.map(function (p) { try { return window.renderPost(p); } catch (e) { return ''; } }).join('') + '</div>';
    } catch (e) { return orig.apply(this, arguments); }   /* any problem → the original view, never a blank tab */
  };


  /* composer greeting: the name after a title (Dr., Eng., Prof.) or the first word — never "undefined" */
  function greetName(n) { var p = String(n || '').trim().split(/\s+/); if (p.length > 1 && /^(dr|eng|prof|pharm|mr|mrs|ms)\.?$/i.test(p[0])) return p[1]; return p[0] || ''; }
  var oc = window.renderComposer;
  if (typeof oc === 'function') window.renderComposer = function () {
    var h = oc.apply(this, arguments), g = greetName((window.ME || {}).name);
    return h.replace(/What(&#39;|')s on your mind, [^?<]*\?/, "What's on your mind, " + (window.esc ? window.esc(g) : g) + '?');
  };
  function ownProfile() { var u = window._profUser; return !u || u.id === (window.ME || {}).id; }
  window.dxProfPostsRefresh = function () {
    if (document.body.getAttribute('data-page') !== 'profile') return;
    var box = document.getElementById('profileTabContent'), act = document.querySelector('.ptab.active');
    if (box && act && act.dataset.tab === 'activity') box.innerHTML = window.renderProfileTab('activity');
  };
  /* publishing from your own profile keeps you on it; the new post appears at the top */
  var os = window.submitPost;
  if (typeof os === 'function') window.submitPost = function () {
    var onProf = document.body.getAttribute('data-page') === 'profile' && ownProfile(), before = (window.POSTS || []).length;
    var r = os.apply(this, arguments);
    if (onProf && (window.POSTS || []).length > before) {
      if (document.body.getAttribute('data-page') !== 'profile' && typeof window.goto === 'function') window.goto('profile');
      window.dxProfPostsRefresh();
    }
    return r;
  };

  /* each tab's content sits right under the tabs; profile-wide sections (certificate wall, insights, my companies) follow it */
  function arrange() {
    if (document.body.getAttribute('data-page') !== 'profile') return;
    var box = document.getElementById('profileTabContent'); if (!box || !box.parentElement) return;
    var after = box;
    ['.dx-certwall', '.dx-insights', '.dx-mycos'].forEach(function (sel) {
      var el = document.querySelector('#content ' + sel); if (!el || el === box || el.contains(box)) return;
      if (el.parentElement !== box.parentElement || (box.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_PRECEDING)) box.parentElement.insertBefore(el, after.nextSibling);
      after = el;
    });
  }
  C.onRender('profile-order', function () { arrange(); setTimeout(arrange, 450); setTimeout(arrange, 1000); });

  /* the page opens on Activity: redraw it once with full cards */
  C.onRender('profile-posts', function () {
    if (document.body.getAttribute('data-page') !== 'profile') return;
    var box = document.getElementById('profileTabContent'), act = document.querySelector('.ptab.active');
    if (!box || !act || act.dataset.tab !== 'activity' || box.dataset.pp === '1') return;
    box.dataset.pp = '1'; box.innerHTML = window.renderProfileTab('activity');
  });
})();
