// The page of «الفحص الأول للملف»: its title and body (prep/build.mjs puts them together with its style and script).
export const TITLE = 'الفحص الأول للملف';

export const BODY = `<div class="page" dir="rtl" lang="ar">
<header>
  <h1>الفحص الأول للملف</h1>
  <p>اختار ملفات المستحضر، أو الفولدر كله. البرنامج بيفتح كل ملف ويعرف نوعه من محتواه مش من اسمه، ويحدد مكانه في الـ CTD، وبعدين بيقارن المستندات ببعض. كل ملاحظة معاها الكلام اللي في صفحتها. الملفات بتتقري على جهازك، ومابتتبعتش لأي حد.</p>
</header>
<section class="box" aria-labelledby="files-h">
  <h2 id="files-h">ملفات المستحضر</h2>
  <div class="drop" id="drop" tabindex="0">
    <p class="drop-text">اسحب الملفات أو الفولدر هنا</p>
    <div class="row center">
      <label class="btn"><input type="file" id="pick-files" multiple>اختار ملفات</label>
      <label class="btn quiet"><input type="file" id="pick-folder" webkitdirectory multiple>اختار فولدر</label>
    </div>
    <p class="fine">بيقرا: PDF فيه نص أو ممسوح، Word القديم (.doc) والجديد (.docx)، الصور الممسوحة، والملفات اللي جوه ZIP و RAR.</p>
  </div>
  <div class="status" id="status" role="status" aria-live="polite" hidden></div>
  <div class="bar" id="bar" hidden><span id="bar-fill"></span></div>
</section>
<section class="box" id="summary-box" aria-labelledby="summary-h" hidden>
  <h2 id="summary-h">النتيجة <small id="summary-when"></small></h2>
  <div class="tiles" id="summary"></div>
</section>
<section class="box" id="findings-box" aria-labelledby="findings-h" hidden>
  <h2 id="findings-h">الملاحظات <small>من قراية المستندات جنب بعض</small></h2>
  <ol class="findings" id="findings"></ol>
  <p class="empty" id="findings-empty" hidden>مالقيتش ملاحظة من الحاجات اللي بيقارنها الفحص ده: المصنع، الحدود اللي اتوافق عليها، صور المادة الواحدة، المواعيد، وشروط الإخطار.</p>
</section>
<section class="box" id="docs-box" aria-labelledby="docs-h" hidden>
  <h2 id="docs-h">المستندات <small>نوع كل واحد ومكانه، واللي اتقرا منه</small></h2>
  <ul class="docs" id="docs"></ul>
</section>
<p class="fine foot">الفحص ده بيقارن المستندات ببعض بقواعد ثابتة، ومابيستخدمش Claude. الصفحة الممسوحة بيقراها قارئ المسح جوه المتصفح، وأول مرة بيحمّل حوالي 35 م.ب. لو حاجة اتقرت غلط هتلاقيها قدامك بكلامها، فتقدر تتأكد منها بنفسك.</p>
</div>`;
