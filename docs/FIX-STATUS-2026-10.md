# حالة الإصلاحات بعد مراجعة أكتوبر 2026

مكمّل لـ `docs/CODE-REVIEW-2026-10.md` (البنود F-01 … F-178). الملف ده بيقول كل بند حصله إيه، اتصلح فين، واتحقق منه إزاي. المصادر: الجولة الأولى (الـ workstreams DB1–DB4، INFRA، UI1–UI3، DBINT، ADAPTER، UIFOLLOW، والـ gates من G1 لـ G6، وتلات شرايح تحقق مستقل V-db وV-web وV-perf-ui)، والجولة التانية (r2-db، r2-adapter، r2-infra، r2-ui، والـ gates R2-G1 وR2-G2، وشريحة التحقق المستقل R2-V2)، والجولة التالتة (r3-db، r3-ui، والـ gate R3، وشريحة التحقق المستقل V3). آخر commit اتجرب عليه: `e3c3dde`.

## 1. الخلاصة

- **اتقفل 167 بند من 178**، و8 جزئي، و2 متأجلين (F-45، F-172)، و1 ملاحظة قياس (F-162). الجولة التالتة (migration `0025` وتعديلات صغيرة في الواجهة) قفلت F-70 وF-74، وقفلت المشاكل الأربعة اللي طلعت في تحقق الجولة التانية (N-7، N-8، N-9، N-10). الستة اتجربوا بشكل مستقل (V3) بهجمات وقياسات حقيقية على `e3c3dde`، والحكم في الستة: اتقفل.
- **كل اللي كان لازم يتقفل قبل production اتقفل:** Fawry مبقاش ممكن يدفع طلب غير اللي اتوقّع، لا من الـ webhook ولا من الداتابيز مباشرة (F-115). `my_interactions()` رجعت 6–9 ms عند 20k صفقة بدل 116–183 ms (N-1). الدليل في الـ live بقى بيجيب أول 100 شركة بس: request واحد بـ 59 KB عند 838 شركة، و163 KB عند 5k، بدل 26 request و8.3 MB (F-05). الدعوة للجروب الخاص شغالة من الواجهة (F-29). والـ build بيمسح ملفات الـ live القديمة لوحده (N-3).
- **الأمان والخصوصية:** الـ anon key مبقاش بيقرا أي محتوى (posts، jobs، products، groups…). العام بس الأسعار والإعدادات والـ ticker والكورسات (F-26، قرار privacy-first وممكن يترجع). ومستندات الشركات (CEP وDMF وISO…) بقت للمسجّلين بس، فالـ anon بياخد 0 صف (N-7). owner الشركة يقدر يمسح حسابه، والصفحة بتفضل "unclaimed" بتاريخها وصفقاتها (F-17). الشركة مبقتش تقدر تقفل البلاغ اللي عليها ولا تعرف مين بلّغ (F-32). الريفيو بقى بشرط علاقة حقيقية (F-10). وأدمن Drugbox يقدر يوثّق الأشخاص من الـ API (N-4).
- **الجروبات والشركات:** المدعو لجروب خاص بيجيله إشعار `group_invite` بالإنجليزي أو العربي، وبيتشال لو الدعوة اتسحبت (N-8). شباك إنشاء الجروب والدعوة والـ toasts بقوا عربي كامل بصيغ الجمع الصح (N-9). والكليك على اسم شخص بيفتح صاحب الاسم بالظبط (N-10). ولو شركتين بنفس الاسم اتعملوا في نفس اللحظة، الداتابيز بتدّي التانية عنوان بـ "-2" بدل خطأ (F-74).
- **السرعة:** الـ live `index.html` نزل من 3.41 MB لـ 0.60 MB، لأن الـ scripts بقت ملفات `js/` بالـ hash وimmutable. وعلى Slow 4G أول paint بقى 2.75 ث بدل 5.3 ث، والزيارة التانية بتبقى جاهزة في 4.9 ث (F-71). الخطوط (Google Fonts) بقت بتتطلب بعد ما الصفحة تحمّل: لو سيرفر الخطوط معلّق، الـ load event بقى حوالي 0.5 ث بدل 6–30 ث، وoffline مفيش ولا طلب (F-70). في الديمو، render الدليل بـ 300 review نزل من 204–374 ms لـ 28–38 ms (F-25). وتبديل الصفحات median 17.0 ms مقابل 16.5 ms للبناء اللي قبل الجولة التالتة، في حدود القاعدة.
- **الاختبارات كلها خضرا:** 35 / 35 suite: `sql sweep demo` 14 / 14، والـ e2e 21 / 21 مرتين على stack اتقام من الأول. ومعاها `migration_check` OK للـ 25 migration، والـ build deterministic (مرتين نفس الـ sha)، وPARITY OK، والـ stress PASS.
- **جاهزية E5:** مفيش بند كود موقّف للإطلاق. اللي فاضل قرارات منك، وحاجات ما تتجربش غير على Supabase حقيقي (F-04 بالـ k6، وF-78 وF-81)، والمتأجلين F-45 وF-172، وذيول صغيرة منخفضة الخطورة، منها أربعة جداد من تحقق الجولة التالتة (N-11 لـ N-14)، كلهم في القسم 5.
- **محتاج منك:** (1) توافق على تغييرات الواجهة في القسم 6، ومنها الجديد في الجولة دي (عربي شاشات الجروبات ورسايل الفورم، 28–33). (2) تأكد قرار الخصوصية (F-26، ومعاه مستندات الشركات N-7). (3) تقرر في اسم "Dr. Asmaa Meabed". (4) تبعت مفاتيح Paymob وFawry وعنوان InstaPay. (5) تأكد أسعار الـ boost والـ featured. (6) تقرر في F-34 وF-107 وN-6.
- الملف المستقل `web/dist/drugbox.html` هو نفس المرجع المعتمد الجديد: sha256 `d7709969…ebde76d2`، حجمه 5,518,727 byte.

## 2. نتيجة الاختبارات النهائية (الجولة التالتة)

R3-gate دمج شغل الجولة التالتة (`0025_small_followups.sql` و`small_followups.rls.sql`، والتعديلات في `app.html` و`afford.js` و`i18n.js`) وعمل commit `e3c3dde`. الفحص بالصور لشاشات الجروبات بالعربي طلّع نصوص لسه إنجليزي: رسايل الفورم زي "Email is required"، وشباك Create a Group، و"Manage Group" و"DISCUSSION" و"NEW"، وإشعار الدعوة الجديد بتاع 0025. كلهم اتزوّدوا في `i18n.js`، واتزوّدت 3 فحوص لـ `d3_groups` على إشعار الدعوة. وبعدها:

- الـ build اتعمل مرتين وطلع نفس الـ sha، والمرجع اتعمله refresh، وPARITY OK.
- `run_all sql sweep demo`: **14 / 14**، وكل SQL suite اشتغلت على داتابيز جديدة من الـ stub + 0001..0025.
- الـ stack المشترك اتقام من الأول مرتين (start.sh ودوال الدفع والـ fixtures)، والـ e2e طلعت **21 / 21** في المرتين: مرة قبل آخر تعديل في القاموس، ومرة على البناء النهائي.
- الديمو 4 / 4 والـ stress A/B PASS على البناء النهائي.

V3 بنى الديمو تاني من `e3c3dde` وطلع نفس الـ sha، يعني اللي اتجرب هو اللي اتسلّم.

| المجموعة | Suite | النتيجة |
|---|---|---|
| sql | `company_hub.rls.sql` | 35 / 35 |
| sql | `deals.rls.sql` | 23 / 23 |
| sql | `followups.rls.sql` (بيفحص 0024) | 68 / 68 |
| sql | `integrity_perf.sql` | 56 / 56 |
| sql | `listings_groups.rls.sql` | 23 / 23 |
| sql | `payments_storage.rls.sql` | 76 / 76 |
| sql | `security_core.rls.sql` | 96 / 96 |
| sql | `small_followups.rls.sql` (جديد، بيفحص 0025) | 33 / 33 |
| sql | `trust_hub_deals.rls.sql` | 143 / 143 |
| sweep | `schema_sweep.sql` (6 سطور كلها none) | 6 / 6 |
| demo | `profile_composer_test.py` en / ar | 11 / 11 · 11 / 11 |
| demo | `videos_test.py` en / ar | 15 / 15 · 15 / 15 |
| e2e | b0_rtl_smoke | 7 / 7 |
| e2e | b1_auth | 19 / 19 |
| e2e | b2_feed | 18 / 18 |
| e2e | b2b_profile_post | 6 / 6 |
| e2e | b3_network | 20 / 20 |
| e2e | b4_messages | 20 / 20 |
| e2e | c1_companies (ومعاها فحوص الـ paging) | 25 / 25 |
| e2e | c2_deals | 16 / 16 |
| e2e | c3_listings | 14 / 14 |
| e2e | d1_market | 17 / 17 |
| e2e | d2a_jobs | 14 / 14 |
| e2e | d2b_trust | 14 / 14 |
| e2e | d3_groups (ومعاها الدعوة للجروب الخاص وإشعارها بالعربي) | 27 / 27 |
| e2e | e1a_follow | 5 / 5 |
| e2e | e1a_uploads | 12 / 12 |
| e2e | e1b_documents | 13 / 13 |
| e2e | e2_review (ومعاها البلاغات من `company_reports_received`) | 16 / 16 |
| e2e | e3_training | 10 / 10 |
| e2e | e4_payments (دوال Deno حقيقية + بديل Paymob/Fawry) | 26 / 26 |
| e2e | e4b_checkout | 14 / 14 |
| e2e | video_live | 14 / 14 |
| **المجموع** | **run_all** (`sql sweep demo` + `e2e`) | **35 / 35 suite** |
| جروبات (R3-gate) | `t_groups.py`: إنشاء ودعوة بالإنجليزي والعربي، وN-10 | 19 / 19، ومعاها صور: شباك الإنشاء، والكارت الجديد، وشباك الدعوة، وخطأ الدخول |
| legacy + stress (R3-UI) | `run_all.py demo demo-full` على بناء R3-UI | 27 / 27 (الـ demo 4، والـ legacy 22، والـ stress A/B) |
| migrations (R3-gate) | `tools/migration_check.py` | OK للـ 25 migration (0001 مش re-runnable زي المتوقع) |
| build (R3-gate) | build.py مرتين | نفس الملف بالظبط |
| parity | `tools/parity_check.py web/reference/demo-approved.html web/dist/drugbox.html` | **PARITY OK** (sha256 d77099694403fd80) |
| الملف المسلَّم | `web/dist/drugbox.html` = `web/reference/demo-approved.html` | sha256 `d77099694403fd80a22644d2a87d6539cf832e1540ef8a64038b1043ebde76d2` · 5,518,727 byte |
| السرعة (R3-gate) | `stress_base.py` على بناء ما قبل الجولة التالتة ضد `stress.py` على الجديد | median 17.0 ms مقابل 16.5 ms (جولات [14.8، 18.4، 17.0] مقابل [16.5، 17.2، 15.8]). R3-UI قاس إن ناحية `stress.py` أبطأ حوالي 0.7 ms حتى لو نفس البناء على الناحيتين، فده في حدود الضوضاء |

**اللي ما اتشغلش هنا:** الـ legacy suites ما اتعادتش في الـ gate نفسه. R3-UI شغّلها على بنائه (27 / 27)، والـ gate بعدها غيّر مداخل في القاموس بس. `rtl_scroll.py` و`data_audit.py` محتاجين WebKit ومش متسطّب. الـ Realtime ما ينفعش يتجرب غير على Supabase حقيقي. والـ k6 load test مستنيه E5.


## 3. التحقق المستقل

### 3.1 الجولة الأولى

تلات شرايح تحقق (V-db، V-web، V-perf-ui) اشتغلت بعد الـ gates على 60 بند (كل الـ critical والـ high وأهم المتوسط)، بحسابات جديدة وهجمات حقيقية، من غير ما تعدّل في الريبو. النتيجة: **43 اتقفلوا و17 اتقفلوا جزئيًا**. لما التحقق يخالف كلام الـ workstream، المعتمد هو التحقق.

