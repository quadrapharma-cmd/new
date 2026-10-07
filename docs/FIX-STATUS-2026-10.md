# حالة الإصلاحات بعد مراجعة أكتوبر 2026

مكمّل لـ `docs/CODE-REVIEW-2026-10.md` (البنود F-01 … F-178). الملف ده بيقول كل بند حصله إيه، اتصلح فين، واتحقق منه إزاي. المصادر: نتايج الـ workstreams (DB1–DB4، INFRA، UI1–UI3، DBINT، ADAPTER، UIFOLLOW)، الـ gates من G1 لـ G6، وتلات شرايح تحقق مستقل (V-db، V-web، V-perf-ui). آخر commit اتجرب عليه: `eadaa52`.

## 1. الخلاصة

- **اتقفل 151 بند من 178**، و24 جزئي، و2 متأجلين، و1 ملاحظة قياس. الحرج في الأمان والفلوس اتقفل واتحقق منه بهجمات حقيقية: الترقية لأدمن (F-01)، الـ Stored XSS (F-02)، الـ Boost ببلاش (F-03)، والدفع اللي مكانش بيعمل حاجة أو سعره غلط (F-06، F-07).
- **الأداء الحرج اتحسن كتير بس فيه ذيل:** `GET /deals` نزل من 2.4 ثانية لـ 33–40 ms، أسرع حوالي 60 مرة (F-04). الهدف كان ≤ 25 ms وماوصلناش له. الدليل مبقاش بيتحمّل مع الـ sign-in، بس لسه بينزّل كل الشركات أول ما تفتح Companies أو Market (F-05).
- **الاختبارات كلها خضرا:** 33 / 33 suite على stack نضيف اتعادت مرتين (كل suite N/N)، والـ legacy 22 / 22، وPARITY OK. الـ build ثابت (deterministic)، وتبديل الصفحات مش أبطأ (median 14.25 ms مقابل 14.8 ms قبل كده).
- **التحقق المستقل لقى حاجات لسه مفتوحة**، وأهمها قبل الإطلاق: Fawry ممكن يدفع طلب غير اللي اتوقّع (F-115)، و`my_interactions()` بقت أبطأ 10 مرات بسبب 0021 (N-1)، والدعوات للجروبات الخاصة مش بتتبعت في الـ live (F-29). كمان الـ anon لسه بيقرا المحتوى العام (F-26)، وowner الشركة اللي ليها صفقات ما يقدرش يمسح حسابه (F-17)، والشركة تقدر تقفل البلاغ اللي عليها بنفسها (F-32).
- **جاهزية E5:** الكود جاهز يتحط على Supabase staging دلوقتي. لكن مش جاهز لـ production قبل ما يتقفل F-115 (قبل مفاتيح Fawry الحقيقية) وN-1 وF-05 (قبل الـ load test)، وقبل ما يتمسح ملف الـ adapter القديم من `web/dist/live/js` (N-3).
- **محتاج منك:** (1) توافق على تغييرات الواجهة والمصطلحات العربي في القسم 6. (2) تقرر في اسم "Dr. Asmaa Meabed" في الديمو. (3) تبعت مفاتيح Paymob وFawry وعنوان InstaPay. (4) تأكد أسعار الـ boost والـ featured. (5) تقرر هل المحتوى يفضل مقروء من غير تسجيل (F-26)، وهل الـ honor references تتنشر من غير مراجعة.
- الملف المستقل `web/dist/drugbox.html` هو نفس المرجع المعتمد الجديد: sha256 `35782b6a…c1a5`، حجمه 5,509,386 byte.

## 2. نتيجة الاختبارات النهائية

G6 شغّل `python3 tests/run_all.py sql sweep demo e2e` (مع `DEMO_FILE=web/dist/drugbox.html`) مرتين، وكل مرة على stack متقام من الأول: داتابيز `drugbox_live` جديدة من 0001–0023، ودوال الدفع، والـ fixtures. المرتين طلعوا **33 / 33**. الـ e2e اتجرّبت كمان على stack كانت اتشغلت عليه قبل كده، وe4_payments طلعت 26 / 26 تاني.

