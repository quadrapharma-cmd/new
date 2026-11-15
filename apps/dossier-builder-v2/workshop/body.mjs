// The workshop page's shell: the top bar, the view, the drawer (a place's rule card, a draft), the settings dialog, the toast.
export const TITLE = 'تحضير الملف — Dossier Builder';
export const BODY = `<div dir="rtl" lang="ar">
<header class="top">
  <div class="brand">تحضير الملف <small id="top-name"></small></div>
  <nav>
    <button class="btn small quiet" data-act="home">ملفاتي</button>
    <button class="btn small quiet" id="save-copy" data-act="save-copy" hidden>احفظ نسخة</button>
    <a class="btn small quiet" href="library/index.html" target="_blank" rel="noopener">المكتبة</a>
    <button class="btn small quiet" id="claude-chip" data-act="settings">Claude</button>
    <button class="btn small quiet" data-act="settings">الإعدادات</button>
  </nav>
</header>
<main id="view" class="wrap"><p class="empty">بيفتح…</p></main>
<aside id="drawer" class="drawer" hidden aria-label="التفاصيل"></aside>
<div id="program" class="program" hidden role="dialog" aria-label="البرنامج">
  <div class="program-bar"><b id="program-title"></b><span id="program-note" class="fine"></span><button class="btn small quiet" id="program-place" data-act="program-place" hidden>حط الملف في التصميم</button><button class="btn small" data-act="program-close">اقفل البرنامج</button></div>
  <div id="program-frames"></div>
</div>
<dialog id="settings"><div class="dlg" id="settings-body"></div></dialog>
<div id="toast" class="toast" role="status" aria-live="polite" hidden></div>
<noscript>الصفحة دي محتاجة JavaScript.</noscript>
</div>`;