| ID | الحكم | الشريحة | الدليل |
|---|---|---|---|
| F-01 | اتقفل | V-db | `PATCH profiles` بـ role=admin / verified=true على صفّي ← 403 42501 والصف فضل user/false؛ شركة بـ status=verified/plan=vip اتخزنت pending/free؛ `review_instapay` لنفسي ← 42501. |
| F-02 | اتقفل | V-web | حسابين: المهاجم كتب payloads في avatar_url/headline/bio/website/logo_url/cover/phone/post_media/enquiries.flag؛ الضحية فتحت الـ feed والكومنتات والـ lightbox والدليل وصفحة الشركة والماركت والبروفايل والوظايف والبحث والاتصال ← `window.__pwned` فضل null ومفيش on* ولا javascript:. |
| F-03 | اتقفل | V-db | `POST products` بـ boosted_until/featured_until=2099 ← 201 والعمودين null؛ PATCH وupsert برضه null؛ التفعيل من `activate_order` بس. |
| F-04 | اتقفل جزئيًا | V-perf-ui | `GET /deals` عند 20k deal: median 33–40 ms (كان 2,400 ms، حوالي 60×)، Index Scan من غير JIT. ما وصلش هدف ≤ 25 ms (أحسن قراءة 27.5 ms والجهاز عليه Chromium تاني). |
| F-05 | اتقفل جزئيًا | V-perf-ui | `directory_companies_page(100)` = 167 KB في 29–55 ms، anon اتقفل، والـ sign-in مبقاش بيحمّل الدليل. باقي: الـ adapter بيجيب 200 في الصفحة (334 KB) ويلف لحد آخر شركة: 26 request و8.3 MB عند 5k شركة مع كل فتح لـ Companies/Market. |
| F-06 | اتقفل | V-web | 3 إعلانات اتدفعت بالمسار الحقيقي (create_order ← confirm_payment): الترتيب featured ثم boost ثم الجديد، والـ featured ملا الكارت الـ sponsored. ملاحظة: مفيش علامة "Boosted" ظاهرة على الكارت. |
| F-07 | اتقفل | V-web | شباك الـ boost: EGP 1,450 + 203 = 1,653 والـ featured 3,950 + 553 = 4,503 بالإنجليزي والعربي، مطابق لـ payment_products وcreate_order؛ مفيش طلب لـ exchangerate.host. |
| F-08 | اتقفل | V-db | connection بـ accepted اتخزن pending؛ الـ requester ما يقدرش يقبل لنفسه؛ تغيير الـ requester ← 42501؛ A→B وB→A بيبقوا صف واحد. |
| F-09 | اتقفل | V-db | بوست بـ created_at 2099 وpinned وlike_count 99999 اتخزن now()/false/0؛ رسالة بـ id ضخم وread_at اتخزنت بالـ sequence وnull. ذيل بلا أثر: id أصغر من الـ sequence لسه مقبول. |
| F-10 | اتقفل جزئيًا | V-db | الـ repro الأصلي اتقفل (رسالة واحدة ← review = 403). باقي: متقدّم لوظيفة E يقدر يكتب review لـ E بدور candidate من غير ما يكون شغّله (`can_review` بيشوف إن E candidate وبس) — تأثير قليل (review واحد لكل زوج وموقّع). |
| F-11 | اتقفل | V-db | profile.company='%%' ← 42501؛ HR شركة موثّقة عن حد ما ذكرش الشركة ← مرفوض؛ evidence_path وهمي ← 23514؛ الحالات السليمة شغالة. |
| F-12 | اتقفل | V-db | anon `rpc/jobs_interacted` ← 401؛ طرف تالت بيسأل عن A,B ← false؛ `has_real_interaction` مقفولة؛ `increment_*` لـ anon ← 401. |
| F-13 | اتقفل | V-db | شهادة بـ site_id بتاع منافس ← 23503 على الـ composite FK؛ نقل شهادة لموقع منافس نفس الرفض؛ source=public_list بيتحول company. |
| F-14 | اتقفل | V-db | تعديل نوع/منتج/expiry لمستند verified ← رجع declared؛ إرجاعه verified بإيدك ← 42501. |
| F-15 | اتقفل | V-db | عضو HR عمل RFQ واتشال من الفريق ← `deal_act` accept/cancel ← 42501 والصفقة مبقتش ظاهرة له؛ الـ owner الحالي بيقبل عادي. |
| F-16 | اتقفل | V-db | `deal_join` بـ NaN / -Infinity / 1e30 ← 22023 والجروب فضل مفتوح؛ validity 99999999999 يوم أو 0 ← 22023؛ join عند حد 1e9 بيكمل عادي. |
| F-17 | اتقفل جزئيًا | V-db | مسح بوست عليه like، وكومنت عليه رد، وحسابات عادية بقى شغال. باقي: مسح حساب owner شركة عندها deals أو دخلت buying group ← 23503 (`deals_to_company_id_fkey` / `deal_members_company_id_fkey`) — أثر جانبي لـ RESTRICT بتاع F-36. |
| F-18 | اتقفل جزئيًا | V-db | اللايكات اتصلحت (5 دورات like/unlike ← 0 إشعار). باقي: 5 مرات سحب/إعادة تقديم ← 5 إشعارات job_application، و5 مرات كومنت/مسح ← 5 إشعارات لكومنتات ممسوحة؛ مفيش retention. |
| F-19 | اتقفل | V-web | reload وهو مسجّل: التطبيق فوق مش صفحة الدخول في كل التوقيتات؛ logout ← POSTS فاضي وdx_/dbx_ اتمسحوا، والمستخدم B ما شافش likes/saves بتاعة A. |
| F-20 | اتقفل | V-web | جروبات اتعملت من الواجهة: Private + Deal Room اتخزن private/DEAL ROOM، وPublic + Discussion صح؛ الغريب ما بيشوفش الجروب الخاص. |
| F-21 | اتقفل | V-web | بالعربي: "أنشئ مجموعة" حفظ الجروب، وPost a Job حفظ العنوان والمكان والـ seniority والمرتب كاملين. |
| F-22 | اتقفل | V-web | رسالة من الـ dock ← صف messages حقيقي، مفيش رد مفبرك بعد 3 ث، مفيش outbox في localStorage؛ مفيش insights أو أرقام وهمية في الـ live. |
| F-23 | اتقفل | V-web | "Look Pharma X Egypt Ltd" (المقلّدة) بتظهر level 0 Not verified والحقيقية level 3؛ الفيديو والـ share card بيستخدموا slug الصفحة. نفس النمط لسه في `links.js:165` و`afford.js:20` (مشكلة جديدة N-2). |
| F-24 | اتقفل | V-perf-ui | 1,017 شركة في الديمو: render 28–41 ms (كان 5.3–6.4 ث)، البحث 52–75 ms للحرف، 60 كارت + Show more. |
| F-25 | اتقفل جزئيًا | V-perf-ui | صور cover كبيرة: render 72–86 ms (كان 452 ms). باقي: `dx_supplier_reviews` بيتقرا ~1,078 مرة لكل render؛ 300 review ← 230–295 ms (الديمو بس). |
| F-26 | اتقفل جزئيًا | V-db | الـ PII والـ buying groups اتقفلوا (anon: profiles 0، companies 0، deals 0، groups 0). باقي: الـ anon key لسه بيقرا posts (34 بالـ user_id)، comments، jobs، products، company_members (24)، post_media، الـ honor references المنشورة، settings. |
| F-27 | اتقفل | V-db | anon على get_reviews/get_ratings/open_candidates/moderate_reference/deal_receiver/directory_companies ← 401؛ gen_salt/digest ← 404 (pgcrypto في `extensions`)؛ الـ sweep: none. |
| F-28 | اتقفل | V-db | متقدّم بعت status=hired اتخزن submitted، وPATCH hired ← 403؛ صاحب الوظيفة shortlisted ← 200؛ applicant_count مطابق للحقيقي. |
| F-29 | اتقفل جزئيًا | V-db | الداتابيز اتصلحت (invite ← join ← member_count=2، العضو العادي ما يقدرش يدعي). باقي: الـ adapter عمره ما بيكتب `group_invites`، وزرار "Invite people" بيطلع toast بس — جروب خاص في الـ live ما ياخدش عضو تاني والمنشئ بيتقاله الدعوة اتبعتت. |
| F-30 | اتقفل | V-db | بعد vip_until: `directory_companies_page` بيرجّع free وis_vip=false والـ adapter بيبص على vip_until؛ `expire_vip_plans()` بتنزّل الـ plan. محليًا مفيش pg_cron فالعمود الخام بيفضل vip لحد ما يتفعل (ومحدش بيقراه). |
| F-31 | اتقفل | V-db | boost ← مسح الإعلان ← callback موقّع ← "paid, not activated (refund due)"، مفيش إشعار "active"، وإشعار refund للعميل والأدمنز. |
| F-32 | اتقفل جزئيًا | V-db | dismiss أو تعديل البلاغ من الشركة ← 42501. باقي: الشركة تقدر تعلّم البلاغ resolved فيختفي من Admin → Review (اللي بيقرا open بس)، ولسه بتشوف هوية المُبلِّغ. |
| F-33 | اتقفل | V-db | dispute تاني بعد إعادة النشر ← 42501؛ warning مرفوض ما يرجعش للطابور؛ الرد العادي شغال. |
| F-36 | اتقفل | V-db | مسح صفحة عليها deals ← 42501 برسالة واضحة والصفقة عند الطرف التاني فضلت؛ صفحة من غير تاريخ بتتمسح عادي (الأثر على مسح الحساب تحت F-17). |
| F-37 | اتقفل | V-db | admin يشيل owner ← 42501؛ شيل صف الـ page owner ← 42501؛ الحالات السليمة شغالة. |
| F-40 | اتقفل | V-db | HR يعمل approve/reject لـ questionnaire ← 42501؛ insert مباشر في approved_suppliers ← RLS؛ quality بيضيف الـ AVL. ملاحظة: HR لسه يقدر يقبل quote ملزم للشركة (نموذج الأدوار ما اتغيرش). |
| F-42 | اتقفل جزئيًا | V-web | الـ live اتصلح: Claim this page ← dialog ← `claim_company` ← طلب pending، والأدمن يوافق فيبقى owner؛ claim تاني مرفوض. باقي في الديمو: `verifyDialog` (`directory.js:345`) بيكتب في created_companies بس، فصفحة اتعملها claim تفضل unverified رغم toast "Documents sent". |
| F-44 | اتقفل جزئيًا | V-perf-ui | FKs من غير index: 34 ← 10 (كلها جداول قليلة)، والـ lookups الساخنة كلها على index. باقي: `my_interactions()` بقت 135–220 ms (كانت 12–15) بسبب فرع جديد في 0021 — N-1. |
| F-46 | اتقفل | V-perf-ui | authenticator عليه jit=off في الداتابيز، والدالتين عليهم jit=off، ومفيش JIT في أي plan. خطوة Supabase المستضاف ما ينفعش تتجرب هنا. |
| F-52 | اتقفل | V-web | logout في تاب 2 ← تاب 1 رجع لصفحة الدخول برسالة "Your session ended"، من غير أخطاء RLS خام؛ دخول تاني في تاب 1 ← تاب 2 اتبعه. |
| F-53 | اتقفل | V-web | فشل fetch الـ profile مرة، أو 503 مرتين ← رسالة "Connection problem" والجلسة فضلت والتطبيق فتح لوحده. |
| F-54 | اتقفل | V-web | الـ posts request اتلغى ← feed فاضي من غير أسماء ديمو؛ البحث عن "Allison" مالقاش حد؛ مفيش 342/481/87 ولا كارت "Who viewed". |
| F-55 | اتقفل | V-web | أول PATCH اتلغى ← الداتابيز null والمستخدم شاف "Connection problem"؛ إعادة الحفظ نجحت؛ تعديلات بعد 200 ms من الإنشاء اتحفظت؛ اللوجو والمنتجات بيتقال إنها مش محفوظة online. |
| F-57 | اتقفل | V-web | مستخدم من غير شركة داس Request ← toast "Create or claim your company page first" و0 deals؛ بشركة ← Requested وصف deal واحد. |
| F-58 | اتقفل | V-web | double-click على Send invitation ← عضو واحد؛ Enter 3 مرات في signup/login ← request واحد؛ double-click على بلاغ ← صف واحد. |
| F-59 | اتقفل | V-web | focus trap في Report (16 Tab + 5 Shift+Tab)، Escape بيقفل اللي فوق بس ويرجّع الـ focus؛ المحرر بيسأل "Discard your changes?"؛ theme وCtrl+K والـ tour و`#dxCoMenu` شغالين بالكيبورد. باقي صغير: `#dxEditor` من غير aria-modal. |
| F-60 | اتقفل | V-web | Reject ← Cancel على سبب الرفض ← الطلب فضل pending؛ الرفض بسبب اتخزن وبعت إشعار؛ Dismiss بيسأل تأكيد بزرار أحمر. |
| F-62 | اتقفل جزئيًا | V-perf-ui | walk عربي على 29 صفحة و29 dialog: نصوص إنجليزي 553 ← 277، attributes 71 ← 20. الباقي أغلبه sample data؛ فاضل UI: tooltips "Open X"، جملة الـ routing في `hub-ui.js:135`، "Certificate document". |
| F-63 | اتقفل | V-perf-ui | زرار لغة واحد في `#authWrap` بيقلب en↔ar/rtl، والـ signup بالعربي كامل (0 نص UI إنجليزي، كان 9). |
| F-64 | اتقفل جزئيًا | V-perf-ui | الماركت والجروبات 0 نص عربي بعد الرجوع لإنجليزي (كان 273 و82). باقي: Jobs فيها 7 عناصر عربي في 3 من 4 تشغيلات لو اتزارت بعد صفحات تانية. |
| F-66 | اتقفل | V-perf-ui | `dxT('Saved')` = المحفوظات، Remove = إزالة، Verified = موثّق. |
| F-70 | اتقفل جزئيًا | V-perf-ui | أول paint مع fonts متعلّق 6 ث: 160 ms (كان 6.2 ث). باقي: offline بيطلب Inter+Cairo ويسجّل ERR_FAILED، الـ load event بيستنى ~6 ث، والخطين مش مستخدمين أصلًا. |
| F-71 | اتقفل جزئيًا | V-perf-ui | الديمو 9.56 ← 5.51 MB؛ الـ live index 3.41 MB (1.21 gzip) والفيديو ملف منفصل immutable؛ Slow 4G: domInteractive 18.6 ث (كان 46.7). باقي: 2.25 MB scripts inline في index.html (no-cache) و114 KB مكرر. |
| F-72 | اتقفل | V-perf-ui | تباين الـ ticker 2.11 ← 10.21، أقل فئة 7.05، `.dx-tier` 5.48، `.in-person em` 4.76 — كله ≥ 4.5 فاتح وغامق. |
| F-114 | اتقفل | V-db | `review_instapay(false)` على طلب card مدفوع ← 400 "Not waiting for review" ومفيش إشعار؛ رفض طلب في review ← failed وإشعار واحد. |
| F-115 | اتقفل جزئيًا | V-db | مسار Paymob اتقفل (USD ← currency mismatch، merchant_order_id مش بيتحسب، replay ← already paid). باقي: إشعار Fawry حقيقي لـ DBX18 اتبعت تاني بـ merchantRefNumber "DBX182" وpaymentAmount 850 بنفس التوقيع ← DBX182 اتعلّم paid والأصلي اترفض "transaction already used". |
| F-116 | اتقفل | V-db | طلب InstaPay في review: callback Paymob موقّع، ومفتاح بالـ DBX، وإشعار Fawry موقّع ← الكل "unknown order" والطلب فضل review. |
| F-124 | اتقفل | V-perf-ui | build مرتين (مرة بـ TZ=Pacific/Auckland وLANG=ar_EG) ← نفس sha 35782b6a ومفيش tracked file اتغيّر؛ live.py نفس الهاشات ويرفض لو الديمو أقدم من المصدر. |
| F-150 | اتقفل | V-perf-ui | parity_check بيفشل برسالة واضحة لملفات فاضية/مقطوعة/مش موجودة ولتغيير حرف في الـ snapshot؛ المرجع ضد الـ dist ← PARITY OK. |
| F-151 | اتقفل جزئيًا | V-perf-ui | Aurobindo وMusthafa وEpione وAllison Wang والرقم والإيميل الحقيقيين = 0 في كل الملفات. باقي: "Dr. Asmaa Meabed" 38 مرة في الديمو — متسابة لقرارك. |

**الأماكن اللي التحقق خالف فيها الـ workstream:**

- **F-02**: كلام الـ workstreams كان جزئي، والتحقق المستقل قال اتصلح — المعتمد: اتصلح.
- **F-04**: كلام الـ workstreams كان اتصلح، والتحقق المستقل قال جزئي — المعتمد: جزئي.
- **F-10**: كلام الـ workstreams كان اتصلح، والتحقق المستقل قال جزئي — المعتمد: جزئي.
- **F-11**: كلام الـ workstreams كان جزئي، والتحقق المستقل قال اتصلح — المعتمد: اتصلح.
- **F-17**: كلام الـ workstreams كان اتصلح، والتحقق المستقل قال جزئي — المعتمد: جزئي.
- **F-18**: كلام الـ workstreams كان اتصلح، والتحقق المستقل قال جزئي — المعتمد: جزئي.
- **F-23**: كلام الـ workstreams كان جزئي، والتحقق المستقل قال اتصلح — المعتمد: اتصلح.
- **F-25**: كلام الـ workstreams كان اتصلح، والتحقق المستقل قال جزئي — المعتمد: جزئي.
- **F-26**: كلام الـ workstreams كان اتصلح، والتحقق المستقل قال جزئي — المعتمد: جزئي.
- **F-29**: كلام الـ workstreams كان اتصلح، والتحقق المستقل قال جزئي — المعتمد: جزئي.
- **F-30**: كلام الـ workstreams كان جزئي، والتحقق المستقل قال اتصلح — المعتمد: اتصلح.
- **F-32**: كلام الـ workstreams كان اتصلح، والتحقق المستقل قال جزئي — المعتمد: جزئي.
- **F-42**: كلام الـ workstreams كان اتصلح، والتحقق المستقل قال جزئي — المعتمد: جزئي.
- **F-44**: كلام الـ workstreams كان اتصلح، والتحقق المستقل قال جزئي — المعتمد: جزئي.
- **F-59**: كلام الـ workstreams كان جزئي، والتحقق المستقل قال اتصلح — المعتمد: اتصلح.
- **F-63**: كلام الـ workstreams كان جزئي، والتحقق المستقل قال اتصلح — المعتمد: اتصلح.
- **F-64**: كلام الـ workstreams كان اتصلح، والتحقق المستقل قال جزئي — المعتمد: جزئي.
- **F-70**: كلام الـ workstreams كان اتصلح، والتحقق المستقل قال جزئي — المعتمد: جزئي.
- **F-71**: كلام الـ workstreams كان اتصلح، والتحقق المستقل قال جزئي — المعتمد: جزئي.
- **F-115**: كلام الـ workstreams كان اتصلح، والتحقق المستقل قال جزئي — المعتمد: جزئي.