| المجموعة | Suite | النتيجة |
|---|---|---|
| sql | `company_hub.rls.sql` | 35 / 35 |
| sql | `deals.rls.sql` | 23 / 23 |
| sql | `integrity_perf.sql` | 56 / 56 |
| sql | `listings_groups.rls.sql` | 23 / 23 |
| sql | `payments_storage.rls.sql` | 73 / 73 |
| sql | `security_core.rls.sql` | 96 / 96 |
| sql | `trust_hub_deals.rls.sql` | 141 / 141 |
| sweep | `schema_sweep.sql` (6 سطور كلها none) | 6 / 6 |
| demo | `profile_composer_test.py` en / ar | 11 / 11 · 11 / 11 |
| demo | `videos_test.py` en / ar | 15 / 15 · 15 / 15 |
| e2e | b0_rtl_smoke | 7 / 7 |
| e2e | b1_auth | 19 / 19 |
| e2e | b2_feed | 18 / 18 |
| e2e | b2b_profile_post | 6 / 6 |
| e2e | b3_network | 20 / 20 |
| e2e | b4_messages | 20 / 20 |
| e2e | c1_companies | 15 / 15 |
| e2e | c2_deals | 16 / 16 |
| e2e | c3_listings | 14 / 14 |
| e2e | d1_market | 17 / 17 |
| e2e | d2a_jobs | 14 / 14 |
| e2e | d2b_trust | 14 / 14 |
| e2e | d3_groups | 17 / 17 |
| e2e | e1a_follow | 5 / 5 |
| e2e | e1a_uploads | 12 / 12 |
| e2e | e1b_documents | 13 / 13 |
| e2e | e2_review | 14 / 14 |
| e2e | e3_training | 10 / 10 |
| e2e | e4_payments (دوال Deno حقيقية + بديل Paymob/Fawry) | 26 / 26 |
| e2e | e4b_checkout | 14 / 14 |
| e2e | video_live | 14 / 14 |
| **المجموع** | **run_all** | **33 / 33 suite** |
| legacy (G1، نفس الـ build) | `run_all.py legacy` على Chromium | 22 / 22 (كانوا 14؛ اتضاف 8 كانوا بيتخطّوا من غير ما حد يحس) |
| migrations (G2) | `tools/migration_check.py` | OK للـ 23 migration (كان 51 finding) |
| build (G1، V-perf-ui) | build.py مرتين، ومرة بـ TZ/LANG مختلفين | نفس الملف بالظبط، ومفيش ملف tracked اتغيّر |
| parity | `tools/parity_check.py web/reference/demo-approved.html web/dist/drugbox.html` | **PARITY OK** (sha256 35782b6ae2d28994) |
| الملف المسلَّم | `web/dist/drugbox.html` = `web/reference/demo-approved.html` | sha256 `35782b6ae2d28994fc69b1854c49c2241132f0147d311b7fb722aa101313c1a5` · 5,509,386 byte (كان 9.56 MB) |
| السرعة (G1) | `stress_base.py` على القديم ضد `stress.py` على الجديد، 6 جولات بالتبادل × 300 تبديل صفحة | القديم: median 14.8 ms / p95 55.3 ms · الجديد: median 14.25 ms / p95 54.25 ms · الـ heap 9 MB في الاتنين · القديم طلّع JS error في 3 جولات من 6، والجديد 0 |
| يدوي (G1) | i18n، xss_audit، dialog_audit en/ar، logic_audit، monkey (400 + 300)، deadlinks | مفيش JS errors، والـ XSS hits: NONE |

**اللي ما اتشغلش هنا:** `rtl_scroll.py` و`data_audit.py` محتاجين WebKit ومش متسطّب (`python3 -m playwright install webkit`)، فالـ lite suites اشتغلت على Chromium بس. الـ Realtime ما ينفعش يتجرب غير على Supabase حقيقي. والـ k6 load test مستنيه E5.


## 3. التحقق المستقل

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


## 4. حالة كل البنود (178)

