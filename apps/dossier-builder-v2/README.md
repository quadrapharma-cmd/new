# Dossier Builder v2 — البرنامج من جديد

مكان الشغل الجديد. البرنامج القديم فاضل زي ما هو في `apps/dossier-builder/`، ومحدش هيلمسه.

## طريقة الشغل
- البرنامج هيتبني **جزء جزء**، حسب خطة صاحب البرنامج.
- كل جزء بيتعمل ويتجرّب، ومش هنبدأ الجزء اللي بعده غير لما يتأكد إنه شغال.
- أي حاجة هتتنقل من البرنامج القديم هتتنقل لما الخطة تطلبها بس.

## الأجزاء

| # | الجزء | الحالة |
|---|---|---|
| 1a | المعرفة في الكود: كل الهيئات، وكل سجل مربوط بمصدره (`knowledge/`) | اتعمل واتجرّب |
| 1b | المكتبة: تصفّح وبحث بالعربي والإنجليزي، في المتصفح وعلى الكمبيوتر (`library/`) | اتعملت واتجرّبت |
| 1c | مراجعة كل سجل على مصدره الرسمي (النص، والإصدار الأحدث) | اتعملت لمصادر الهيئة، ولسه مراجعة إصدارات ICH وEMA وFDA ومنظمة الصحة والخليج أونلاين |

```
npm install        # once
npm run build      # checks every record; writes dist/knowledge.json and the library (dist/library/ and its zip)
npm run verify     # checks every citation against the text of its source (knowledge/checks/citations.json)
npm test           # the knowledge tests and the library in a real browser
```

البحث في المكتبة: خانة واحدة بتدوّر في المعرفة كلها وجوه نص المستندات، بالعربي والإنجليزي («ذوبان» بتلاقي dissolution)، وكل نتيجة
في مستند بتفتحه على صفحتها. نصوص المستندات بيطلّعها `npm run verify` (في `dist/texts/`) قبل `npm run build`.
Search: one box looks through all the knowledge and inside the documents' text, in Arabic and English, and each page found opens
at that page. The texts come from `npm run verify` (in `dist/texts/`), so run it before `npm run build`.

المكتبة على الكمبيوتر: فك `dist/Dossier-Builder-Library.zip` وافتح `index.html` (شغالة من غير إنترنت، والمستندات جنبها في `sources/`).
The library on the desktop: unzip `dist/Dossier-Builder-Library.zip` and open `index.html` (works offline; the source documents
it opens are beside it in `sources/`). The same page, without its document shell (`dist/library-artifact.html`), is the
claude.ai artifact, published with the same `sources/` files.

---

# Dossier Builder v2 — the program anew

The new workspace. The old program stays as it is in `apps/dossier-builder/`, untouched.

## How it is built
- **One part at a time**, following the owner's plan.
- Each part is built and tested. The next part starts only after the current one is confirmed working.
- Nothing is carried over from the old program unless the plan asks for it.

## Parts
| # | Part | State |
|---|---|---|
| 1a | Knowledge in code: every authority, every record tied to its source (`knowledge/`) | built and tested |
| 1b | The library: browse and search in Arabic and English, in the browser and on the desktop (`library/`) | built and tested |
| 1c | Review every record against its official source (the text, and the latest version) | done for EDA's sources; the online version check of ICH, EMA, FDA, WHO and GCC sources is open |