### 3.2 الجولة التانية (R2-V2)

R2-V2 اشتغل على الشجرة النهائية (`828133f`) والـ stack المشترك شغال: `web/dist/live` مطابق لـ build جديد من نفس الشجرة، والديمو PARITY OK. استخدم داتابيزين scratch: `rv_v2` (الـ stub + 0001..0024، والـ sweep 6 مرات none) و`rv_v2s` (نفسها + 20k مستخدم و5k شركة و20k صفقة)، واتمسحوا في الآخر، وكل حسابات وصفوف الاختبار اتشالت من `drugbox_live`. الإذن ما اتداش لزرع 4,200 شركة مؤقتة في الداتابيز المشتركة، فتجربة F-05 في البراوزر اتعملت على 838 شركة، ومقاس الـ 5k اتعمل على `rv_v2s`. النتيجة: **17 اتقفلوا وواحد جزئي (F-70)**.

| ID | الحكم | الدليل |
|---|---|---|
| F-115 | اتقفل | إشعار Fawry حقيقي لـ DBX35 (2850.00) اتبعت تاني كـ merchantRefNumber "DBX352" وpaymentAmount 850 بنفس التوقيع ← 400 "amount mismatch"، والطلبين فضلوا pending. من غير الـ webhook: `confirm_payment('fawry')` بمرجع Fawry بتاع طلب تاني أو بـ null ← "reference mismatch". توقيع A مع merchantRef بتاع B ← 401. Paymob: USD ← "currency mismatch"، وmerchant_order_id متبدّل بيدفع الطلب الموقّع بس، وtransaction id متكرر ← "transaction already used". الدفع السليم شغال. |
| N-1 | اتقفل | عند 20k صفقة: `my_interactions()` في psql 6.0–9.2 ms (كانت 116–183)، ومن PostgREST median 9.8–12.4 ms (كانت 135–220). النتايج صح: E بيشوف المتقدّم C والـ contact R (متصلين واتراسلوا وopen to work)، ومش بيشوف G اللي مالوش علاقة. |
| F-17 | اتقفل | مسح حساب owner شركة دخلت buying group وعندها RFQ ← نجح، والشركة فضلت unclaimed (owner null)، والـ deal_members والـ RFQ فضلوا. وكمان اتمسحوا عادي: مورّد عنده deals واردة، ومنظّم buying group (الجروب فضل بـ from_user null)، وشخص عنده طلب وظيفة لشركة، وصاحب وظايف وريفيوهات وإشعارات. سكريبت الجولة الأولى بعد ترتيبه: 58 / 58 هجمة اتصدّت و39 / 39 حالة سليمة. |
| F-18 | اتقفل | أول تقديم ← إشعار واحد لصاحب الوظيفة، و5 مرات سحب وإعادة ← لسه واحد، ومتقدّم تاني ← 2. 5 مرات كومنت ومسح ← 0، وكومنت متساب ← 1. `purge_old_notifications` مش متاحة لـ authenticated. |
| F-32 | اتقفل | الشركة المبلَّغ عنها بتقرا 0 صف من `company_reports`، وبتشوف البلاغ من `company_reports_received()` بس ومن غير عمود المبلِّغ. تغييرها لـ resolved أو dismissed بيغيّر 0 صف، والمسح ← 42501، والبلاغ فاضل open في طابور الأدمن. لما أدمن Drugbox يقفله الشركة بتشوفه resolved. والـ e2e e2_review 16 / 16. |
| F-10 | اتقفل | متقدّم بيقيّم صاحب وظيفة open_to_work بدور candidate ← 42501 (كان بيتسجّل). مرفوض كمان: صاحب شغل بيقيّم غريب كـ employer، وواحد مش بيوظّف ومتصل ومراسل بيقيّم كـ candidate، وcontact من غير تقديم بيقيّم كـ employer. شغال: المتقدّم بيقيّم صاحب الوظيفة كـ employer، وصاحب الوظيفة بيقيّم المتقدّم كـ candidate، وصاحب شغل متصل ومراسل في الاتجاهين بيقيّم contact open to work، والمتقدّم لوظيفة شركة بيقيّم owner الشركة. والـ e2e d2b_trust 14 / 14. |
| F-26 | اتقفل | 46 جدول وview بالـ anon key بس: الصفوف جت من `payment_products` و`settings` و`ticker_items` و`training_courses` بس (عامة بالتصميم)، والباقي 0 صف، و`company_documents?select=*` ← 401. الـ sweep: مفيش دالة security-definer متاحة لـ anon. التطبيق من غير تسجيل على 1440 و390: 0 calls لـ REST أو storage أو functions أو auth. فيه ذيل منفصل (N-7 تحت). |
| F-44 | اتقفل | استعلام الجولة الأولى (FKs من غير index) طلّع 0 صف على داتابيز نضيفة وعلى `drugbox_live` (كانوا 10). والـ FKs الجديدة `job_id` و`comment_id` عليها partial indexes. |
| N-4 (الأدمن يوثّق) | اتقفل | PATCH من أدمن بـ verified=true لشخص ← 200 والصف اتغيّر، والإلغاء 204. أدمن بيعدّل headline لحد تاني ← 403. مستخدم عادي بيوثّق حد ← 0 صف، وبيوثّق نفسه ← 403. وتعديل الـ headline بتاعه شغال. |
| F-05 | اتقفل | الـ live بـ 838 شركة (12 / 12): الـ sign-in مش بينده الدليل. فتح Companies ← request واحد `{p_limit:100}` بـ 59 KB والكروت بعد 184 ms. Market أو الرجوع خلال دقيقتين ← 0 requests. Show more ← request واحد (offset 100). بعد دقيقتين ← الصفحة الأولى بس. بحث مالوش نتيجة ← request واحد. الجلسة كلها 4 requests و175 KB. عند 5k شركة: الصفحة 160–163 KB في 40–43 ms، وp_limit 5000 بيتقص لـ 200، و`directory_companies(5000)` القديمة ← 403. |
| F-29 | اتقفل | الـ live بالعربي (15 / 16): الأدمن عمل جروب خاص من الشباك المعتمد، ودعا B من زرار الدعوة الحقيقي ← صف في `group_invites` وtoast "Invites sent to 1 person". B شاف الكارت وانضم، وmember_count بقى 2، والدعوة اتستهلكت. الغريب مش شايف حاجة، والـ join من الـ API مرفوض. الفحص الوحيد اللي فشل كان nice-to-have: مفيش إشعار للمدعو (N-8). |
| N-2 (البحث بأول الاسم) | اتقفل | الـ live 8 / 8: owner "Look Pharma <x> Egypt WS" داس على عنوان الـ workspace فراح لصفحته هو، وكان بيروح للشركة اللي اسمها أقصر. `dxAfford.destination()` بقى بيطابق الاسم بالظبط أو الاسم + فاصل، والأطول بيكسب. فيه ذيل للأشخاص (N-10). |
| F-25 | اتقفل | 1,000 شركة و300 review متخزّن: المرجع القديم 204–374 ms والجديد 28–38 ms. و50 review: من 67–101 لـ 29–42 ms. الـ cache لكل `__dxStoreVer`، فمش بيقدم بين الـ renders. |
| F-62 | اتقفل | walk عربي (29 صفحة + 29 dialog): النصوص الإنجليزي المختلفة 277 ← 265، والـ attributes 18 ← 9، من غير errors. كل اللي اتذكر في الجولة الأولى اختفى: tooltips "Open X"، وجملة Questionnaires، و"Certificate document"، و"listed"، و"commented:"، و"<co>: Send quote — …". الباقي sample data. فيه ذيول في الجروبات (N-9). |
| F-64 | اتقفل | 8 تسلسلات لكل build: المرجع القديم ساب 7 عناصر عربي في Jobs في 6 من 8، والجديد 0 في 8 من 8 (market وgroups وjobs). السبب كان `brand.js` بيقسّم نصوص متترجمة بعد ما الـ i18n يعدّي عليها. |
| F-70 | جزئي | offline حقيقي (navigator.onLine=false): 0 طلبات للخطوط و0 errors (القديم: طلب وERR_INTERNET_DISCONNECTED)، وFCP 192 ms. لكن على جهاز "online" مش واصل لجوجل (LAN، captive portal، firewall) لسه بيطلب fonts.googleapis.com ويسجّل ERR_FAILED، ولو السيرفر معلّق الـ load event بيستنى حوالي 6 ث. الـ FCP مش متأثر (260 ms). |
| F-71 | اتقفل | الـ live `index.html` بقى 599,641 B (gzip 296 KB) بدل 3.41 MB، والـ inline scripts 1,962 B بدل 2.25 MB. بنفس طريقة الجولة الأولى: FCP 2.75 ث وdomInteractive 13.6 ث (كانوا 5.3 و18.6). Slow-4G preset: الزيارة التانية DI 4.87 ث والـ 33 script من الـ cache. ذيل صغير: اللوجو (28 KB) مكرر مرتين. |
| N-3 | اتقفل | `web/dist/live/js` فيه 34 ملف، هم بالظبط اللي `index.html` بيطلبهم. زرعنا adapter وفيديو قديمين في نسخة وشغّلنا live.py ← "removed old files: 2"، والناتج مطابق (diff -r) للـ live المشترك، فالـ build deterministic. |

**فحوص زيادة:** e2e e2_review 16 / 16 وd2b_trust 14 / 14 على الـ stack المشترك. ووقت كتابة الملف ده اتشيّك F-132 على `web/dist/drugbox.html`: فحص UI قديم بيتوقع إن Escape واحدة تقفل الـ lightbox والجروب مع بعض، وده بيخالف F-59 (Escape بتقفل اللي فوق بس). الواقع: أول Escape بتقفل الـ lightbox، والتانية بتقفل الجروب، ومن غير errors. يعني السلوك مظبوط والفحص القديم هو اللي محتاج يتحدّث.

**F-42** اتكمّل في الجولة التانية (الديمو: `verifyDialog` بقى بيكتب في `company_edits` للصفحات اللي اتعملها claim). اتجرب في فحوص r2-ui (23 / 23) وفي مراجعة R2-G1، بس R2-V2 ما عادهوش.

### 3.3 الجولة التالتة (V3)

V3 اشتغل على `e3c3dde` (بناء جديد من نفس الشجرة طلع نفس الـ sha `d7709969` وPARITY OK)، على الـ stack المشترك و0025 متطبّقة. كل الصفوف والحسابات المؤقتة اتمسحت في الآخر. النتيجة: **الستة اتقفلوا**، والمسار السليم شغال في كل واحد منهم.

| ID | الحكم | الدليل |
|---|---|---|
| N-7 | اتقفل | صف مستند مؤقت (verified ومعاه `file_path`) اتقرا بالـ anon key بس: `company_documents?select=*` ← 401، والأعمدة المسموحة ← 200 بـ 0 صف، وبالـ id برضه 0، و`company_documents_public` ← 0 صف. الـ policy "documents: everyone reads metadata" بقت `TO authenticated` (0025)، ومفيش دالة عامة بتقرا الجدول، فمفيش طريق تاني من RPC. المستخدم المسجّل بيقرا الصف من الـ view والأعمدة، و`file_path` لسه مرفوض (403). والـ e2e e1b_documents 13 / 13. |
| N-8 | اتقفل | الـ live 15 / 15: أدمن بالعربي عمل جروب خاص من الشباك المعتمد ودعا اتنين بزرار الدعوة الحقيقي ← صفين في `group_invites`. المدعو B جاله إشعار واحد (`group_invite`، من الأدمن، فيه اسم الجروب)، والغريب ماجالوش حاجة. التزوير مرفوض: insert مباشر في notifications، ولا إنك تدعي نفسك. B (إنجليزي) شاف '<Admin> invited you to join the private group "<name>"' في Alerts بـ badge 1، وD (عربي) شاف 'دعاك للانضمام إلى المجموعة الخاصة "<name>"'. لما B انضم member_count بقى 2 والدعوة اتستهلكت والإشعار فضل، ولما دعوة D اتسحبت الإشعار بتاعه اتشال. 0 page errors، والـ e2e d3_groups 27 / 27. |
| N-9 | اتقفل | النص اتقرا بعد الـ paint (مراقبة أولى بالـ MutationObserver كانت بتمسك الإنجليزي اللي الـ i18n بيبدّله قبل ما الفريم يترسم). الديمو بعد login حقيقي: 24 / 24 على الجديد و13 / 24 على بناء ما قبل الجولة، يعني الفحص بيفرّق بينهم. بالعربي: زرار الدعوة '✉️ ادعُ'، وtoast الإنشاء 'تم إنشاء المجموعة — ادعُ أول أعضائها'، وtoasts الدعوة لـ 1 و2 و5 و11 شخص: 'تم إرسال الدعوة إلى شخص واحد' و'…إلى شخصين' و'…إلى 5 أشخاص' و'…إلى 11 شخصًا'. شباك الدعوة مافيهوش إنجليزي، والإنجليزي ما اتغيّرش. والـ live: الزرار '✉️ ادعُ' والـ toasts 'تم إنشاء المجموعة' و'تم إرسال الدعوات إلى شخصين'. |
| N-10 | اتقفل | `afford.js user()` بقى بيطابق الاسم بالظبط أو الاسم + فاصل، والأطول بيكسب. 'Sara Nabil Fahmy' مبقاش بيفتح 'Sara Nabil' (في القديم كان بيفتحها). الاسم بالظبط و'· 3h' و'✓' و', PharmD' لسه بيفتحوها، و'Sara Nabil2' و'Sara' مش بيطابقوا حد، ولو الاتنين موجودين الأطول بيكسب، ونفس الكلام بالعربي. كل شخص في الديمو اسمه بيفتحه، والكليك الحقيقي على كروت البروفايل (الاسم والوظيفة، 5 أشخاص) نفس النتيجة في القديم والجديد. الاختلافات السبعة اللي طلعت كانت على عناصر مش بتتداس أصلًا. ذيل: الاسم بشرطة (N-14). |
| F-70 | اتقفل | `app.html` سطر 8 بيضيف link الخطوط بعد الـ load event بس، ولو `navigator.onLine` مش false، وبيشيله لو فشل. سيرفر خطوط معلّق (proxy بيمسك الاتصال) 6 ث و60 ث: الـ load event حوالي 0.5 ث في الجديد، و6.03 ث و30.06 ث في القديم. offline كامل: 0 طلبات خطوط و0 errors. ولما الخطوط متاحة الـ stylesheet بيتطبّق ومتحمّل مرة واحدة (بسيرفر HTTP حقيقي بالـ cache). الـ live (تعليق 6 و20 ث): load عند 264 و256 ms، وطلب الخطوط بيبدأ بعد الـ load، والـ link بيتشال بعد الـ abort (القديم 6076 و20063 ms). ذيل طبيعي: لو السيرفر واصل بس بيرفض، بيتسجّل ERR_FAILED واحد. |
| F-74 | اتقفل | REST (11 / 11): 5 جولات، في كل جولة مستخدمين بيبعتوا نفس الاسم والـ slug في نفس اللحظة ← الاتنين 201 بـ x وx-2. 12 في نفس اللحظة ← كلهم 201 بـ slugs مختلفة (x و-2…-9 وبعدين 3 بلاحقة hex)، وكل شركة owner بتاعها اللي عملها. من غير slug ← الاتنين اتعملوا بـ slugs مختلفة. تغيير الـ slug لواحد متاخد بيزوّد لاحقة، والشركة التانية بتحتفظ بالـ slug بتاعها. الإنشاء العادي بيحتفظ بالـ slug بتاع البراوزر، والتعديل العادي ما بيغيّرش الـ slug. الواجهة (10 / 10): متصفحين داسوا "Create my page" الحقيقي في نفس اللحظة ← الشركتين اتعملوا (x وx-2) من غير toast خطأ، وتعديل كل owner راح على صفه، وبعد reload كل واحد شايف شركته بالـ slug بتاع الداتابيز. والـ e2e c1_companies 25 / 25. ذيلين: N-11 وN-12 (5.7). |