اتصلح 151 · جزئي 24 · متأجل 2 · ملاحظة 1. "اتحقق منه" = البند اتجرب بشكل مستقل في القسم 3. "اتكمّل بعدين" = الـ workstream قال جزئي والباقي اتعمل في خطوة بعدها:

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
| F-04 | حرج | GET /deals بيشغّل is_company_member() على كل صف وكل embed → 2.4 ثانية في كل sign-in وكل notification | جزئي (اتحقق منه — خالف كلام الـ workstream) | `0022` §1 (`my_company_ids`, `idx_deals_updated`) |
| F-05 | حرج | directory_companies(5000) بيبني 8.7–17 MB JSON ويعيد حساب track record لكل شركة في كل sign-in وكل زيارة anon | جزئي (اتحقق منه) | `0022` §2 (`directory_companies_page`) + `adapter.js` |
| F-06 | عالي | الـ Boost/Featured المدفوعين مش بيعملوا حاجة في الـ live: boosted_until/featured_until بيتكتبوا ومحدش بيقراهم | اتصلح (اتحقق منه) | `adapter.js` (loadMarket) |
| F-07 | عالي | سعر الـ Boost/Featured في شباك الدفع محسوب من USD × FX API خارجي ومختلف عن اللي السيرفر بيحاسب عليه (payment_products) | اتصلح (اتحقق منه) | `checkout.js` + `adapter.js` (`dxPay.quote`) |
| F-08 | عالي | connections بتتزوّر: insert كـ accepted مباشرة من غير موافقة، والـ addressee يقدر يغيّر الـ requester لشخص تالت | اتصلح (اتحقق منه) | `0020_security_core.sql` |
| F-09 | عالي | أعمدة السيرفر (id, created_at, pinned, counters, read_at, reply/replied_at) البراوزر بيكتبها: تثبيت بوست سنة 2099، كسر paging، DoS للرسايل، تزوير رد المرشح | اتصلح (اتحقق منه) | `0020_security_core.sql` |
| F-10 | عالي | رسالة واحدة = 'تعامل حقيقي': أي حد يسيب review مجهول 1 نجمة على أي حد ويتعرض كـ Verified applicant | جزئي (اتحقق منه — خالف كلام الـ workstream) | `0021_trust_hub_deals.sql` |
| F-11 | عالي | work_reference_rules معتمدة على profile.company نص حر بـ LIKE: أي حد ينشر honor/warning على أي حد — وفي الـ live مستحيل تتعمل أصلاً لأن experience مش بتتكتب | اتصلح (اتحقق منه — خالف كلام الـ workstream) | `0021` §3 |
| F-12 | عالي | jobs_interacted(a,b) و increment_* RPCs مفتوحين لـ anon: oracle على مين راسل مين / قدّم لمين | اتصلح (اتحقق منه) | `0020_security_core.sql` |
| F-13 | عالي | site_certificates مش مربوطة بشركة الموقع: أي عضو شركة يحط شهادات على صفحة شركة منافسة | اتصلح (اتحقق منه) | `0021_trust_hub_deals.sql` |
| F-14 | عالي | مستند compliance متحقق منه يتعدّل بالكامل (النوع/الرقم/الملف) ويفضل status = verified | اتصلح (اتحقق منه) | `0021_trust_hub_deals.sql` |
| F-15 | عالي | العضو اللي سابَ الشركة بيفضل متحكم بكل deal هو اللي بدأها (from_user بيتخطى العضوية للأبد) | اتصلح (اتحقق منه) | `0021_trust_hub_deals.sql` |
| F-16 | عالي | أرقام محرك الصفقات من غير validation: deal_join يقبل NaN/Infinity/كميات ضخمة ويقفل أي buying group، وvalidity تعمل overflow | اتصلح (اتحقق منه) | `0021_trust_hub_deals.sql` |
| F-17 | عالي | FKs بـ NO ACTION (notifications, groups.created_by, reviewed_by, comments.parent) بتمنع مسح أي بوست اتعمله like/comment ومسح أي حساب | جزئي (اتحقق منه — خالف كلام الـ workstream) | `0022` §3 |
| F-18 | عالي | notification لكل like من غير dedupe والـ unlike مش بيمسحها: 2,352 إشعار دائم في 20 ثانية | جزئي (اتحقق منه — خالف كلام الـ workstream) | `0022` §4 |
| F-19 | عالي | جلسة الـ adapter: صفحة الدخول بتتحط فوق التطبيق مع كل تحميل، والـ logout بيسيب cache المستخدم السابق للحساب الجديد | اتصلح (اتحقق منه) | `web/src/live/adapter.js` |
| F-20 | عالي | الجروبات الـ Private/Deal Room بتتعمل public DISCUSS في الـ live (الـ adapter بيقرأ radio مش موجود) | اتصلح (اتحقق منه) | `web/src/live/adapter.js` |
| F-21 | عالي | الـ adapter بيعتمد على نص الأزرار/placeholders الإنجليزي → إنشاء الجروب وحقل Location بيتكسروا في الواجهة العربية | اتصلح (اتحقق منه) | `web/src/live/adapter.js` |
| F-22 | عالي | محاكاة الديمو شغالة في الـ live: الـ dock بيبعت لـ localStorage وبيظهر رد مفبرك من شخص حقيقي، وإحصائيات وهمية | اتصلح (اتحقق منه) | `batch2.js`/`batch3.js`/`craft.js`/`links.js` + `adapter.js` |
| F-23 | عالي | الشركة بتتحدد بـ prefix الاسم من الـ h1: badge/passport/share card/video بيظهروا لشركة تانية اسمها بيبدأ بنفس الكلمة (trust spoofing) | اتصلح (اتحقق منه — خالف كلام الـ workstream) | `tiers.js` + `share.js` + `videos.js` |
| F-24 | عالي | الدليل بيرندر كل الشركات مرة واحدة والبحث O(n²) (madeFor × n): ثواني لكل حرف عند آلاف الشركات | اتصلح (اتحقق منه) | `hub-ui.js` + `hub-data.js` |
| F-25 | عالي | companies() مش memoised: كل render بيقرأ ويعمل JSON.parse لـ localStorage مئات المرات — صورة cover واحدة تبطّئ الدليل 18–95× | جزئي (اتحقق منه — خالف كلام الـ workstream) | `directory.js` (+ `hub-data.js`) |
| F-26 | متوسط | الـ anon key بيقرأ بيانات شخصية والـ content graph كله: profiles.phone/role، companies.email/phone/registry، الـ buying groups بأعضائها وكمياتها | جزئي (اتحقق منه — خالف كلام الـ workstream) | `0020_security_core.sql` |
| F-27 | متوسط | EXECUTE الافتراضي لـ anon على functions: get_reviews/get_ratings/moderate_reference/deal_receiver وpgcrypto/pg_trgm | اتصلح (اتحقق منه) | `0020_security_core.sql` |
| F-28 | متوسط | المتقدم للوظيفة بيغيّر status بتاعه (hired/shortlisted) وصاحب الوظيفة مالوش UPDATE policy خالص | اتصلح (اتحقق منه) | `0021_trust_hub_deals.sql` |
| F-29 | متوسط | الجروبات الخاصة dead end في الداتابيز: محدش غير المنشئ يشوفها أو ينضم، وadmin الجروب يقدر يعدّل صفوف العضوية | جزئي (اتحقق منه — خالف كلام الـ workstream) | `0021_trust_hub_deals.sql` |
| F-30 | متوسط | VIP مش بينتهي أبداً: vip_until بيتكتب ومحدش بيقراه ولا بينزّل plan | اتصلح (اتحقق منه — خالف كلام الـ workstream) | `0023` §1 + `0021`/`0022` (plan الفعلي) + `adapter.js` |
| F-31 | متوسط | activate_order بيعلّم الطلب paid ويبعت إشعار 'active' حتى لو الإعلان/الشركة اتمسحت | اتصلح (اتحقق منه) | `0023_payments_moderation_storage.sql` |
| F-32 | متوسط | الشركة المُبلَّغ عنها تقدر تشيل وتعدّل بلاغات 'معلومات غلط' قبل ما Drugbox تشوفها | جزئي (اتحقق منه — خالف كلام الـ workstream) | `0023_payments_moderation_storage.sql` |
| F-33 | متوسط | المرشح يقدر يخفي warning منشور للأبد بإنه يعمل dispute تاني (reply_to_reference من غير state check) | اتصلح (اتحقق منه) | `0021_trust_hub_deals.sql` |
| F-34 | متوسط | job_reviews.hidden مستحيل يتعمل set: مفيش policy ولا function ولا UI — مفيش أي علاج للريفيوهات المسيئة | جزئي | `0021_trust_hub_deals.sql` |
| F-35 | متوسط | jobs_hidden_for_me() بتكشف مين حاطك في الـ blacklist | اتصلح | `0021_trust_hub_deals.sql` |
| F-36 | متوسط | مسح صفحة شركة بيعمل cascade لصفقات وطلبات وAVL شركات تانية | اتصلح (اتحقق منه) | `0021_trust_hub_deals.sql` |
| F-37 | متوسط | عضو admin يقدر يمسح عضوية الـ owner (القاعدة اتطبقت على UPDATE مش DELETE) | اتصلح (اتحقق منه) | `0021_trust_hub_deals.sql` |
| F-38 | متوسط | routing الطلبات ممكن يشاور على غير أعضاء وبيفضل بعد خروج العضو: عناوين الطلبات بتتسرب لبرّه | اتصلح | `0021_trust_hub_deals.sql` |
| F-39 | متوسط | track record العام بيتنفخ ذاتياً: شخص عنده شركتين يقيّم نفسه 5 نجوم | اتصلح | `0021_trust_hub_deals.sql` |
| F-40 | متوسط | الموافقة على questionnaire عن طريق المحرك بتسمح لأي role يكتب approved-supplier list | اتصلح (اتحقق منه) | `0021_trust_hub_deals.sql` |
| F-41 | متوسط | مسح البوست بيسيب صوره وملفاته متاحة للتحميل في post-media للأبد | اتصلح | `0023_payments_moderation_storage.sql` |
| F-42 | متوسط | 'Claim this page' مالوش مسار سيرفر: الـ claim في الديمو مجرد edits، طلب التحقق من شركة claimed بيضيع، والـ admin ما يقدرش يعمل صفحات unclaimed | جزئي (اتحقق منه — خالف كلام الـ workstream) | `0021` §9 (`claim_company`) + `adapter.js` |
| F-43 | متوسط | مفيش حدود حجم على نصوص المستخدم: messages.body بـ 2 MB (وبيتنسخ في conversation_heads)، bio/profile/site، JSON المحرك والإعلانات | اتصلح | `0022_integrity_perf.sql` |
| F-44 | متوسط | فهارس ناقصة على FK/الأعمدة الساخنة (34 FK): notifications, jobs(user_id), job_applications(cv_path), products(user_id), company_followers… | جزئي (اتحقق منه — خالف كلام الـ workstream) | `0022` §7 + `0020`/`0021` |
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
| F-62 | متوسط | نصوص كتير فاضلة إنجليزي في الوضع العربي: Ctrl+K/Appearance/tour/compare/dock، محرر الشركة/share/trade-show/landed/PDF، molecules، training/admin/deals/messages | جزئي (اتحقق منه) | `i18n.js` |
| F-63 | متوسط | مفيش زرار لغة في صفحات login/signup وصفحة signup نص مترجمة | اتصلح (اتحقق منه — خالف كلام الـ workstream) | `app.html` + `i18n.js` |
| F-64 | متوسط | التحويل من عربي لإنجليزي بيسيب الصفحات الـ cached (Marketplace/Jobs/Groups) وأكشن الـ feed بالعربي لحد reload | جزئي (اتحقق منه — خالف كلام الـ workstream) | `i18n.js` |
| F-65 | متوسط | SKIP selector '.pb-text' في i18n بيطابق banner الأسعار في الماركت فعمره ما بيتترجم | اتصلح | `i18n.js` |
| F-66 | متوسط | مفاتيح مكررة في قاموس الترجمة: 'Saved' في السايدبار بيطلع 'تم الحفظ'، و'Remove'/'Verified' بيتكتبوا فوق بعض | اتصلح (اتحقق منه) | `i18n.js` |
| F-67 | متوسط | شارة 'Ctrl K' فوق خانة البحث من غير حجز مساحة: النص بيدخل تحتها LTR وأول الحروف مخفية في RTL | اتصلح | `batch3.js` |
| F-68 | متوسط | مودال الـ boost عربي بس بأرقام هندية و'ج.م' حتى في الواجهة الإنجليزية، وcheckout.js بيضيف طرق دفع إنجليزي | اتصلح (اتكمّل بعدين) | `app.html` + `checkout.js` |
| F-69 | متوسط | molecules.js بيحط زرار 'Structure' جوه عنوان الإعلان فالـ share caption وقراءة العنوان بيبقوا '…GMP GradeStructure' | اتصلح | `molecules.js` + `molecules.css` |
| F-70 | متوسط | Google Fonts <link> في الـ head بيبلوك أول paint ويفشل offline، والخطين (Inter/Cairo) مش مستخدمين — العربي بيرندر بخطوط النظام | جزئي (اتحقق منه — خالف كلام الـ workstream) | `app.html` |
| F-71 | متوسط | ملف الدخول 9.56 MB (64% فيديو splash base64 + لوجو مكرر 5 مرات): ~47 ثانية على Slow 4G | جزئي (اتحقق منه — خالف كلام الـ workstream) | `splash_full.mp4` + `mobile_opt.py` + `live.py` |
| F-72 | متوسط | تباين ألوان تحت WCAG AA: عناصر الـ ticker في a11y.css (1.5–3.2:1)، شارة مستوى التحقق (2.3:1)، تواريخ المشاهدين (2.9:1) | اتصلح (اتحقق منه) | `a11y.css` |
| F-73 | متوسط | حاسبة landed-cost بتطلع برّه الـ dialog على التابلت/الديسكتوب (عرض الـ Incoterm select بيكسر الجريد) | اتصلح | `landed.css` |
| F-74 | متوسط | الـ slug والـ monogram بيتعملوا في البراوزر: اسم عربي بس = لوجو فاضي وslug 'company-<timestamp>'، والأسماء المتشابهة بتعمل unique-violation خام | جزئي | `directory.js` |
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
| F-115 | منخفض | Paymob callback بيربط الطلب بحقل غير موقّع (merchant_order_id)، العملة مش بتتفحص، وprovider_ref مش unique | جزئي (اتحقق منه — خالف كلام الـ workstream) | `0023` + `paymob-webhook` + `fawry-webhook` + `payments-create` |
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

### 5.1 لازم يتقفل قبل production (بالترتيب)

| ID | اللي فاضل | ليه | الخطوة الجاية |
|---|---|---|---|
| F-115 | إشعار Fawry حقيقي ممكن يتبعت تاني برقم طلب تاني ومبلغ تاني بنفس التوقيع، فيدفع طلب مادفعش | النص الموقّع بيلزق `merchantRefNumber` و`paymentAmount` من غير فاصل، والـ webhook مش بيستخدم `paymentAmount`، و`confirm_payment('fawry')` مش بيقارن المرجع بالمرجع المتسجّل على الطلب | في `confirm_payment('fawry')` نشترط إن `p_provider_ref = o.provider_ref` (المرجع اللي `payments-create` طلّعه)، وفي `fawry-webhook` نشترط `paymentAmount = orderAmount`. بعدين نزوّد الهجمة دي على `e4_payments` |
| N-1 | `my_interactions()` (بتتنده مع كل فتح لـ Jobs، `adapter.js:1170`) بقت 135–220 ms عند 20k deal، وكانت 12–15 ms | فرع جديد في 0021 بيعمل seq scan على كل الـ deals وبينده `company_has_member()` لكل صف، فالوقت بيزيد مع عدد الصفقات | migration 0024: نكتب الفرع تاني بـ `d.to_company_id in (select my_company_ids())` ونعمل index على `deals(to_company_id, status)`، وبعدين نعيد `integrity_perf.sql` بقياس للدالة |
| F-05 | الـ live بيحمّل الدليل كله: 200 شركة في الصفحة (334 KB) ويلف لحد آخر شركة. عند 5k شركة ده 26 request و8.3 MB في كل فتح لـ Companies/Market، وبيتكرر بعد دقيقتين | الـ loop في `loadDirectory` (`adapter.js:731`) | نخلي `DIR_PAGE=100` والتحميل بالبحث أو عند الطلب ("Show more" بيجيب الصفحة اللي بعدها). وكمان نسحب `directory_companies(5000)` من authenticated (لسه 8.7 MB لو حد ندهها) |
| N-3 | `web/dist/live/js/adapter.5fcddf497a.js` قديم ومحدش بيستخدمه، وموجود جنب `adapter.829f574489.js` | `live.py` مش بيمسح الملفات القديمة اللي بالـ hash | قبل الـ deploy: `rm -rf web/dist/live && python3 web/build/live.py`، أو نخلي live.py ينضّف `js/` و`media/` |
| F-29 | جروب خاص في الـ live ما ينفعش يدخله عضو تاني. زرار "Invite people" المعتمد بيطلّع toast "Invites sent" ومش بيكتب حاجة | الداتابيز جاهزة (`group_invites`)، بس الـ adapter عمره ما بيكتب فيها | الـ adapter يمسك زرار الـ invite (delegated capture handler زي Join) ويعمل insert في `group_invites` للناس اللي اتختاروا، والـ toast يطلع بعد ما الكتابة تنجح. ونزوّد check على `d3_groups` |
| F-04 | `GET /deals` بيرجّع median 33–40 ms، والهدف ≤ 25 ms. الـ payload لسه 429 KB | الـ embeds (events، members، الشركات، الناس) لـ 300 صفقة | نقيس على staging بالـ k6. لو لسه فوق الهدف: نقلّل الـ limit ونجيب الـ events عند فتح الصفقة بس |