**ملاحظة:** وقت التحقق، حد تاني غيّر في الشجرة (اتمسح `vercel.json`، واتعدّل `web/build/live.py`، واتضاف `deploy/` و`tools/scale/`). ده مش جزء من الجولة دي ومش في `e3c3dde`، وV3 ما لمسوش.

## 4. حالة كل البنود (178)

اتصلح 167 · جزئي 8 · متأجل 2 · ملاحظة 1. "اتحقق منه" = البند اتجرب بشكل مستقل في الجولة الأولى (3.1). "اتحقق منه في الجولة 2" = اتصلح في الجولة التانية واتجرب تاني بشكل مستقل (3.2). "اتحقق منه في الجولة 3" = اتصلح في الجولة التالتة واتجرب بشكل مستقل (3.3). "اتكمّل في الجولة 2" = اتكمّل في الجولة التانية واتجرب في الـ workstream والـ gate بس. "اتكمّل بعدين" = الـ workstream قال جزئي والباقي اتعمل في خطوة بعدها:

- **F-68**: UI1 قال جزئي؛ UI3 صلّح `openBoostModal` وG1 صلّح رسالة التأكيد بعد الدفع.
- **F-126**: UI1 قال جزئي؛ INFRA نقل الـ 7 suites القديمة لـ `tests/demo/legacy/retired`.
- **F-127**: UI1 قال جزئي؛ الباقي (الـ ticker و`.lg-demo`) اتعمل في UIFOLLOW وG1 شاف الـ ticker العربي شغال.
- **F-128**: UI1 قال جزئي؛ `.me-name` اتعمله overflow-wrap في UIFOLLOW وG1 شاف الأسماء الطويلة بتلف.
- **F-170**: DB4 قال جزئي؛ CORS اتصلح، `completed` مش متاح بالتصميم، والـ mock مبقاش بيسجّل الـ Authorization (F-79).