### 5.2 جزئي (مش موقِّف للإطلاق، بس متسجّل)

| ID | اللي فاضل | ليه | الخطوة الجاية |
|---|---|---|---|
| F-10 | متقدّم لوظيفة يقدر يقيّم صاحب الوظيفة بدور candidate من غير ما يكون شغّله | `can_review` للدور candidate بيشوف إن الشخص "open to work" وبس | نشترط علاقة توظيف حقيقية (طلب اتقبل أو deal نوعه hired) |
| F-17 | owner شركة ليها صفقات أو دخلت buying group ما يقدرش يمسح حسابه، وبيطلعله خطأ FK خام | الـ RESTRICT بتاع F-36 مقصود عشان سجل الطرف التاني يفضل محفوظ | دالة definer تنقل الملكية لـ admin تاني أو تقفل الصفحة (status closed) قبل المسح، ورسالة واضحة في `friendly()` |
| F-18 | سحب طلب الوظيفة وإعادته بيعمل إشعار جديد كل مرة، وإشعارات الكومنتات الممسوحة بتفضل | الـ dedupe اتعمل للايكات بس | unique index على إشعار job_application لكل (صاحب الوظيفة، المتقدّم، الوظيفة)، ونمسح الإشعار لما الكومنت يتمسح، وretention يومي بـ pg_cron للإشعارات المقروءة الأقدم من 90 يوم |
| F-25 | في الديمو: `dx_supplier_reviews` بيتقرا حوالي 1,078 مرة في كل render. مع 300 review الـ render بياخد 230–295 ms | `track()`/`reviewsOf()` في `hub-data.js` مش memoised | نعمل cache لكل `__dxStoreVer` زي `companies()`. ده في الديمو بس، والـ live مش متأثر |
| F-26 | الـ anon key لسه بيقرا posts وcomments وjobs وproducts وcompany_members وpost_media والـ honor references المنشورة وsettings | الـ policies دي اتسابت عامة | **قرارك:** لو مش محتاجين صفحات عامة (SEO)، نخلي الـ policies دي `to authenticated`، لأن الـ adapter مش بيقرا حاجة قبل الـ session |
| F-32 | الشركة تقدر تعلّم البلاغ اللي عليها resolved، فيختفي من Admin → Review، ولسه بتشوف مين بلّغ | open→resolved مسموح، والطابور بيقرا open بس | نخلي resolved للـ staff بس، أو الطابور يعرض اللي الشركة قفلته عشان يتراجع. ونخبّي `reporter` عن الشركة (column grant) |
| F-34 | `moderate_review()` موجودة بس مش متوصّلة بأي واجهة | Admin → Review في الديمو المعتمد مفيهوش تبويب للريفيوهات | **قرارك:** نزوّد تبويب Reviews في Admin → Review (ده تغيير في الواجهة)، أو نسيبها للدعم من SQL |
| F-42 | في الديمو بس: Verify بعد Claim بيقول "Documents sent" والحالة بتفضل unverified | `verifyDialog` (`directory.js:345`) بيكتب في `created_companies` بس | يكتب في `company_edits` كمان للصفحات اللي اتعملها claim |
| F-44 | 10 FKs من غير index، كلهم على جداول قليلة. والتراجع اللي حصل في `my_interactions` متسجّل تحت N-1 | مش ساخنين | ممكن نضيفهم في 0024 مع N-1 |
| F-62 | شوية نصوص واجهة لسه إنجليزي في العربي: tooltips "Open X"، وجملة الـ routing في `hub-ui.js:135`، و"Certificate document"، والأفعال جوه نشاط الـ sample | ماتغطوش في القاموس | نزوّدهم في `i18n.js` |
| F-64 | Jobs بتفضل فيها 7 عناصر عربي بعد الرجوع لإنجليزي، في 3 تشغيلات من 4 | `restore()` مش بيوصل لعناصر اترسمت تاني جوه الـ node المتخزن | نمشي على `__jxNode` بعد إعادة الرسم، ونزوّد check على `i18n_test` |
| F-70 | offline الملف لسه بيطلب Inter وCairo ويسجّل ERR_FAILED، والـ load event بيستنى حوالي 6 ثواني لو سيرفر الخطوط واقع | الـ link اتعمل non-blocking بس لسه موجود، والخطين أصلًا مش مستخدمين | نشيل الـ link خالص. شكل الصفحة مش هيتغير، بس لازم refresh للمرجع |
| F-71 | الـ live `index.html` حجمه 3.41 MB (منهم 2.25 MB scripts inline) ومتعلّم no-cache، وفيه 114 KB مكررين | الطبقات بتتحط inline في الصفحة | `live.py` يطلّع الـ scripts في ملفات `js/` بالـ hash (immutable). Vercel هيضغط الملفات |
| F-74 | لو اتعملت شركتين بنفس الاسم في نفس اللحظة، بيطلع unique-violation (`friendly()` بيخبّي النص الخام بس الإنشاء بيفشل) | الـ slug بيتعمل في البراوزر | `companies_before_write` يزوّد -2 و-3 في السيرفر |
| F-78 / F-81 | المحاكي المحلي لسه مختلف عن Supabase: مفيش rate limits ولا /recover ولا /verify، والـ superuser والـ collation وحدود الخطة مختلفين | محتاجين مشروع حقيقي | يتجربوا على staging في E5 |
| F-83 | `0001_init.sql` مش re-runnable ومن غير `notify pgrst` في الآخر، و`0014` فيها notify مرتين (ملهاش ضرر) | 0001 هي الـ schema الأساسية | ما نعيدش تشغيل 0001 أبدًا. ممكن نزوّد سطر notify في آخرها |
| F-107 | سعر "To be confirmed" في الـ buying group لسه بيعمل orders، وأزرار cancel/decline للجروب المفتوح مش موجودة في الواجهة | زرار confirm المعتمد بيبعت `{}` | **قرارك:** خطوة في الواجهة تطلب سعر رقمي قبل confirm، وأزرار cancel/decline |
| F-151 | "Dr. Asmaa Meabed" موجودة 38 مرة في الديمو | زميلتك، فمحدش غيّر الاسم من غير قرارك | **قرارك:** نسيبه أو نغيّره لاسم خيالي |
| F-157 | لسه فيه sleeps ثابتة كتير في الـ e2e (dialogs وreloads) | الـ CSP بتمنع `wait_for_function`، فاتعمل `_dx.wait_for` | نبدّلهم تدريجيًا |