| ID | الخطورة | العنوان | الحالة | فين اتصلح |
|---|---|---|---|---|
| F-01 | حرج | أي مستخدم يقدر يخلي نفسه admin/verified: سياسة profiles own-update من غير تقييد أعمدة | اتصلح (اتحقق منه) | `0020_security_core.sql` |
| F-02 | حرج | Stored XSS من نصوص/روابط الداتابيز بتتحط في الـ markup من غير escape (logo_url, cover, avatar_url, post_media.url, enquiries.flag, intro_video.poster, links.js phone/name) → سرقة الحساب | اتصلح (اتحقق منه — خالف كلام الـ workstream) | `adapter.js` + `directory.js`/`hub-ui.js` + `links.js`/`videos.js` + `app.html` |
| F-03 | حرج | صاحب الإعلان بياخد Boost/Featured ببلاش: سياسة products own-manage بتسمح يكتب boosted_until/featured_until (ومعاهم counters/pinned) | اتصلح (اتحقق منه) | `0020_security_core.sql` |
| F-04 | حرج | GET /deals بيشغّل is_company_member() على كل صف وكل embed → 2.4 ثانية في كل sign-in وكل notification | جزئي (اتحقق منه — محتاج k6 على staging) | `0022` §1 (`my_company_ids`, `idx_deals_updated`) |
| F-05 | حرج | directory_companies(5000) بيبني 8.7–17 MB JSON ويعيد حساب track record لكل شركة في كل sign-in وكل زيارة anon | اتصلح (اتحقق منه في الجولة 2) | `0022` §2 + `0024` (`directory_companies` مقفولة) + `adapter.js` (صفحات 100 + Show more + البحث) |
| F-06 | عالي | الـ Boost/Featured المدفوعين مش بيعملوا حاجة في الـ live: boosted_until/featured_until بيتكتبوا ومحدش بيقراهم | اتصلح (اتحقق منه) | `adapter.js` (loadMarket) |
| F-07 | عالي | سعر الـ Boost/Featured في شباك الدفع محسوب من USD × FX API خارجي ومختلف عن اللي السيرفر بيحاسب عليه (payment_products) | اتصلح (اتحقق منه) | `checkout.js` + `adapter.js` (`dxPay.quote`) |
| F-08 | عالي | connections بتتزوّر: insert كـ accepted مباشرة من غير موافقة، والـ addressee يقدر يغيّر الـ requester لشخص تالت | اتصلح (اتحقق منه) | `0020_security_core.sql` |
| F-09 | عالي | أعمدة السيرفر (id, created_at, pinned, counters, read_at, reply/replied_at) البراوزر بيكتبها: تثبيت بوست سنة 2099، كسر paging، DoS للرسايل، تزوير رد المرشح | اتصلح (اتحقق منه) | `0020_security_core.sql` |
| F-10 | عالي | رسالة واحدة = 'تعامل حقيقي': أي حد يسيب review مجهول 1 نجمة على أي حد ويتعرض كـ Verified applicant | اتصلح (اتحقق منه في الجولة 2) | `0021` + `0024` (`can_review` و`my_interactions`) |
| F-11 | عالي | work_reference_rules معتمدة على profile.company نص حر بـ LIKE: أي حد ينشر honor/warning على أي حد — وفي الـ live مستحيل تتعمل أصلاً لأن experience مش بتتكتب | اتصلح (اتحقق منه — خالف كلام الـ workstream) | `0021` §3 |
| F-12 | عالي | jobs_interacted(a,b) و increment_* RPCs مفتوحين لـ anon: oracle على مين راسل مين / قدّم لمين | اتصلح (اتحقق منه) | `0020_security_core.sql` |
| F-13 | عالي | site_certificates مش مربوطة بشركة الموقع: أي عضو شركة يحط شهادات على صفحة شركة منافسة | اتصلح (اتحقق منه) | `0021_trust_hub_deals.sql` |
| F-14 | عالي | مستند compliance متحقق منه يتعدّل بالكامل (النوع/الرقم/الملف) ويفضل status = verified | اتصلح (اتحقق منه) | `0021_trust_hub_deals.sql` |
| F-15 | عالي | العضو اللي سابَ الشركة بيفضل متحكم بكل deal هو اللي بدأها (from_user بيتخطى العضوية للأبد) | اتصلح (اتحقق منه) | `0021_trust_hub_deals.sql` |
| F-16 | عالي | أرقام محرك الصفقات من غير validation: deal_join يقبل NaN/Infinity/كميات ضخمة ويقفل أي buying group، وvalidity تعمل overflow | اتصلح (اتحقق منه) | `0021_trust_hub_deals.sql` |
| F-17 | عالي | FKs بـ NO ACTION (notifications, groups.created_by, reviewed_by, comments.parent) بتمنع مسح أي بوست اتعمله like/comment ومسح أي حساب | اتصلح (اتحقق منه في الجولة 2) | `0022` §3 + `0024` (`owner_id` و`from_user` ← SET NULL) |
| F-18 | عالي | notification لكل like من غير dedupe والـ unlike مش بيمسحها: 2,352 إشعار دائم في 20 ثانية | اتصلح (اتحقق منه في الجولة 2) | `0022` §4 + `0024` (`job_id`/`comment_id` + dedupe + `purge_old_notifications`) |
| F-19 | عالي | جلسة الـ adapter: صفحة الدخول بتتحط فوق التطبيق مع كل تحميل، والـ logout بيسيب cache المستخدم السابق للحساب الجديد | اتصلح (اتحقق منه) | `web/src/live/adapter.js` |
| F-20 | عالي | الجروبات الـ Private/Deal Room بتتعمل public DISCUSS في الـ live (الـ adapter بيقرأ radio مش موجود) | اتصلح (اتحقق منه) | `web/src/live/adapter.js` |
| F-21 | عالي | الـ adapter بيعتمد على نص الأزرار/placeholders الإنجليزي → إنشاء الجروب وحقل Location بيتكسروا في الواجهة العربية | اتصلح (اتحقق منه) | `web/src/live/adapter.js` |
| F-22 | عالي | محاكاة الديمو شغالة في الـ live: الـ dock بيبعت لـ localStorage وبيظهر رد مفبرك من شخص حقيقي، وإحصائيات وهمية | اتصلح (اتحقق منه) | `batch2.js`/`batch3.js`/`craft.js`/`links.js` + `adapter.js` |
| F-23 | عالي | الشركة بتتحدد بـ prefix الاسم من الـ h1: badge/passport/share card/video بيظهروا لشركة تانية اسمها بيبدأ بنفس الكلمة (trust spoofing) | اتصلح (اتحقق منه — خالف كلام الـ workstream) | `tiers.js` + `share.js` + `videos.js` |
| F-24 | عالي | الدليل بيرندر كل الشركات مرة واحدة والبحث O(n²) (madeFor × n): ثواني لكل حرف عند آلاف الشركات | اتصلح (اتحقق منه) | `hub-ui.js` + `hub-data.js` |
| F-25 | عالي | companies() مش memoised: كل render بيقرأ ويعمل JSON.parse لـ localStorage مئات المرات — صورة cover واحدة تبطّئ الدليل 18–95× | اتصلح (اتحقق منه في الجولة 2) | `directory.js` + `hub-data.js` (cache لكل `__dxStoreVer`) |
| F-26 | متوسط | الـ anon key بيقرأ بيانات شخصية والـ content graph كله: profiles.phone/role، companies.email/phone/registry، الـ buying groups بأعضائها وكمياتها | اتصلح (اتحقق منه في الجولة 2) | `0020` + `0024` (privacy-first) + `0025` (مستندات الشركات، N-7) |
| F-27 | متوسط | EXECUTE الافتراضي لـ anon على functions: get_reviews/get_ratings/moderate_reference/deal_receiver وpgcrypto/pg_trgm | اتصلح (اتحقق منه) | `0020_security_core.sql` |
| F-28 | متوسط | المتقدم للوظيفة بيغيّر status بتاعه (hired/shortlisted) وصاحب الوظيفة مالوش UPDATE policy خالص | اتصلح (اتحقق منه) | `0021_trust_hub_deals.sql` |
| F-29 | متوسط | الجروبات الخاصة dead end في الداتابيز: محدش غير المنشئ يشوفها أو ينضم، وadmin الجروب يقدر يعدّل صفوف العضوية | اتصلح (اتحقق منه في الجولة 2) | `0021` + `adapter.js` (الدعوة ← `group_invites`) + `0025` (إشعار الدعوة، N-8) |
| F-30 | متوسط | VIP مش بينتهي أبداً: vip_until بيتكتب ومحدش بيقراه ولا بينزّل plan | اتصلح (اتحقق منه — خالف كلام الـ workstream) | `0023` §1 + `0021`/`0022` (plan الفعلي) + `adapter.js` |
| F-31 | متوسط | activate_order بيعلّم الطلب paid ويبعت إشعار 'active' حتى لو الإعلان/الشركة اتمسحت | اتصلح (اتحقق منه) | `0023_payments_moderation_storage.sql` |
| F-32 | متوسط | الشركة المُبلَّغ عنها تقدر تشيل وتعدّل بلاغات 'معلومات غلط' قبل ما Drugbox تشوفها | اتصلح (اتحقق منه في الجولة 2) | `0023` + `0024` (`company_reports_received`) + `adapter.js` |
| F-33 | متوسط | المرشح يقدر يخفي warning منشور للأبد بإنه يعمل dispute تاني (reply_to_reference من غير state check) | اتصلح (اتحقق منه) | `0021_trust_hub_deals.sql` |
| F-34 | متوسط | job_reviews.hidden مستحيل يتعمل set: مفيش policy ولا function ولا UI — مفيش أي علاج للريفيوهات المسيئة | جزئي | `0021_trust_hub_deals.sql` |
| F-35 | متوسط | jobs_hidden_for_me() بتكشف مين حاطك في الـ blacklist | اتصلح | `0021_trust_hub_deals.sql` |
| F-36 | متوسط | مسح صفحة شركة بيعمل cascade لصفقات وطلبات وAVL شركات تانية | اتصلح (اتحقق منه) | `0021_trust_hub_deals.sql` |
| F-37 | متوسط | عضو admin يقدر يمسح عضوية الـ owner (القاعدة اتطبقت على UPDATE مش DELETE) | اتصلح (اتحقق منه) | `0021_trust_hub_deals.sql` |
| F-38 | متوسط | routing الطلبات ممكن يشاور على غير أعضاء وبيفضل بعد خروج العضو: عناوين الطلبات بتتسرب لبرّه | اتصلح | `0021_trust_hub_deals.sql` |
| F-39 | متوسط | track record العام بيتنفخ ذاتياً: شخص عنده شركتين يقيّم نفسه 5 نجوم | اتصلح | `0021_trust_hub_deals.sql` |
| F-40 | متوسط | الموافقة على questionnaire عن طريق المحرك بتسمح لأي role يكتب approved-supplier list | اتصلح (اتحقق منه) | `0021_trust_hub_deals.sql` |
| F-41 | متوسط | مسح البوست بيسيب صوره وملفاته متاحة للتحميل في post-media للأبد | اتصلح | `0023_payments_moderation_storage.sql` |
| F-42 | متوسط | 'Claim this page' مالوش مسار سيرفر: الـ claim في الديمو مجرد edits، طلب التحقق من شركة claimed بيضيع، والـ admin ما يقدرش يعمل صفحات unclaimed | اتصلح (اتكمّل في الجولة 2) | `0021` §9 (`claim_company`) + `adapter.js` + `directory.js` (`verifyDialog` ← `company_edits`) |
| F-43 | متوسط | مفيش حدود حجم على نصوص المستخدم: messages.body بـ 2 MB (وبيتنسخ في conversation_heads)، bio/profile/site، JSON المحرك والإعلانات | اتصلح | `0022_integrity_perf.sql` |
| F-44 | متوسط | فهارس ناقصة على FK/الأعمدة الساخنة (34 FK): notifications, jobs(user_id), job_applications(cv_path), products(user_id), company_followers… | اتصلح (اتحقق منه في الجولة 2) | `0022` §7 + `0020`/`0021` + `0024` (آخر 10 FKs) |
| F-45 | متوسط | Hot counter row: 50 لايك على نفس البوست بيتسلسلوا على lock صف posts (117 tps بدل 1,784) | متأجل | — (الأسباب في `0022` §13) |
| F-46 | متوسط | JIT بيزوّد ~0.9 ثانية على كل deals call (79 function) وإعدادات Supabase سايباه on | اتصلح (اتحقق منه) | `0022` §12 |
| F-47 | متوسط | suggest_people تكلفتها بتكبر مع عدد الأصدقاء × درجتهم وبتعمل hash لكل profiles في الآخر | اتصلح | `0022_integrity_perf.sql` |
| F-48 | متوسط | عداد أعضاء الجروب recount trigger بيعمل drift مع الانضمام المتزامن | اتصلح | `0022_integrity_perf.sql` |
| F-49 | متوسط | نقل reaction بـ UPDATE بيفصل like_count (الـ trigger على INSERT/DELETE بس) | اتصلح | `0022_integrity_perf.sql` |
| F-50 | متوسط | الـ adapter بيجيب زيادة: كل كارت بيضمّن profiles كامل، connections ×2 بحد 1000 بيقطع الشبكة، work_references بيتجاب بدون فلتر | اتصلح | `web/src/live/adapter.js` |
| F-51 | متوسط | tick()/Realtime: بيشتغل متوازي ويكرّر الرسالة الواردة، وبيعيد تحميل connections/notifications/deals مع كل إشعار، وpolling كل 20 ث | اتصلح | `web/src/live/adapter.js` |
| F-52 | متوسط | مفيش onAuthStateChange: بعد logout في تاب تاني أو فشل refresh التطبيق بيكمل كـ anon ويعرض أخطاء RLS خام | اتصلح (اتحقق منه) | `web/src/live/adapter.js` |
| F-53 | متوسط | فشل مؤقت في جلب الـ profile عند التحميل بيعمل sign-out ويدمّر الجلسة | اتصلح (اتحقق منه) | `web/src/live/adapter.js` |
| F-54 | متوسط | بيانات seed بتاعة الديمو بتتسرب للـ live: بوستات مفبركة لما الـ feed يفشل، أشخاص الديمو في البحث، surplus/dossiers الديمو في الماركت | اتصلح (اتحقق منه) | `web/src/live/adapter.js` |
| F-55 | متوسط | حفظ صفحة الشركة في الـ adapter: الـ snapshot بيتسجل قبل الكتابة فالفشل مش بيتعاد، حقول مش بتتحفظ (products/logo/cover/certificates) بتظهر محفوظة، وتعديلات أثناء الـ insert بتضيع | اتصلح (اتحقق منه) | `web/src/live/adapter.js` |
| F-56 | متوسط | wrapper بتاع dxHub.page/workspace بيرجّع صفحة الشركة بعد ما المستخدم راح صفحة تانية | اتصلح | `web/src/live/adapter.js` |
| F-57 | متوسط | طلبات الصفقات بتتعرض لأشخاص من غير شركة وبتتعلّم 'Requested' والمحرك بيرفضها | اتصلح (اتحقق منه) | `deals.js` + `directory*.js` |
| F-58 | متوسط | الزر الأساسي في الـ dialogs بيتنفذ مع كل كليك: double-click يبعت مرتين (أعضاء/مواقع/بلاغات مكررة) ونفس الشيء login/signup بـ Enter | اتصلح (اتحقق منه) | `app.html` |
| F-59 | متوسط | Dialogs وmenus من غير focus trap/restore ولا كيبورد: الخلفية شغالة، Escape بيقفل كل الـ stack، drawer المحرر بيضيع التعديلات بكليك على الخلفية، Appearance وCtrl+K والـ tabs | اتصلح (اتحقق منه — خالف كلام الـ workstream) | `app.html` (DBK) + `directory.js`/`brand.js`/`batch3.js` |
| F-60 | متوسط | Moderation: Cancel في prompt سبب الرفض بيرفض برضه، ومفيش تأكيد للقرارات المدمرة | اتصلح (اتحقق منه) | `moderation.js` |
| F-61 | متوسط | afford.js بيودّي المستخدم لصفحة Groups لما يدوس على ختم Verified في كارت الوظيفة | اتصلح | `afford.js` |
| F-62 | متوسط | نصوص كتير فاضلة إنجليزي في الوضع العربي: Ctrl+K/Appearance/tour/compare/dock، محرر الشركة/share/trade-show/landed/PDF، molecules، training/admin/deals/messages | اتصلح (اتحقق منه في الجولة 2) | `i18n.js` |
| F-63 | متوسط | مفيش زرار لغة في صفحات login/signup وصفحة signup نص مترجمة | اتصلح (اتحقق منه — خالف كلام الـ workstream) | `app.html` + `i18n.js` |
| F-64 | متوسط | التحويل من عربي لإنجليزي بيسيب الصفحات الـ cached (Marketplace/Jobs/Groups) وأكشن الـ feed بالعربي لحد reload | اتصلح (اتحقق منه في الجولة 2) | `i18n.js` + `brand.js` |
| F-65 | متوسط | SKIP selector '.pb-text' في i18n بيطابق banner الأسعار في الماركت فعمره ما بيتترجم | اتصلح | `i18n.js` |
| F-66 | متوسط | مفاتيح مكررة في قاموس الترجمة: 'Saved' في السايدبار بيطلع 'تم الحفظ'، و'Remove'/'Verified' بيتكتبوا فوق بعض | اتصلح (اتحقق منه) | `i18n.js` |
| F-67 | متوسط | شارة 'Ctrl K' فوق خانة البحث من غير حجز مساحة: النص بيدخل تحتها LTR وأول الحروف مخفية في RTL | اتصلح | `batch3.js` |
| F-68 | متوسط | مودال الـ boost عربي بس بأرقام هندية و'ج.م' حتى في الواجهة الإنجليزية، وcheckout.js بيضيف طرق دفع إنجليزي | اتصلح (اتكمّل بعدين) | `app.html` + `checkout.js` |
| F-69 | متوسط | molecules.js بيحط زرار 'Structure' جوه عنوان الإعلان فالـ share caption وقراءة العنوان بيبقوا '…GMP GradeStructure' | اتصلح | `molecules.js` + `molecules.css` |
| F-70 | متوسط | Google Fonts <link> في الـ head بيبلوك أول paint ويفشل offline، والخطين (Inter/Cairo) مش مستخدمين — العربي بيرندر بخطوط النظام | اتصلح (اتحقق منه في الجولة 3) | `app.html` (الخطوط بعد الـ load event، ومش بتتطلب offline، وبتتشال لو فشلت) |
| F-71 | متوسط | ملف الدخول 9.56 MB (64% فيديو splash base64 + لوجو مكرر 5 مرات): ~47 ثانية على Slow 4G | اتصلح (اتحقق منه في الجولة 2) | `splash_full.mp4` + `mobile_opt.py` + `live.py` (الـ scripts في `js/` بالـ hash) |
| F-72 | متوسط | تباين ألوان تحت WCAG AA: عناصر الـ ticker في a11y.css (1.5–3.2:1)، شارة مستوى التحقق (2.3:1)، تواريخ المشاهدين (2.9:1) | اتصلح (اتحقق منه) | `a11y.css` |
| F-73 | متوسط | حاسبة landed-cost بتطلع برّه الـ dialog على التابلت/الديسكتوب (عرض الـ Incoterm select بيكسر الجريد) | اتصلح | `landed.css` |
| F-74 | متوسط | الـ slug والـ monogram بيتعملوا في البراوزر: اسم عربي بس = لوجو فاضي وslug 'company-<timestamp>'، والأسماء المتشابهة بتعمل unique-violation خام | اتصلح (اتحقق منه في الجولة 3) | `directory.js` + `0025` (`companies_before_write`: الداتابيز بتزوّد -2، -3… للـ slug المتاخد) |
| F-75 | متوسط | live.py ما يقدرش يكتشف service_role JWT حقيقي (بيدور على النص الحرفي والـ role مشفر base64) | اتصلح | `web/build/live.py` |
| F-76 | متوسط | الـ gateway المحلي كله بيقع من Range header واحد غلط (ده سبب وقوع الـ stack المشترك أثناء الـ audit) | اتصلح | `gateway.mjs` |
| F-77 | متوسط | path traversal في محاكاة الـ storage: مستخدم مسجل يكتب/يقرأ/يمسح ملفات برّه STORE_DIR بصلاحية root | اتصلح | `gateway.mjs` |
| F-78 | متوسط | محاكاة الـ auth في الـ gateway مختلفة عن Supabase: JWT منتهي بيتحوّل anon بصمت بدل 401، apikey مش مطلوب، مفيش rate limit/recover/verify | جزئي | `gateway.mjs` |
| F-79 | متوسط | الـ stack المحلي: gateway/functions/mocks بتسمع على 0.0.0.0 والأسرار مكتوبة world-readable في /tmp (أي user محلي يزوّر service_role) | اتصلح | `gateway.mjs` + `mock-providers.mjs` + `start*.sh` |
| F-80 | متوسط | سكريبتات التشغيل: start.sh بيسجل PID غلط ويسيب gateway قديم (كل الطلبات 401)، ما بيضبطش DRUGBOX_REALTIME=0، وstart-payments.sh من غير error handling | اتصلح | `start.sh` + `start-payments.sh` |
| F-81 | متوسط | PostgREST المحلي من غير max-rows=1000 ولا statement timeouts، وفروق تانية بين الـ stub وSupabase الحقيقي بتخبي سلوك الإنتاج | جزئي | `start.sh` + `_local_supabase_stub.sql` |
| F-82 | متوسط | storage.foldername في الـ stub بتحتفظ باسم الملف (Supabase بتشيله) وأكتر تساهلاً: اختبارات policies المسارات مش بتكشف الأخطاء | اتصلح | `_local_supabase_stub.sql` + `gateway.mjs` |
| F-83 | متوسط | إعادة تشغيل migration بتتخطى policies بصمت (schema_sweep مش بيكشفها)، 0001 مش re-runnable وبيرجّع functions قديمة، وnotify ناقص/مكرر | جزئي | `tools/migration_check.py` + تقسيم الـ DO blocks في 0007–0021 (G2) |
| F-84 | متوسط | signup بيكشف إن الإيميل مسجل قبل كده (user enumeration) | اتصلح | `gateway.mjs` |
| F-85 | متوسط | اختبار b1 'cannot change another person's profile' فاضي في كل تشغيل بعد الأول (إيميل ثابت other@x.test) | اتصلح | `tests/e2e/b1_auth_test.py` |
| F-86 | متوسط | deals.rls.sql: الاختبارات السلبية بتعدّي لسبب غلط أو فاضية (عنوان حرف واحد، ref = NULL تحت RLS) | اتصلح | `supabase/tests/deals.rls.sql` |
| F-87 | متوسط | SQL harness: أي خطأ غير متوقع بيلغي الـ transaction ويمسح التقرير كله وpsql بيخرج 0 | اتصلح | الـ 4 SQL suites (harness مشترك) |
| F-88 | متوسط | ولا suite تقدر تفشّل CI: كل اختبار بيطبع 'N / N' ويخرج 0، ومفيش runner | اتصلح | `tests/run_all.py` + `tests/e2e/_dx.py` |
| F-89 | متوسط | e4_payments_test: أسبقية العوامل بتخلي فحص الـ direct-INSERT tampering dead code | اتصلح | `tests/e2e/e4_payments_test.py` |
| F-90 | متوسط | E4 payments: مسارات replay/amount/ownership مش مختبرة (Fawry replay، boost لإعلان غيرك، receipt-path spoof، reject) | اتصلح | `tests/e2e/e4_payments_test.py` |
| F-91 | متوسط | الـ e2e عمرها ما بتشغّل الواجهة العربية/RTL | اتصلح | `tests/e2e/b0_rtl_smoke_test.py` |
| F-92 | متوسط | الاختبارات مقفولة على المحاكي المحلي وملفات برّه الريبو (/tmp/vids، /tmp/drugbox-fn.env، psql socket، رسايل الـ gateway) | اتصلح | `tests/e2e/_dx.py` + `tests/fixtures/make_fixtures.py` |
| F-93 | متوسط | b3_network_test.py بيعمل SyntaxError على Python < 3.12 | اتصلح | `tests/e2e/b3_network_test.py` |
| F-94 | منخفض | handle_new_user: من غير search_path، بيفشل للتسجيل بدون إيميل، وبيقبل اسم فاضي | اتصلح | `0020_security_core.sql` |
| F-95 | منخفض | companies_guard سايب follower_count/source/created_at/slug وregistry (وهي pending) قابلين للكتابة من الفريق | اتصلح | `0020_security_core.sql` |
| F-96 | منخفض | companies.status الافتراضي 'verified': صفحات الـ admin أو الـ imports بتاخد شارة Verified من غير مراجعة | اتصلح | `0020_security_core.sql` |
| F-97 | منخفض | مسارات الملفات الخاصة (verification_requests paths، evidence_path) وحقول المراجعة مش متحقق منها عند الـ insert: licence وهمي بيعمل licensed=true | اتصلح | `0023_payments_moderation_storage.sql` |
| F-98 | منخفض | bucket reference-evidence من غير حد حجم ولا MIME allow-list ولا delete policy | اتصلح | `0023_payments_moderation_storage.sql` |
| F-99 | منخفض | فهرس paging في 0010 مش بيتعمل بصمت (تصادم اسم مع 0001)، وفهارس مكررة/غير مستخدمة على أكتر الجداول كتابة | اتصلح | `0022_integrity_perf.sql` |
| F-100 | منخفض | is_company_member() بتتجاهل company_members.accepted: الشخص بياخد صلاحية الفريق قبل ما يوافق | اتصلح | `0021_trust_hub_deals.sql` |
| F-101 | منخفض | profiles.followers_count وenquiries.reply_count عمرهم ما بيتحدثوا (دايماً 0) | اتصلح | `0020_security_core.sql` |
| F-102 | منخفض | comments.post_id nullable: تعليقات يتيمة بتعدّي RLS وبتتخطى العداد | اتصلح | `0020_security_core.sql` |
| F-103 | منخفض | صفوف A→B وB→A في connections ممكن يتعايشوا وبيتحسبوا مرتين | اتصلح | `0020_security_core.sql` |
| F-104 | منخفض | عدادات المشاهدة/المشاركة/زيارات البروفايل قابلة للنفخ بلا حد، حتى من anon | اتصلح | `0020_security_core.sql` |
| F-105 | منخفض | flooding غير محدود للطلبات والإشعارات عن طريق deal_create | اتصلح | `0021_trust_hub_deals.sql` |
| F-106 | منخفض | طلبات بتتبعت لشركات unclaimed (محدش يقدر يرد) ومن شركات suspended | اتصلح | `0021_trust_hub_deals.sql` |
| F-107 | منخفض | buying group مفتوحة مستحيل تتلغي أو تترفض، وسعر 'To be confirmed' بيعمل orders بحالة accepted | جزئي | `0021_trust_hub_deals.sql` |
| F-108 | منخفض | search_companies وcompany_sites_public بيرجّعوا شركات suspended (والدليل مخفيها) وكل الأعمدة | اتصلح | `0021_trust_hub_deals.sql` |
| F-109 | منخفض | directory_companies بتسقط شركات بشكل عشوائي لما يزيدوا عن p_limit (LIMIT بدون ORDER BY) | اتصلح | `0021_trust_hub_deals.sql` |
| F-110 | منخفض | RLS predicate بتاع messages بيخلي conversation_messages/new_messages تعمل scan لكل رسايل المستخدم بدل idx_msgs_pair | اتصلح | `0022_integrity_perf.sql` |
| F-111 | منخفض | صفحات الـ feed العميقة O(scroll depth): فلتر الـ cursor بصيغة OR ما بيستخدمش idx_posts_created_id | اتصلح | `web/src/live/adapter.js` |
| F-112 | منخفض | get_reviews_many بتكتب not coalesce(r.hidden,false) فبتعطّل الفهرس الجزئي → full scan لـ job_reviews مع كل فتح لـ Jobs | اتصلح | `0022_integrity_perf.sql` |
| F-113 | منخفض | خمس write policies بتستخدم auth.uid() مباشرة بدل (select auth.uid()) | اتصلح | `0020_security_core.sql` |
| F-114 | منخفض | review_instapay(p_ok=false) بيبعت إشعار للعميل حتى لو الطلب مش في review (مدفوع مثلاً) | اتصلح (اتحقق منه) | `0023_payments_moderation_storage.sql` |
| F-115 | منخفض | Paymob callback بيربط الطلب بحقل غير موقّع (merchant_order_id)، العملة مش بتتفحص، وprovider_ref مش unique | اتصلح (اتحقق منه في الجولة 2) | `0023` + `0024` §1 + `paymob-webhook` + `fawry-webhook` + `payments-create` |
| F-116 | منخفض | webhook من مزود الدفع يقدر يأكد طلب InstaPay لسه في 'review' متخطياً موافقة الأدمن | اتصلح (اتحقق منه) | `0023_payments_moderation_storage.sql` |
| F-117 | منخفض | مفيش security headers (CSP, X-Frame-Options, HSTS, X-Content-Type-Options) — CSP متوافقة مع الـ inline scripts ممكنة | اتصلح | `gateway.mjs` + `vercel.json` |
| F-118 | منخفض | حالات حافة في checkout.js: الـ dialog بيتشال قبل الطلب، المنتج بيتقرأ من نص الـ dialog، InstaPay dialog بيتقفل قبل نتيجة الرفع | اتصلح | `checkout.js` |
| F-119 | منخفض | poller بتاع الرجوع من الدفع بيلف للأبد كل 800ms لو المستخدم مش مسجل | اتصلح | `web/src/live/adapter.js` |
| F-120 | منخفض | friendly() بتعرض رسايل PostgREST/Postgres خام وبتصنّف أي رسالة فيها 'network' كمشكلة اتصال | اتصلح | `web/src/live/adapter.js` |
| F-121 | منخفض | الأعضاء العاديين (member/hr/sales) الواجهة بتعاملهم كـ owners والداتابيز بترفض بأخطاء خام | اتصلح | `web/src/live/adapter.js` |
| F-122 | منخفض | ترقية VIP من غير دفع بتظهر VIP طول الجلسة (snapshot overlay) مع رسالة 'payments open at launch' رغم إن الدفع موجود | اتصلح | `web/src/live/adapter.js` |
| F-123 | منخفض | مفتاح storage لمرفق الرسالة بياخد الامتداد من اسم الملف من غير sanitising (عكس extOf للمستندات) | اتصلح | `web/src/live/adapter.js` |
| F-124 | منخفض | البناء غير deterministic وبيوسّخ ملفات tracked (lite snapshot، _static.html، أرقام count-up نص الأنيميشن)، والـ live build المحفوظ أقدم من الديمو | اتصلح (اتحقق منه) | `snapshot.py` + `build.py` |
| F-125 | منخفض | البناء بيشحن snapshot قديم بصمت لو Playwright ناقص، وبيسيب drugbox.html ناقص لو Pillow ناقص | اتصلح | `build.py` + `mobile_opt.py` |
| F-126 | منخفض | ~400 سطر كود الدليل القديم (pre-hub) dead ورا dxHub.render()، و6 legacy suites بتستهدفه ومستحيل تعدّي (وواحدة live test بتكتب في الداتابيز المشتركة) | اتصلح (اتكمّل بعدين) | `directory*.js` + `tests/demo/legacy/retired/` |
| F-127 | منخفض | RTL: خصائص CSS فيزيائية left/right (sponsored cards، drawer المحرر، deals timeline، login box)، ticker بـ translateX يفترض LTR، وسهم '→' مش بيتعكس | اتصلح (اتكمّل بعدين) | `deals.css`/`directory*.css`/`hub.css`/`tiers.css` + `i18n.js` (ticker) |
| F-128 | منخفض | نصوص طويلة بدون overflow-wrap: URL في About واسم الهوية في السايدبار بيعملوا scroll أفقي ومخفيين في RTL | اتصلح (اتكمّل بعدين) | `directory.css` + `.me-name` |
| F-129 | منخفض | dialog الـ group-buying على الموبايل: زرار Join/Add بيطلع برّه المودال (flex:1 بدون min-width:0) | اتصلح | `directory3.css` |
| F-130 | منخفض | أهداف لمس صغيرة (chip ×، compare-tray ×، saved-search ×، Edit my intents) أقل من 24×24 | اتصلح | `batch2.css` + `craft.css` |
| F-131 | منخفض | فجوات هيكل الوصول: مفيش <main>، خمس صفحات بدون heading، <nav> بدون label، document title ثابت | اتصلح | `app.html` |
| F-132 | منخفض | Escape handler العام بيعمل stopPropagation فـ Escape بتاع الـ base (lightbox/.modal-bg) ما بيشتغلش والنافذة الـ cached مفتوحة | اتصلح | `core.js` |
| F-133 | منخفض | تفضيلات localStorage بتتطبق بدون validation: dx_theme تالف بيكسر قائمة Appearance، dx_role غير معروف بيقتل الـ boot | اتصلح | `brand.js` + `batch3.js` |
| F-134 | منخفض | videos.js بيعمل insertAdjacentHTML بعد ما البروفايل اتعمله re-render: 'element has no parent' وNoModificationAllowedError | اتصلح | `videos.js` |
| F-135 | منخفض | closeGroup() بيرمي exception لما صفحة Groups مش mounted (من غير null guard) | اتصلح | `app.html` |
| F-136 | منخفض | hub-data store(): الحفظ اللي بيفشل (localStorage مليان) بيتبلّغ كنجاح 'Site added' | اتصلح | `hub-data.js` + `directory.js` + `deals.js` |
| F-137 | منخفض | بيانات مخزنة بشكل غلط بترمي exception جوه الـ render: answers مش array بتبوّظ الـ thread، sites مش array بتبوّظ صفحة Companies | اتصلح | `deals.js` + `hub-data.js` + `directory2/3.js` |
| F-138 | منخفض | Admin → Review في الديمو: 'Mark checked' على شهادة موقع مش بيثبت (key mismatch) | اتصلح | `moderation.js` |
| F-139 | منخفض | تصدير CSV لقائمة الموردين: الأسماء مش quote-escaped والخلايا اللي بتبدأ بـ = + - @ مش محيّدة (CSV injection) | اتصلح | `directory3.js` |
| F-140 | منخفض | خصم الـ surplus مش محدود: '−150%' بيتقبل (max=95 attribute بس) | اتصلح | `directory3.js` |
| F-141 | منخفض | قائمة 'acting as' في الـ topbar مش بتتحدث بعد تغيير اللوجو/اللون (drawSwitch بيتجاهلهم) | اتصلح | `directory.js` |
| F-142 | منخفض | Share card 'Copy caption' بيقول 'Copied ✓' حتى لو Clipboard API وexecCommand فشلوا | اتصلح | `share.js` |
| F-143 | منخفض | الربط التلقائي لأسماء الشركات بيطابق أجزاء كلمات: 'Quadra Pharm' جوه 'Quadra Pharmaceuticals International' | اتصلح | `directory.js` |
| F-144 | منخفض | حقل 'Unit' في landed-cost بيتكتب في innerHTML بدون escape (self-XSS sink) | اتصلح | `landed.js` |
| F-145 | منخفض | تاريخ تجديد VIP بـ setMonth(+1): 31 يناير بيتجدد 3 مارس | اتصلح | `directory.js` |
| F-146 | منخفض | رفع فيديو بـ MIME فاضي بيترفض 'Use an MP4, WebM or MOV' حتى لو MP4 | اتصلح | `videos.js` |
| F-147 | منخفض | الجمع والأرقام والتواريخ: WORDS map بتتجاهل العدد، التواريخ بلغة البراوزر، تسمية العملة مش متسقة | اتصلح | `i18n.js` + `deals.js`/`hub-ui.js` |
| F-148 | منخفض | عربي غير طبيعي أو غير متسق: 'Connect'→'اتصال'، 'Message'→'رسالة'، 'Upgrade Now'→'رقِّ الآن'، Senior=Expert='خبير' | اتصلح | `i18n.js` |
| F-149 | منخفض | نصوص المستخدم الإنجليزية مش معزولة bidi في العربي (dir=auto/<bdi>): علامات الترقيم والأوقات بتتعكس | اتصلح | `i18n.css` |
| F-150 | منخفض | parity_check.py بيقول PARITY OK لملفين فاضيين أو مقطوعين لما الـ markers ناقصة | اتصلح (اتحقق منه) | `tools/parity_check.py` |
| F-151 | منخفض | أسماء وبيانات تواصل لأشخاص وشركات حقيقية منسوب ليهم كلام مخترع في بيانات الديمو | جزئي (اتحقق منه) | `app.html` + `batch2.js`/`batch3.js` |
| F-152 | منخفض | نفس الشخص بلونين avatar وheadline مختلفين (ME وUSERS[0] مش متطابقين) | اتصلح | `app.html` |
| F-153 | منخفض | الـ no-JS lite snapshot فيه ids مكررة وh1 مركّب | اتصلح | `snapshot.py` |
| F-154 | منخفض | .gitignore مش مغطي *.env variants ولا __pycache__/*.pyc/*.log | اتصلح | `.gitignore` |
| F-155 | منخفض | الوثائق مش مطابقة للكود: README وroadmap قديمين، اسم DB مش موثق، DATA-CONTRACT.md فيه جداول مش موجودة | اتصلح | `README.md` + `docs/DATA-CONTRACT.md` |
| F-156 | منخفض | assertions مش بتختبر اللي بتدّعيه: الأخطاء السلبية بتقبل أي error، e1b على dialog مفبرك، videos_test self-fulfilling، d1 'newest first' بس presence | اتصلح | `tests/e2e/_dx.py` + الـ suites |
| F-157 | منخفض | 289 sleep ثابت مقابل 3 condition waits — المصدر الرئيسي للـ flakiness | جزئي | `tests/e2e/_dx.py` |
| F-158 | منخفض | مفيش اختبار إن الصفحات اللي بتعيد تعريف دوالها (messages/jobs/boost) بتفضل wrapped بعد render تاني | اتصلح | `b4`/`d2a`/`e4b` e2e |
| F-159 | منخفض | تصادم إيميلات بنفس الثانية بين suites بتتشغل متوازي (c2 vs d1) | اتصلح | `tests/e2e/_dx.py` |
| F-160 | معلوماتي | SQL suites بتفترض داتابيز فاضية وبتغطي role authenticated بس | اتصلح | `company_hub`/`deals`/`listings_groups` .rls.sql |
| F-161 | معلوماتي | schema_sweep.sql: فحص العدادات بالاسم، ومفيش sweep للـ RPCs الـ security-definer المتاحة لـ anon ولا لـ storage policies | اتصلح | `schema_sweep.sql` |
| F-162 | معلوماتي | تكلفة طبقات الـ layers على تبديل الصفحات (baseline لقاعدة 'never slower') | ملاحظة | قياس بس |
| F-163 | معلوماتي | فهارس GIN للـ full-text على posts/products مش مستخدمة وبإعدادات 'english' (مفيش عربي) | اتصلح | `0020_security_core.sql` |
| F-164 | معلوماتي | ملاحظات: مفيش UPDATE policy على posts (زرار Pin بتاع الأدمن client-only)، المستخدم يقدر يزوّر notifications، enquiries.id من العميل | اتصلح | `0020_security_core.sql` |
| F-165 | معلوماتي | get_ratings() بتجمّع وترتّب جدول job_reviews كله مع كل نداء حتى لو ids متبعتة | اتصلح | `0020_security_core.sql` |
| F-166 | معلوماتي | conversation_heads مش بتتحدث عند مسح رسالة | اتصلح | `0022_integrity_perf.sql` |
| F-167 | معلوماتي | orders بتاعة confirm_group فيها event 'sent' من جهة الـ from مكتوب باسم المورّد، وTRUNCATE سايب على جداول المحرك | اتصلح | `0021_trust_hub_deals.sql` |
| F-168 | معلوماتي | الـ moderators (role='moderator') ما بيشوفوش طلبات التحقق ولا البلاغات ولا المستندات — Admin → Review فاضي ليهم | اتصلح | `0021_trust_hub_deals.sql` |
| F-169 | معلوماتي | buckets العامة videos وpost-media بتسمح لـ anon يعمل list لكل الكائنات (user-id enumeration) | اتصلح | `0020_security_core.sql` |
| F-170 | معلوماتي | تحصين بسيط في الدفع: CORS '*' على payments-create، حالة enrollment 'completed' مش قابلة للوصول، الـ mock بيسجل secret المزود | اتصلح (اتكمّل بعدين) | `payments-create` + `mock-providers.mjs` |
| F-171 | معلوماتي | موبايل: شريط الـ undo بيغطي input الـ chat dock المفتوح | اتصلح | `batch2.css` |
| F-172 | معلوماتي | supabase-js 2.45.4 الـ vendored أصلي؛ auth-js 2.65.0 فيه advisory واحد low (GHSA-8r88-6cj9-9fh5) | متأجل | `README.md` (ملاحظة إطلاق) |
| F-173 | معلوماتي | live.py بيحقن DRUGBOX_CONFIG في inline <script> بـ json.dumps من غير escape لـ '<' أو '</script>' | اتصلح | `web/build/live.py` |
| F-174 | معلوماتي | مسارات كود ميتة بتشاور على ids مش موجودة (chatPanel, ptab-activity, jobsList) | اتصلح | `app.html` |
| F-175 | معلوماتي | بيانات الديمو متجمدة في أوائل 2025: الوظائف الست مواعيدها فاتت ومعروضة بالأحمر كمفتوحة | اتصلح | `app.html` |
| F-176 | معلوماتي | تاب الـ honour-reference بيعرض حقل 'Evidence document (required)' زيادة | اتصلح | `web/src/live/adapter.js` |
| F-177 | معلوماتي | صلاحيات الجداول أوسع من الـ policies والـ sequences قابلة للكتابة من anon (hardening) | اتصلح | `0020_security_core.sql` |
| F-178 | معلوماتي | PgBouncer/Supavisor transaction mode: مفيش مخاطر في الـ SQL؛ PostgREST وRealtime محتاجين direct connections (يتوثق في runbook الإطلاق) | اتصلح | `README.md` (ملاحظات الإطلاق) |

## 5. المتأجل والجزئي

### 5.1 قبل production

مفيش بند كود موقِّف للإطلاق. اللي فاضل قبل production خطوات بيئة ما تتعملش غير على Supabase حقيقي:

| ID | اللي فاضل | ليه | الخطوة الجاية |
|---|---|---|---|
| F-04 | `GET /deals` محليًا median 33–40 ms والهدف ≤ 25 ms، والـ payload 429 KB | الحكم الحقيقي محتاج Supabase المستضاف والـ k6، والجهاز المحلي عليه Chromium وPostgres مع بعض | k6 على staging (خطوة 11 في القسم 7). لو لسه فوق الهدف: نقلّل الـ limit ونجيب الـ events عند فتح الصفقة بس |
| F-78 / F-81 | المحاكي المحلي مختلف عن Supabase: مفيش rate limits ولا /recover ولا /verify، والـ superuser والـ collation وحدود الخطة مختلفين | محتاجين مشروع حقيقي | يتجربوا على staging (خطوات 1 و11 في القسم 7) |
| F-172 | `supabase-js` 2.45.4 و`auth-js` 2.65.0 عليه advisory واحد low | متأجل لحد الإطلاق | نحدّث لآخر 2.x قبل الـ build ونعيد b1 وb4 وe4b (خطوة 7) |

### 5.2 قرارات محتاجاك

| ID | السؤال | الوضع دلوقتي |
|---|---|---|
| F-26 | المحتوى (البوستات والوظايف والإعلانات والجروبات) يتقري من غير تسجيل؟ | **اتقفل privacy-first:** الـ anon مش بيقرا حاجة غير الأسعار والإعدادات والـ ticker والكورسات، والـ live مش بيقرا حاجة قبل الـ session. لو عايز صفحات عامة (SEO)، كل جدول بيرجع بسطر واحد `alter policy "<اسم الـ policy>" on public.<table> to public;` (الأسماء مكتوبة في 0024). ومستندات الشركات بقت للمسجّلين بس في 0025 (N-7)، والرجوع: `alter policy "documents: everyone reads metadata" on public.company_documents to public;` |
| F-34 | `moderate_review()` موجودة ومش متوصّلة بواجهة | نزوّد تبويب Reviews في Admin → Review (تغيير في الواجهة)، أو نسيبها للدعم من SQL |
| F-107 | سعر "To be confirmed" في الـ buying group لسه بيعمل orders، ومفيش أزرار cancel/decline للجروب المفتوح | خطوة في الواجهة تطلب سعر رقمي قبل confirm، وأزرار cancel/decline (تغيير في الواجهة) |
| F-151 | "Dr. Asmaa Meabed" موجودة 38 مرة في الديمو | زميلتك، فمحدش غيّر الاسم من غير قرارك: نسيبه أو نغيّره لاسم خيالي |
| N-6 | الـ Boost المدفوع بيغيّر الترتيب بس، ومفيش علامة على الكارت | نحط علامة "مميّز" ظاهرة (تغيير في الواجهة)، ولا يكفي الترتيب |
| F-11 (ذيل) | الـ honor references بتتنشر على طول | تتنشر على طول ولا تعدّي على مراجعة |
| الأسعار | boost EGP 1,450 / 7 أيام وfeatured EGP 3,950 / 30 يوم قبل الـ VAT 14% | تأكيد. ورسالة تأكيد الديمو بتقول "7 days" للاتنين، وده كان كده في المعتمد |

### 5.3 جزئي متساب (منخفض، مش موقِّف)

| ID | اللي فاضل | ليه | الخطوة الجاية |
|---|---|---|---|
| F-83 | `0001_init.sql` مش re-runnable ومن غير `notify pgrst` في الآخر (و0014 فيها notify مرتين، من غير ضرر) | 0001 هي الـ schema الأساسية وبتتشغل مرة واحدة. `migration_check` بيعرف ده ومطلّع OK للـ 25 | ما نعيدش تشغيل 0001 أبدًا. ممكن نزوّد سطر notify في آخرها |
| F-157 | لسه فيه sleeps ثابتة كتير في الـ e2e (dialogs وreloads) | الـ CSP بتمنع `wait_for_function`، فاتعمل `_dx.wait_for` | نبدّلهم تدريجيًا. الـ e2e عدّت 21 / 21 مرتين على stack جديد في R3-gate |

F-70 وF-74 اتشالوا من هنا: اتقفلوا في الجولة التالتة (3.3).

### 5.4 متأجل

| ID | ليه | الخطوة الجاية |
|---|---|---|
| F-45 | 50 like متزامنين على نفس البوست بيستنوا lock صف البوست. السقف حوالي 120–170 like/s للبوست الواحد، وده أعلى بكتير من أي حاجة هتحصل في شبكة B2B | نعيد التصميم (delta table) بس لو الـ k6 أو الإنتاج ورّوا ضغط فعلي |
| F-172 | `supabase-js` 2.45.4 أصلي، و`auth-js` 2.65.0 عليه advisory واحد low (`auth.admin`، service role بس) | نحدّث لآخر 2.x قبل E5 ونعيد b1 وb4 وe4b |
| F-162 | قياس بس (baseline للسرعة) | — |

### 5.5 المشاكل الجديدة من الجولة الأولى: حالتها

| ID | المشكلة | الحالة |
|---|---|---|
| N-1 | تراجع في سرعة `my_interactions()` (135–220 ms عند 20k صفقة) | **اتقفل** في 0024: 6–9 ms (اتحقق منه) |
| N-2 | البحث عن الشركة بأول الاسم في `links.js` و`afford.js` | **اتقفل** في `links.js` و`afford.js` (اتحقق منه). وذيل الأشخاص (N-10) اتقفل في الجولة التالتة |
| N-3 | ملف adapter قديم في `web/dist/live/js` | **اتقفل**: `live.py` بيمسح أي ملف مش مطلوب (اتحقق منه) |
| N-4 | الأدمن مالوش طريق يغيّر `profiles.verified` لشخص | **اتقفل** في 0024: الأدمن يغيّر verified والدور ونوع الحساب بس (اتحقق منه) |
| N-5 | `#dxEditor` من غير `aria-modal=true` | **اتقفل** في `directory.js` (اتشاف في فحوص r2-ui) |
| N-6 | الـ Boost المدفوع من غير علامة على الكارت | قرارك (5.2) |

### 5.6 المشاكل الجديدة من الجولة التانية: حالتها

| ID | المشكلة | الحالة |
|---|---|---|
| N-7 | الـ anon يقدر يقرا بيانات مستندات الشركات (النوع والمنتج والرقم والـ expiry والحالة، من غير الملف) | **اتقفل** في 0025: الـ policy بقت للمسجّلين بس، والـ anon بياخد 0 صف من الجدول والـ view (اتحقق منه، 3.3). والرجوع بسطر واحد لو قررت تخليها عامة (5.2) |
| N-8 | الدعوة للجروب الخاص مش بتعمل إشعار | **اتقفل** في 0025: trigger على `group_invites` بيعمل إشعار `group_invite` واحد، وبيتشال لو الدعوة اتسحبت أو اترفضت من غير انضمام، ومع الجروب (`notifications.group_id`). والـ live بيعرضه بالإنجليزي والعربي (اتحقق منه) |
| N-9 | زرار الدعوة والـ toasts بتاعة الجروبات إنجليزي في العربي | **اتقفل** في `i18n.js`، ومعاها شباك Create a Group ورسايل الفورم (اتحقق منه) |
| N-10 | `afford.js user()` بيدوّر على الأشخاص بأول الاسم | **اتقفل**: الاسم بالظبط أو الاسم + فاصل، والأطول بيكسب (اتحقق منه). ذيل: N-14 |

**مش مشكلة في المنتج:** سكريبت تحقق الجولة الأولى (`V-db/v1.sql`) لو اتشغل زي ما هو بيقول إن F-16 مكسور وF-32 مفتوح. الأولى لأن F-17 بقى بيسمح بمسح حساب المورّد في نص السكريبت، والتانية لأن الفحص بيعتبر update بـ 0 صف نجاح. بعد ترتيبه وفحص الحالة (`v1b.sql`) طلع 58 / 58 و39 / 39. ده يهم بس لو حد استخدم السكريبت ده تاني.

### 5.7 مشاكل جديدة طلعت في الجولة التالتة (كلها منخفضة)

- **N-11 (ذيل F-74، في الـ adapter):** لو الداتابيز زوّدت لاحقة لـ slug شركة جديدة (x بقت x-2)، براوزر اللي عملها بيفضل شايفها بـ x لحد reload، لأن `persistCreated` بيخزّن `CO.raw` و`CO.byId` بالـ slug بتاع البراوزر ومش بياخد `ins.data.slug` (`web/src/live/adapter.js:704-709`). التعديلات بتروح للصف الصح لأنها بالـ id، وبعد reload كله مظبوط. بس لحد الـ reload، لينك أو صفقة بالـ slug ده بتشاور على الشركة التانية، ولو الشركة التانية اتحمّلت في الدليل ممكن تغطي على الكارت المحلي. ده بيحصل بس لو شركتين بنفس الاسم اتعملوا في نفس اللحظة، أو الاسم متاخد لشركة المستخدم مش شايفها. الحل: الـ adapter ياخد الـ slug بتاع السيرفر ويغيّره في القايمة الحية و`CO.raw` و`CO.byId` و`dx_acting`، وصفحة الشركة المفتوحة بالـ slug القديم تفضل شغالة، ومعاه e2e جديد للتصادم.
- **N-12 (ذيل F-74، في الداتابيز):** الـ lock على الـ slug الأساسي، فلو اسم محتاج x-4 وشركة تانية الـ slug بتاعها أصلًا x-4 (اسمها "X 4") اتعملوا في نفس اللحظة بالظبط، واحدة بتاخد 409 (23505)، في 6 من 6 جولات في اختبار مصطنع. نادر جدًا، والواجهة بترجّع الإنشاء وبتطلع toast. الحل لو لزم: retry مرة في الـ trigger، أو lock على الـ slug النهائي.
- **N-13: toast التسجيل "Welcome to Drugbox, <الاسم>!"** (`app.html:2315`، `doSignup`) مالوش pattern عربي في `i18n.js`، فبيفضل إنجليزي للمستخدم العربي في الديمو والـ live. الحل سطر في القاموس وrefresh للمرجع.
- **N-14 (ذيل N-10):** `afford.js user()` بيعتبر "-" فاصل، فاسم أطول بشرطة زي "Sara Nabil-Fahmy" لسه بيفتح "Sara Nabil" لو هي بس الموجودة. الحل نشيل "-" من الفواصل.
- **ملاحظات من R3-gate، متسابة زي ما هي:** وصف "New group" الافتراضي على كارت الجروب الجديد بيفضل إنجليزي في العربي، لأن `.gcard-desc` متساب من الترجمة كنص بيكتبه الناس. والكليك على إشعار الدعوة بيفتح بروفايل اللي بعتها مش الجروب، لأن الواجهة المعتمدة مالهاش route لإشعار جروب.

### 5.8 ذيول في بنود اتقفلت

- F-11: الـ live لسه مالوش مكان يكتب فيه `profiles.experience` أو `open_to_work`، فالـ work references هتشتغل لما يبقى فيه محرر بروفايل. والـ honor references بتتنشر من غير مراجعة (قرارك، 5.2).
- F-29: الإشعار (N-8) والعربي (N-9) اتعملوا. الكليك على الإشعار بيفتح بروفايل اللي دعاك مش الجروب (5.7).
- F-30: الـ plan الخام بيفضل `vip` لحد ما pg_cron يتفعل، بس محدش بيقراه.
- F-40: عضو HR لسه يقدر يقبل quote ملزم للشركة (نموذج الأدوار ماتغيّرش).
- F-09: الـ id اللي البراوزر يبعته وأصغر من الـ sequence لسه بيتقبل، ومن غير أثر.
- F-70: لو سيرفر الخطوط واصل بس بيرفض الطلب، بيتسجّل ERR_FAILED واحد في الـ console، وده طبيعي.
- F-71: اللوجو (28 KB) موجود مرتين في الـ live `index.html` (splLogo وformLogo).
- F-74: البراوزر بيفضل على الـ slug القديم لحد reload (N-11)، وتصادم نادر بين اسمين مختلفين (N-12).
- F-132: فحص UI قديم (`verify.py`) لسه بيطلّعه FAIL لأنه بيتوقع Escape واحدة تقفل حاجتين. السلوك الحالي مقصود (F-59) واتشيّك (3.2).

## 6. تغييرات الواجهة اللي محتاجة موافقتك

كل التغييرات دي مقصودة. تغييرات الجولة الأولى (1–18) G1 راجعها بالصور قديم مقابل جديد بالإنجليزي والعربي. ما طلعش أي JS error، ولا شكل اتكسر، ولا جزء اختفى. وبعدها اتنسخت على `web/reference/demo-approved.html`. لو رفضت أي حاجة منهم، بنرجّعها ونعمل refresh للمرجع.

**ظاهرة في الديمو:**
1. زرار لغة في صفحات الدخول والتسجيل (F-63)، وصفحة التسجيل بقت عربي كامل.
2. شباك الـ Boost بيمشي مع لغة الواجهة. بالإنجليزي من الشمال لليمين ومكتوب "EGP 1,653"، وبالعربي "ج.م" بأرقام لاتيني. ورسالة التأكيد بعد الدفع كمان بتمشي مع اللغة (F-68).
3. الأشخاص والشركات الخيالية اتغيرت أساميهم: Allison Wang بقت Vivian Zhou، وM. Musthafa بقى F. Rahmani، وAurobindo بقت Indovista، وEpione بقت Azurea، وShandong Hope بقت Shandong Hexa، وMinapharm بقت Nilevale، وEIPICO بقت Qarun Pharma، وZhejiang NHU بقت Zhejiang Lanhe، وAl Hayat بقت Al Sarab. والتليفونات والإيميلات الحقيقية اتشالت (F-151).
4. التواريخ اتنقلت لـ 2026/2027: مواعيد الوظايف من 15 يناير لـ 1 فبراير 2027، و© 2026. وشهادة ISO 9001 فضلت "expired" زي المعتمد (F-175).
5. صورة "أنا" في الـ composer والكومنتات بقت زرقا زي بوستاتك (F-152).
6. الـ ticker العربي بيتحرك من اليمين، والأسماء الطويلة في السايدبار بتلف بدل ما تتقطع (F-127، F-128).
7. ألوان الـ ticker وشارات مستوى التحقق اتغيرت عشان التباين يوصل لـ AA (F-72).
8. الدليل بيعرض 60 كارت وتحتهم زرار "Show more (60 of N)" (F-24).
9. Reject وDismiss وNot received في Admin → Review بقوا يطلبوا تأكيد بزرار أحمر، وCancel على سبب الرفض مبقاش بيرفض (F-60).
10. طلب عرض سعر من غير صفحة شركة بيطلّع "Create or claim your company page first"، وصفحتك مبقتش تعرضلك زرار Request (F-57).
11. Escape بيقفل النافذة اللي فوق بس، والـ focus بيرجع للزرار اللي فتحها. والمحرر بيسأل "Discard your changes?" لو فيه تعديلات (F-59، F-132).
12. الدرج في المحرر بيطلع من ناحيته في العربي، وسهم الـ deal بيتعكس (F-127). ومسافة جنب شارة "Ctrl K" في خانة البحث (F-67).
13. كلمة "Structure" على الـ chip بقت بتترسم بالـ CSS، فالـ share caption مبقاش فيه "…GMP GradeStructure" (F-69).
14. الكلام الإنجليزي اللي بيكتبه الناس بقى معزول اتجاهه في العربي. وصيغ الجمع والتواريخ بقت بلغة الواجهة، بأرقام لاتيني (F-147، F-149).
15. فيديو الـ splash اتضغط تاني بنفس الشكل والمقاس، والملف نزل من 9.56 MB لـ 5.51 MB (F-71).

**في الـ live بس:**
16. السعر في شباك الدفع بييجي من `payment_products`: EGP 1,450 + 14% = 1,653 للـ boost، و3,950 + 553 = 4,503 للـ featured. مبقاش USD × سعر صرف (F-07).
17. محاكاة الديمو مبقتش شغالة في الـ live: For you، وinsights، وشارات الإعلانات، والرد المفبرك في الـ dock، وكروت "Who viewed" و"Search appearances" (F-22، F-54).
18. "Claim this page" بيفتح dialog يسأل عن الدور والموبايل وإيميل الشغل، والطلب بيروح لـ Admin → Review (F-42).

**اتضاف في الجولة التانية.** R2-G1 راجعهم بالصور: 18 شاشة × إنجليزي وعربي × 1440 و390 px، و0 JS errors، ومفيش scroll أفقي. وبعدها اتنسخوا على المرجع (`c642b397`):

**ظاهر في الديمو:**
19. في تبويب Contact لصفحة الشركة بالعربي، الجملة اللي بتقول مين بيرد على الـ questionnaires وطلبات التوظيف بقت عربي (F-62).
20. في نشاط الماركت بالعربي، "listed" بقت **"أدرج"**، و"commented:" بقت **"علّق:"** (F-62).
21. حاجات بالعربي من غير ما الشكل يتغيّر: tooltip "افتح صفحة <الشركة>"، وأفعال الصفقات جوه الإشعارات (عدّل العرض، اسحب الطلب، وقّع اتفاقية السرية…)، وplaceholders المحرر (F-62). ومحرر الشركة بقى `aria-modal` (N-5).

**في الـ live بس:**
22. Companies بتعرض أول 100 شركة، وزرار "Show more" المعتمد بيجيب الـ 100 اللي بعدهم، والبحث بيسأل السيرفر. والرجوع للصفحة خلال دقيقتين مش بيعمل request (F-05).
23. زرار الدعوة في الجروب الخاص بيحفظ الدعوة فعلًا، والـ toast المعتمد بيطلع بعد ما الحفظ ينجح. ولو الاسم مش لعضو في Drugbox بيطلع "No Drugbox member found for …" (F-29).
24. في Reports بتاعة الشركة، "Mark fixed" مبقاش بيقفل البلاغ: الحالة بترجع، وبيطلع toast "Thanks — Drugbox checks the page and closes the report" (F-32).
25. زرار Review في Jobs بيتفتح بس لما فيه علاقة حقيقية: تقديم على وظيفة، أو شخص بتوظّفه ومتصل بيه واتراسلتوا في الاتجاهين (F-10).
26. مسح حساب owner الشركة بيسيب الصفحة "unclaimed" بصفقاتها وتاريخها، بدل خطأ FK (F-17).
27. من غير تسجيل مفيش أي محتوى بيتقري من الـ API (F-26، قرارك في 5.2).

**اتضاف في الجولة التالتة.** R3-gate راجعهم بالصور بالإنجليزي والعربي (شباك الإنشاء، والكارت الجديد، وشباك الدعوة، وخطأ الدخول)، وبعدها اتنسخوا على المرجع (`d7709969`):

**ظاهر في الديمو:**
28. شاشات الجروبات بالعربي: شباك "Create a Group" كله (العنوان، والاسم، والنوع، والخصوصية، وأوصافهم، والـ placeholder)، و"Manage Group" و"DISCUSSION" و"NEW" وجملة "Created just now · you are the admin"، وزرار الدعوة "✉️ ادعُ"، والـ toasts بصيغ الجمع (شخص واحد، شخصين، 5 أشخاص، 11 شخصًا) (N-9).
29. رسايل الفورم بالعربي: "Email is required" و"Password must be at least 8 characters" وأخواتهم (Title وDetails وProduct name وGroup name is required، و"Please write at least 20 / 40 characters"). كانت إنجليزي في المعتمد.
30. الكليك على اسم شخص بيفتح صاحب الاسم بالظبط، مش أول حد اسمه بيبدأ بنفس الكلام (N-10). الشكل ما اتغيّرش.
31. الخطوط بتتطلب بعد ما الصفحة تحمّل، فمفيش تعليق لو سيرفر جوجل مش واصل (F-70). الشكل ما اتغيّرش.

**في الـ live بس:**
32. المدعو لجروب خاص بيلاقي إشعار في Alerts: "<الأدمن> invited you to join the private group "<الاسم>""، وبالعربي "دعاك للانضمام إلى المجموعة الخاصة "<الاسم>"" (N-8).
33. شركتين بنفس الاسم في نفس اللحظة: التانية بتاخد عنوان بـ "-2" بدل رسالة خطأ (F-74).

**المصطلحات العربي المقترحة (UI2، F-148):**

| الإنجليزي | قبل | المقترح |
|---|---|---|
| Connect / + Connect | اتصال | **تواصل** |
| Message | رسالة | **مراسلة** |
| Upgrade Now | رقِّ الآن | **ترقية الآن** |
| Role | — | **المسمى الوظيفي** |
| Senior | خبير (زي Expert بالظبط) | **متمرّس** (وExpert تفضل خبير) |
| Alerts | — | **الإشعارات** (نفس كلمة السايدبار) |
| New batch | — | **تشغيلة** جديدة |
| EGP (عربي) | مش ثابت | **ج.م** |

**قرارات محتاجاك:**
- اسم "Dr. Asmaa Meabed" في الديمو: نسيبه ولا نغيّره (F-151)؟
- الـ Boost المدفوع: نحط علامة "مميّز" ظاهرة على الكارت، ولا يكفي الترتيب (N-6)؟
- أسعار ومدد الـ boost والـ featured (EGP 1,450 لمدة 7 أيام، وEGP 3,950 لمدة 30 يوم، قبل الـ VAT 14%). ورسالة تأكيد الديمو بتقول "7 days" للاتنين، وده كان كده في المعتمد.
- المحتوى العام (البوستات والوظايف والإعلانات) يتقري من غير تسجيل ولا لأ (F-26). اتعمل privacy-first لحد ما تقرر، والرجوع بسطر لكل جدول (5.2).
- الـ honor references تتنشر على طول ولا تعدّي على مراجعة (F-11).
- سعر "To be confirmed" في الـ buying group، وأزرار إلغاء ورفض الجروب المفتوح (F-107)، وتبويب لمراجعة الريفيوهات في Admin → Review (F-34). التلاتة دول تغييرات في الواجهة.

## 7. خطوات الإطلاق E5 (محدّثة)

1. **مشروع Supabase:** اعمل المشروع وخلي "Confirm email" شغال وrate limits الـ Auth شغالة وأقل طول لكلمة السر 8. في الـ API خلي Max rows = 1000، والـ statement timeout للـ anon 3s وللـ authenticated 8s.
2. **الـ migrations بالترتيب 0001 → 0025**، كل واحدة بـ `psql -v ON_ERROR_STOP=1 -f supabase/migrations/00NN_*.sql`. 0001 تتشغل مرة واحدة بس، ومن 0002 لـ 0025 ينفع تتعاد (`migration_check` طلع OK). كل migration بتخلص بـ `notify pgrst, 'reload schema';`، فاتأكد إن عمود جديد بيظهر في الـ API على طول. بعدها شغّل `psql -f supabase/tests/schema_sweep.sql`: لازم الـ 6 سطور يطلعوا **none**.
3. **JIT:** لو 0022 طبعت notice إنها ما قدرتش تقفل الـ JIT (صلاحيات Supabase المستضاف)، شغّل في الـ SQL editor: `alter role authenticator in database postgres set jit = off;` وبعدين `show jit` من الـ API لازم يطلع off.
4. **pg_cron:** فعّل pg_cron من Database → Extensions، وبعدين أعد تشغيل 0023 و0024، فهيتعمل jobين: `drugbox-expire-vip` الساعة 01:17 UTC و`drugbox-purge-notifications` (بيمسح الإشعارات الأقدم من 180 يوم) الساعة 02:23 UTC كل يوم. اتأكد بـ `select * from cron.job`. لو مش هتفعّل pg_cron، اعمل `POST /rest/v1/rpc/expire_vip_plans` و`rpc/purge_old_notifications` بالـ service key مرة كل يوم.
5. **Storage:** الـ migrations بتعمل الـ buckets (`videos` و`post-media` و`message-media` و`documents` و`reference-evidence`) بحدودها. اتأكد إن role الـ migration يقدر يمسح صفوف `storage.objects`. لو مش قادر، الـ triggers بتاعة مسح ملفات البوست والـ evidence هتسجّل warning بس، والملفات هتفضل.
6. **أسرار الدوال (Edge Functions → Secrets):** `APP_URL`، و`ALLOWED_ORIGINS` (لازم يبقى فيها كل عنوان التطبيق بيتفتح منه، وإلا الـ checkout من البراوزر هيرجع 403)، و`PAYMOB_SECRET_KEY` و`PAYMOB_PUBLIC_KEY` و`PAYMOB_HMAC_SECRET` و`PAYMOB_CARD_INTEGRATION_ID` و`PAYMOB_WALLET_INTEGRATION_ID`، و`FAWRY_BASE` و`FAWRY_MERCHANT_CODE` و`FAWRY_SECURE_KEY`، و`INSTAPAY_ADDRESS` و`INSTAPAY_NAME`. بعدها `supabase functions deploy payments-create`، و`paymob-webhook --no-verify-jwt`، و`fawry-webhook --no-verify-jwt`. جرّب الأول بمفاتيح Paymob التجريبية وFawry staging. F-115 اتقفل (0024 + `fawry-webhook` الجديدة)، فلازم تنشر النسخة الجديدة من الدالة قبل مفاتيح Fawry الحقيقية.
7. **قبل الـ build:** N-1 وF-05 اتقفلوا في الجولة التانية، وF-70 وF-74 وN-7 لـ N-10 في الجولة التالتة. فاضل تحدّث `supabase-js` (F-172) وتعيد b1 وb4 وe4b. ولو عايز تقفل الذيول الصغيرة قبل الإطلاق: N-11 وN-13 وN-14 (القسم 5.7)، وده محتاج refresh للمرجع.
8. **الـ build والـ deploy:** `rm -rf web/dist/live`، وبعدين `DRUGBOX_SUPABASE_URL=… DRUGBOX_SUPABASE_ANON_KEY=… python3 web/build/live.py`. السكريبت بيرفض أي مفتاح مش anon وأي URL مش https، وبيكتب `web/dist/live/vercel.json` بالـ CSP وعنوان المشروع والـ headers والـ cache. بعدها `vercel deploy web/dist/live`. الـ scripts بتطلع في `js/` بأسماء فيها hash (immutable)، و`index.html` no-cache، وlive.py بيمسح أي ملف قديم مش مطلوب (N-3)، فالـ `rm` بقى احتياط بس.
9. **الدومين:** HTTPS، وحدّث `ALLOWED_ORIGINS` و`APP_URL` بالدومين النهائي. وفي Paymob حط الـ processed callback على `…/functions/v1/paymob-webhook` للتكاملين (card وwallet)، وظبط إشعار Fawry على `fawry-webhook`.
10. **الـ pooler:** PostgREST والـ Realtime يفضلوا على الاتصال المباشر. أي clients زيادة (k6 أو scripts) يروحوا على Supavisor transaction mode (port 6543) من غير prepared statements.
11. **إعادة الاختبار على staging:**
    - `schema_sweep.sql` (6 none)، و`followups.rls.sql` و`small_followups.rls.sql` وباقي الـ SQL suites على داتابيز staging فاضية لو ينفع.
    - الـ e2e كلها على staging عن طريق متغيرات `_dx`: `APP_URL` و`DB_NAME` و`PGHOST/PGPORT/PGUSER` و`DRUGBOX_FN_ENV` و`DRUGBOX_FIXTURES`. يعني b0 لحد video_live، ومعاهم e4 وe4b بمفاتيح الدفع التجريبية.
    - الـ Realtime (رسالة وإشعار بيوصلوا من غير polling)، لأنه ماتجربش محليًا.
    - Safari/WebKit يدوي بالعربي، لأن `rtl_scroll` و`data_audit` ما اشتغلوش هنا.
    - k6 بـ 100k مستخدم و2,000 متزامن، يغطّي `GET /deals` و`my_interactions` و`directory_companies_page` والـ feed والرسايل.
12. **الخصوصية:** لو قررت المحتوى يبقى عام (F-26)، رجّع الـ policies المطلوبة بـ `alter policy … to public` قبل الإطلاق. ومستندات الشركات بقت للمسجّلين بس (N-7، 0025)، ولو عايزها عامة: `alter policy "documents: everyone reads metadata" on public.company_documents to public;`.
13. **التشغيل:** Sentry للـ front-end والدوال، وbackups (PITR)، وتمسح الداتابيز القديمة اللي على الجهاز المحلي (`rv_*`) لو مش محتاجها.