### 5.3 متأجل

| ID | ليه | الخطوة الجاية |
|---|---|---|
| F-45 | 50 like متزامنين على نفس البوست بيستنوا lock صف البوست. السقف حوالي 120–170 like/s للبوست الواحد، وده أعلى بكتير من أي حاجة هتحصل في شبكة B2B | نعيد التصميم (delta table) بس لو الـ k6 أو الإنتاج ورّوا ضغط فعلي |
| F-172 | `supabase-js` 2.45.4 أصلي، و`auth-js` 2.65.0 عليه advisory واحد low (`auth.admin`، service role بس) | نحدّث لآخر 2.x قبل E5 ونعيد b1 وb4 وe4b |
| F-162 | قياس بس (baseline للسرعة) | — |

### 5.4 مشاكل جديدة طلعت في التحقق (مش من الـ 178)

- **N-1** — تراجع في سرعة `my_interactions()` (راجع 5.1).
- **N-2** — البحث عن الشركة بأول الاسم لسه موجود في `web/src/links.js:165` (الضغط على عنوان الـ workspace) و`web/src/afford.js:20`. owner صفحة "Look Pharma X Egypt WS" داس على عنوانه فراح لصفحة "Look Pharma X". الحل إننا ندوّر بالـ slug أو بالاسم بالظبط.
- **N-3** — ملف adapter قديم في `web/dist/live/js` (راجع 5.1).
- **N-4** — الأدمن مالوش طريق من الـ API يغيّر `profiles.verified` لشخص، لأن profiles عليها policy "own update" بس، فالـ update بيعدّي على 0 صف. ده كان كده من قبل الإصلاحات. الحل دالة definer للأدمن أو policy للأدمن.
- **N-5** — `#dxEditor` واخد role=dialog بس من غير `aria-modal=true`. ده بند صغير.
- **N-6** — الـ Boost المدفوع بيغيّر الترتيب بس، ومفيش أي علامة على الكارت (القرار في القسم 6).

### 5.5 ذيول في بنود اتقفلت

- F-11: الـ live لسه مالوش مكان يكتب فيه `profiles.experience` أو `open_to_work`، فالـ work references هتشتغل لما يبقى فيه محرر بروفايل. وكمان الـ honor references بتتنشر من غير مراجعة (قرارك).
- F-30: الـ plan الخام بيفضل `vip` لحد ما pg_cron يتفعل، بس محدش بيقراه.
- F-40: عضو HR لسه يقدر يقبل quote ملزم للشركة (نموذج الأدوار ماتغيّرش).
- F-09: الـ id اللي البراوزر يبعته وأصغر من الـ sequence لسه بيتقبل، ومن غير أثر.

## 6. تغييرات الواجهة اللي محتاجة موافقتك

كل التغييرات دي مقصودة، وG1 راجعها بالصور قديم مقابل جديد بالإنجليزي والعربي. ما طلعش أي JS error، ولا شكل اتكسر، ولا جزء اختفى. وبعدها اتنسخت على `web/reference/demo-approved.html`. لو رفضت أي حاجة منهم، بنرجّعها ونعمل refresh للمرجع.

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
- المحتوى العام (البوستات والوظايف والإعلانات) يتقري من غير تسجيل ولا لأ (F-26).
- الـ honor references تتنشر على طول ولا تعدّي على مراجعة (F-11).
- سعر "To be confirmed" في الـ buying group، وأزرار إلغاء ورفض الجروب المفتوح (F-107)، وتبويب لمراجعة الريفيوهات في Admin → Review (F-34). التلاتة دول تغييرات في الواجهة.

## 7. خطوات الإطلاق E5 (محدّثة)

1. **مشروع Supabase:** اعمل المشروع وخلي "Confirm email" شغال وrate limits الـ Auth شغالة وأقل طول لكلمة السر 8. في الـ API خلي Max rows = 1000، والـ statement timeout للـ anon 3s وللـ authenticated 8s.
2. **الـ migrations بالترتيب 0001 → 0023**، كل واحدة بـ `psql -v ON_ERROR_STOP=1 -f supabase/migrations/00NN_*.sql`. 0001 تتشغل مرة واحدة بس، ومن 0002 لـ 0023 ينفع تتعاد (`migration_check` طلع OK). كل migration بتخلص بـ `notify pgrst, 'reload schema';`، فاتأكد إن عمود جديد بيظهر في الـ API على طول. بعدها شغّل `psql -f supabase/tests/schema_sweep.sql`: لازم الـ 6 سطور يطلعوا **none**.
3. **JIT:** لو 0022 طبعت notice إنها ما قدرتش تقفل الـ JIT (صلاحيات Supabase المستضاف)، شغّل في الـ SQL editor: `alter role authenticator in database postgres set jit = off;` وبعدين `show jit` من الـ API لازم يطلع off.
4. **pg_cron لـ `expire_vip_plans`:** فعّل pg_cron من Database → Extensions، وبعدين أعد تشغيل 0023، فهتعمل job اسمها `drugbox-expire-vip` الساعة 01:17 UTC كل يوم. اتأكد بـ `select * from cron.job`. لو مش هتفعّل pg_cron، اعمل `POST /rest/v1/rpc/expire_vip_plans` بالـ service key مرة كل يوم.
5. **Storage:** الـ migrations بتعمل الـ buckets (`videos` و`post-media` و`message-media` و`documents` و`reference-evidence`) بحدودها. اتأكد إن role الـ migration يقدر يمسح صفوف `storage.objects`. لو مش قادر، الـ triggers بتاعة مسح ملفات البوست والـ evidence هتسجّل warning بس، والملفات هتفضل.
6. **أسرار الدوال (Edge Functions → Secrets):** `APP_URL`، و`ALLOWED_ORIGINS` (لازم يبقى فيها كل عنوان التطبيق بيتفتح منه، وإلا الـ checkout من البراوزر هيرجع 403)، و`PAYMOB_SECRET_KEY` و`PAYMOB_PUBLIC_KEY` و`PAYMOB_HMAC_SECRET` و`PAYMOB_CARD_INTEGRATION_ID` و`PAYMOB_WALLET_INTEGRATION_ID`، و`FAWRY_BASE` و`FAWRY_MERCHANT_CODE` و`FAWRY_SECURE_KEY`، و`INSTAPAY_ADDRESS` و`INSTAPAY_NAME`. بعدها `supabase functions deploy payments-create`، و`paymob-webhook --no-verify-jwt`، و`fawry-webhook --no-verify-jwt`. جرّب الأول بمفاتيح Paymob التجريبية وFawry staging. **قبل مفاتيح Fawry الحقيقية لازم F-115 يتقفل.**
7. **قبل الـ build:** اقفل N-1 (`my_interactions`) وF-05 (paging الدليل)، وحدّث `supabase-js` (F-172).
8. **الـ build والـ deploy:** `rm -rf web/dist/live`، وبعدين `DRUGBOX_SUPABASE_URL=… DRUGBOX_SUPABASE_ANON_KEY=… python3 web/build/live.py`. السكريبت بيرفض أي مفتاح مش anon وأي URL مش https، وبيكتب `web/dist/live/vercel.json` بالـ CSP وعنوان المشروع والـ headers والـ cache. بعدها `vercel deploy web/dist/live`. الـ `rm` بيضمن إن الـ adapter القديم مش هيتنشر (N-3).
9. **الدومين:** HTTPS، وحدّث `ALLOWED_ORIGINS` و`APP_URL` بالدومين النهائي. وفي Paymob حط الـ processed callback على `…/functions/v1/paymob-webhook` للتكاملين (card وwallet)، وظبط إشعار Fawry على `fawry-webhook`.
10. **الـ pooler:** PostgREST والـ Realtime يفضلوا على الاتصال المباشر. أي clients زيادة (k6 أو scripts) يروحوا على Supavisor transaction mode (port 6543) من غير prepared statements.
11. **إعادة الاختبار على staging:**
    - `schema_sweep.sql` (6 none).
    - الـ e2e كلها على staging عن طريق متغيرات `_dx`: `APP_URL` و`DB_NAME` و`PGHOST/PGPORT/PGUSER` و`DRUGBOX_FN_ENV` و`DRUGBOX_FIXTURES`. يعني b0 لحد video_live، ومعاهم e4 وe4b بمفاتيح الدفع التجريبية.
    - الـ Realtime (رسالة وإشعار بيوصلوا من غير polling)، لأنه ماتجربش محليًا.
    - Safari/WebKit يدوي بالعربي، لأن `rtl_scroll` و`data_audit` ما اشتغلوش هنا.
    - k6 بـ 100k مستخدم و2,000 متزامن، يغطّي `GET /deals` و`my_interactions` و`directory_companies_page` والـ feed والرسايل.
12. **التشغيل:** Sentry للـ front-end والدوال، وbackups (PITR)، وتمسح الداتابيز القديمة اللي على الجهاز المحلي (`rv_*`) لو مش محتاجها.
