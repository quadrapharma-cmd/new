# فحص اكتمال المنتج — أكتوبر 2026

الملف ده مش عن الأمان ولا السرعة (دول في `docs/CODE-REVIEW-2026-10.md` و`docs/FIX-STATUS-2026-10.md`). ده عن سؤال واحد: **المستخدم الحقيقي يقدر يخلّص شغلته من أولها لآخرها ولا لأ؟**

إزاي اتعمل: تلات فحوص اكتمال (السوشيال، البيزنس، المجتمع والوظايف). كل فحص مشي في كل flow بإيده على الديمو (`web/dist/drugbox.html`) بالإنجليزي والعربي على 1440 و390 px، وعلى الـ live على الـ stack المحلي (`http://localhost:54321`) بحسابات جديدة حقيقية، وبعد كل خطوة اتشيّك في الداتابيز بـ SQL. بعدها اتعمل شغل المجموعات (commit `ee2b5f8`) واتعمله تحقق مستقل. الصور والسكريبتات في الـ scratchpad (المسارات تحت).

**الدرس الأهم:** الـ e2e كانت خضرا وفي نفس الوقت زراير حقيقية مش بتعمل حاجة. مثال: `b2_feed_test` بيستدعي `likePost()` من الـ JS مباشرةً، لكن زرار Like في الواجهة بينادي `doReact()` اللي الـ adapter عمره ما لفّه. فالاختبار بيعدّي والـ like بيختفي بعد الـ reload. من هنا ورايح أي اختبار لازم **يدوس على الزرار نفسه** ويشيّك الداتابيز.

---

## 1. الخلاصة

**الأرقام (الفجوات المفتوحة دلوقتي، بعد المرحلة 1 — 15 أكتوبر 2026، commit `d0b2cfe`):** 14 blocker، 37 major، 24 minor — المجموع 75 (كانت 21 / 35 / 20 = 76).
- **اتقفل في المرحلة 1 (5):** S-01 حفظ البروفايل، S-04 دعوات الاتصال، B-05 مراسلة الشركة، G-02 كروت الجروبات الديمو وJoin الوهمي، G-03 قايمة "Your Groups". "اتقفل" معناه إن رحلاته عدّت في الديمو والـ live **و** المراجع المستقل وافق.
- **نزلوا من blocker لـ major (2):** S-02 (الـ like والتفاعلات بتتحفظ؛ فاضل قايمة التفاعلات على العربي 390px) وG-01 (تاب Listings اتخبّى في الـ live؛ فاضل يتبني).
- **بنود جديدة لقاها التحقق (4 minor):** S-29، B-22، G-16، A-04 (في الجداول تحت).
- **اتصلّحوا والرحلات عدّت، بس لسه مفتوحين** لأن المراجع ماشافهومش أو لقى فيهم حاجة: S-03، S-07، S-10، S-11، S-15، S-26، وأجزاء من S-09 وS-19 وS-20 وB-06 وB-07 وG-04 وA-03. التفاصيل في كل بند.
- **الرحلات:** 32 من 150 شغالة ومتحقق منها (كانت 14) — `docs/FEATURE-STATUS-2026-10.md`.

قبل المرحلة 1، شغل المجموعات كان قفل 6 بنود من الفحص الأصلي (القسم 2) وقسّم بند الاكتشاف لبنود أصغر.

**الحكم بصراحة:** الواجهة كاملة وجميلة في الديمو، والأساس التقني (الأمان، الدفع، السرعة، الـ RLS) قوي. لكن **المنتج في الـ live مش جاهز تجارياً لسه**: فيه مشاوير أساسية بتقول "اتحفظ ✅" وهي ما حفظتش حاجة، وفيه بيانات ديمو بتظهر لمستخدم حقيقي على إنها حقيقية (ودي في منتج بيبيع boost وVIP تبقى إعلان مضلِّل)، وفيه ثغرة خصوصية في الرسايل، ومفيش سياسة خصوصية ولا شروط استخدام ولا "نسيت الباسورد".

**بعد المرحلة 1:** البروفايل والـ like والحفظ والبلاغ والشبكة والرسايل ومراسلة الشركة بقوا بيتحفظوا فعلاً، والجروبات والماركت والشبكة والرسايل في الـ live مابقاش فيهم أسماء ولا أرقام ديمو. **فاضل من "الكدب والتسريب":** (1) ثغرة New message لسه موجودة في حالة واحدة: عضوين بنفس الاسم ونفس الشركة (S-03)؛ (2) شريط الأخبار (ticker) فوق كل صفحة لسه بيعرض إعلانات ديمو لحد ما المستخدم يفتح الماركت وفيه إعلانات (S-19)؛ (3) صفحة Jobs لسه بتقول "76 open positions" و"4 candidates" على داتابيز فاضية (J-05)؛ (4) My Intents في الماركت بتعرض اختيارات ديمو جاهزة لمستخدم جديد (B-06)؛ (5) Home فيه صور وشوش stock جنب عدد الأعضاء وكارت TODAY فاضي (S-19). ومازال مفيش سياسة خصوصية ولا شروط ولا "نسيت الباسورد" (المرحلة 2).

### قسم قسم — تقدر تعمل إيه النهارده وما تقدرش تعمل إيه

| القسم | شغال فعلاً في الـ live | مش شغال / مضلِّل |
|---|---|---|
| **الدخول والحساب** | تسجيل، دخول، خروج، رسايل خطأ مفهومة، انتهاء الجلسة من تاب تاني. الشركة والتخصص في التسجيل بقوا بيتحفظوا (المرحلة 1) | مفيش "نسيت الباسورد" خالص (اللي ينسى بيتقفل برّه للأبد). اللي مابيغيّرش خانة Role في التسجيل بياخد "Regulatory Affairs" (وبالعربي بيتخزّن "الشؤون التنظيمية"). تأكيد الإيميل بيطلع كأنه خطأ ومن غير "ابعت تاني". مفيش صفحة إعدادات (تغيير إيميل/باسورد، إشعارات، مسح الحساب) |
| **البروفايل** | زرار Message وConnect من بروفايل حد تاني. **Save في تعديل البروفايل بقى بيحفظ** كل الخانات (ومعاهم Location وOpen to work)، وFollow لشخص بيتحفظ وبيبعت إشعار (المرحلة 1) | الصورة والغلاف ما بيترفعوش. مفيش إضافة خبرة/تعليم/مهارات. أرقام الديمو (448 اتصال، 342 مشاهدة) لسه في بروفايل الديمو، ومشاهدات البروفايل مابتتحسبش |
| **الفيد** | بوست بصور وملفات، كومنت (وبيوصل إشعار لصاحب البوست)، مسح بوست مع Undo. **Like والتفاعلات بنوعها، Save وصفحة Saved، Copy link، Report بأسباب وطابور مراجعة** (المرحلة 1) | Repost وEdit لسه toast بس. Reply على كومنت "coming soon". اللينكات والـ #hashtags والـ @mentions نص عادي. قايمة التفاعلات على العربي 390px بتطلع برّه الشاشة |
| **الشبكة** | طلب اتصال بيتحفظ. **Pending invitations بقى بيعرض الطلبات الجاية ليّا، وAccept وDecline بيتحفظوا؛ Sent requests بـ Withdraw؛ قايمة My connections بـ Remove؛ الاقتراحات بسببها و×** (المرحلة 1). الأرقام حقيقية | مفيش بحث عن ناس في صفحة Network (S-18). اللي طلبه اترفض بيفضل شايفه "Pending" على طول، ومفيش ملاحظة مع Connect (S-29) |
| **الرسايل** | رسالة من بروفايل حد بتوصل صح، بمرفقات صور وملفات في تخزين خاص (وأنواع الملفات الممنوعة بتترفض). **✎ New message بقى بيبعت للعضو اللي اخترته بس؛ Mute وBlock وReport بيتحفظوا والداتابيز بترفض الرسايل بعد Block؛ ✓/✓✓؛ Unread حقيقي؛ البحث جوه الرسايل** (المرحلة 1) | **لو عضوين ليهم نفس الاسم ونفس الشركة، الرسالة ممكن تروح للتاني من غير تحذير (S-03 لسه مفتوح).** اللي عملك Block لسه بيظهر في اقتراحات New message. ✓✓ ممكن تاخد لحد 60 ثانية |
| **الإشعارات والبحث** | الإشعارات بتظهر وبتتعلّم مقروءة. إشعار التفاعل والكومنت بقى بيفتح البوست (المرحلة 1) | إشعار طلب الاتصال مافيهوش "View profile"، وإشعارات الجروب/الوظيفة مابتفتحش حاجتها. البحث (Ctrl+K والشريط) بيدوّر في بيانات الديمو المحمّلة، مش في الأعضاء الحقيقيين. مفيش إيميل لأي حاجة. زرار Back بيخرّج من الأبلكيشن |
| **الشركات** | إنشاء صفحة شركة، طلب توثيق برفع السجل والبطاقة الضريبية، claim بمراجعة Drugbox. **"Message" للشركة بقى بيوصل للعضو المتوجّه له أو للمالك، وبإشعار** (المرحلة 1) | **الدليل فاضي** (مفيش import للشركات من القوايم العامة). المنتجات والمواقع والشهادات والـ logo والفريق **ما بيتحفظوش**. التقييمات دايماً "No reviews yet". شركة لسه متعملة بتطلّع "آخر تحديث من أكتر من 6 شهور"، والمالك مكتوب "(Admin)" (B-22) |
| **الصفقات** | الـ state machine كامل (quote → … → rated) بـ `deal_create`/`deal_act` | مفيش ملفات في أي خطوة (COA، PO، فاتورة، NDA). RFQ من الماركت مجرد رسالة شات مش صفقة |
| **الماركت** | نشر listing supply بيتحفظ ويظهر، Contact بيفتح شات مع البايع، Quick view. **أرقام وكروت الديمو اتشالت من Browse** (الأرقام من `market_stats()`، و"Live now" والخدمات والوظايف حقيقية أو حالة فاضية، ومفيش "150,000+" ولا "8×")، وMy Listings بقت بتعرض إعلاناتي بس (المرحلة 1) | My Intents بتعرض لمستخدم جديد اختيارات ديمو جاهزة. Edit/Pause/Renew في My Listings ما اتبنوش. فلتر Demand في الـ live مابيعرضش إعلانات الطلب. البحث على آخر 40 بس |
| **الدفع** | VIP وBoost وFeatured: سعر من السيرفر، رقم Fawry، InstaPay بإيصال للمراجعة | مفيش صفحة "مدفوعاتي" ولا إيصال ولا فاتورة ضريبية. اختيار VIP في معالج إنشاء الشركة بيقول "live on VIP" **من غير ما ياخد فلوس ومن غير ما يفعّل حاجة**. مزايا VIP (subdomain، 3 boosts، analytics) مش متبنية |
| **المجموعات** | (بعد `ee2b5f8`) جوّه الجروب شغال: بوستات بصور، like، كومنت، report، طلب انضمام وموافقة، Members وAbout، Manage. **(المرحلة 1) كل كروت الجروبات والسايد بار والأرقام من الداتابيز، وJoin/Leave حقيقيين** | تاب Listings في الـ deal room متخبّي في الـ live لحد ما يتبني. مفيش بحث ولا By Country. خطأ JavaScript لما تدوس على اسم شخص في كارت جروب (G-16). التفاصيل في القسم 2 والجدول 3.3 |
| **الوظايف** | نشر وظيفة، تقديم بـ CV في تخزين خاص (وإشعار لصاحب الوظيفة)، Save، Contact Candidate | **صاحب الشغل مش شايف مين قدّم** (مفيش قايمة متقدمين). "Post My Profile" ما بيحفظش حاجة، فقايمة المرشحين دايماً فاضية. مفيش "طلباتي" ولا تفاصيل وظيفة. الأرقام لسه ثابتة حتى على داتابيز فاضية ("76 open positions"، "6 this week"، "4 candidates"، أرقام الـ seniority، "150,000+") |
| **التدريب** | التسجيل في كورس بيتحفظ | الكورس مجرد كارت: مفيش دروس ولا فيديو ولا تقدّم ولا شهادة، والكورسات بتتضاف بـ SQL بس |
| **الأدمن** | Admin → Review شغال (توثيق بلينكات خاصة، InstaPay). **طابورين جداد في المرحلة 1: 💬 بلاغات الرسايل و🚩 البوستات المبلّغ عنها** (Remove بإشعار للكاتب والمبلّغين، أو Dismiss) | Users / Posts / Ticker / Sponsors / Settings بيقولوا "اتعمل" وما بيعملوش حاجة في الداتابيز. مفيش suspend ولا سجل لأفعال الأدمن. مدخل "⚙️ Admin" ظاهر لأي عضو (A-04) |
| **العربي والموبايل** | مفيش scroll أفقي على 390 px في أي صفحة اتجربت، والـ RTL سليم. كل النصوص الجديدة في المرحلة 1 ليها ترجمة | نصوص إنجليزي متبقية: Apply في الوظايف، Admin Review، الكورسات، "see more"، "What's on your mind, <name>?"، وكمان (لقاها التحقق): رسالة Messages الفاضية، "To *" في New message، toast "Connected! 🤝"، هيدر My Listings، "No supply listings yet…" و"Filters" في الماركت، "Create my page" في المعالج، وإشعار company_message بيتخزّن إنجليزي |

### عشان يبقى جاهز تجارياً محتاج إيه

1. **يوقف الكدب والتسريب (أسبوع تقريباً، adapter أغلبه):** ثغرة New message (S-03)، الـ like (S-02)، حفظ البروفايل (S-01)، الدعوات (S-04)، وشيل/استبدال **كل** محتوى الديمو في الـ live (S-19، B-06، G-02، G-03، G-04، وصفوف My Listings في B-07). القاعدة: في الـ live أي رقم أو كارت مش من الداتابيز يتشال أو يتملي من الداتابيز. **← اتعملت (15 أكتوبر) وفاضل منها:** S-03 في حالة الاسم والشركة المتطابقين، الـ ticker وصور Home (S-19)، My Intents (B-06)، أرقام Jobs (J-05)، وقايمة التفاعلات على العربي 390px (S-02). التفاصيل في جدول المرحلة 1 في القسم 4.
2. **القانوني والحساب:** سياسة خصوصية وشروط استخدام بالعربي والإنجليزي (قانون حماية البيانات 151/2020، وPaymob وFawry بيطلبوها في onboarding التاجر)، صفحة إعدادات، نسيت الباسورد، مسح الحساب (X-01، S-05). النص محتاج محامي أو حضرتك.
3. **قلب البيزنس:** الدليل يتملي (B-01)، الشركة تقدر تحفظ منتجاتها ومواقعها وشهاداتها وفريقها (B-02، B-03، B-04)، والمشتري يقدر يكلّم الشركة (B-05)، والبايع يدير إعلاناته (B-07).
4. **الوظايف والتدريب والأدمن:** قايمة المتقدمين (J-01)، "Post My Profile" (J-03)، أدوات الأدمن الحقيقية (A-01)، وقرار في التدريب: يا إما نبني دروس وشهادات (T-01) يا إما نسمّيه "كتالوج كورسات" بوضوح لحد ما يتبني.
5. **بعدها:** خطوات الإطلاق E5 في `docs/LAUNCH.md` (staging، k6 بـ 2,000 مستخدم، Sentry، الباك أب) — ودي متوقفة على مفاتيحك وعلى الوصول لـ Supabase وVercel.

**كام تقريباً:** المرحلة 1 + 2 في القسم 4 (كل الـ blockers) تقريباً 6–8 أسابيع لمطوّر واحد بنفس طريقة الشغل الحالية (migration + adapter + e2e بيدوس على الزرار + parity). الـ majors بعدها 6–10 أسابيع تانيين. الأرقام دي تقدير، مش وعد.

---

## 2. شغل المجموعات اللي لسه خالص

**الشكوى:** حضرتك فتحت جروب ولقيت هيدر بس — اسم وعدد أعضاء وزرار Leave. مفيش بوستات ولا نقاش ولا أعضاء. ده كان البند الأول في فحص المجتمع (blocker).

**اللي اتعمل (commit محلي `ee2b5f8`، من غير push):**

- **الداتابيز — `supabase/migrations/0027_group_posts.sql`:** `posts.group_id` (بوست الجروب هو بوست عادي، فالـ like والكومنت والصور والـ save والمشاهدات والإشعارات شغالين زي ما هم)، `groups.rules` و`listed` و`pinned_post_id`، جدول `group_join_requests` بـ RPCs (`group_request_join` / `group_cancel_request` / `group_decide_request`)، جدول `group_post_reports`، `group_pin_post()`، `group_activity(ids)`، وأي admin في الجروب (مش المنشئ بس) يعدّل الإعدادات. كل جدول ودالة ليهم GRANT/REVOKE (قاعدة 0026). الفيد الرئيسي بقى `group_id is null`.
- **الواجهة — `web/src/groups.js` و`web/src/groups.css`:** جوّه الجروب تحت الهيدر المعتمد: تابات Discussion · Members · About (وListings في الـ deal rooms)، معمولة من كارت البوست والـ composer المعتمدين كـ template (مش markup جديد). Manage فيه Members & Roles وReports وRequests وSettings.
- **الـ adapter — قسم D3b في `web/src/live/adapter.js`:** الـ hooks (`groupPosts`، `groupPost`، `groupMembers`، `groupJoin`)، الأعضاء من `group_members`، الطلبات والبلاغات والإعدادات في Manage.

**اتحقق منه:**

| الفحص | النتيجة |
|---|---|
| build مرتين | نفس الـ sha: `drugbox.html` sha256 `5c9b45e1…3f216109d8b`، 5,665,701 byte |
| parity | PARITY OK بعد refresh المرجع (تغيير واجهة مقصود ومتجرب) |
| `group_posts.rls.sql` | 120 / 120 |
| `run_all sql sweep migrations` | 13 / 13، والـ sweep 6/6 none، و`migration_check` OK |
| demo + legacy | 28 / 28، منها `groups_test` إنجليزي 63 / 63 وعربي 64 / 64 |
| e2e على الـ stack المشترك | 22 / 22، منها `d3b_group_posts` 61 / 61 و`d3_groups` 29 / 29 و`b2_feed` 18 / 18 |
| السرعة (تبديل الصفحات) | median 13.8 ms مقابل 14.1 ms للمرجع القديم — مفيش بطء |
| سرعة الداتابيز (60 ألف بوست رئيسي + 220 ألف بوست جروبات) | كل الصفحات p95 ≤ 1.9 ms؛ غير عضو بيطلب فيد جروب خاص كان 241 ms واتصلح لـ 8.5 ms |
| تحقق مستقل (grp-verify) بحسابين جداد | في الديمو: كل الـ 12 جروب بيفتحوا بتاباتهم، بوست بصورة، Edit/Delete بـ Undo، reactions، كومنت ولايك كومنت، Repost، Save، Report، Pin، Manage كامل، طلب انضمام لجروب خاص، دعوة وقبول. في الـ live: بوست بصورة بيتحفظ (`posts.group_id` + `post_media`)، الـ like والكومنت والـ report بيوصلوا الداتابيز وبيفضلوا بعد الـ reload، الطلب والموافقة بيعملوا عضوية وإشعار `group_join_approved`، والعربي على 390 px من غير overflow |

اتصلح وقت المراجعة بالعين (`web/src/groups.css`): نقطة الجملة الإنجليزي كانت بتطلع أول السطر في العربي (`unicode-bidi:plaintext` زي البوستات)، وهيدر البوست على الموبايل كان بيتعصر لحد ما كل كلمة في سطر.

**الصور:**
- مراجعة الـ gate (ديسكتوب وموبايل، عربي وإنجليزي، 118 صورة): `/tmp/claude-0/-home-user-new/821674db-a196-55af-97b7-080b6c8aa6d4/scratchpad/finish/grpshots/`
- التحقق المستقل: `/tmp/claude-0/-home-user-new/821674db-a196-55af-97b7-080b6c8aa6d4/scratchpad/v-grp/` — `02_*` كل كارت وكل تاب في الديمو، `03`–`07` أفعال الديمو، `L*` الـ live. أمثلة: `L05_A_after_post.png`، `L13_B_after_like_comment.png`، `L15_B_private_lock.png`، `L20_A_manage_requests.png`، `L31_B_ar_390_g7_disc.png`.
- صور فحص المجتمع قبل الشغل (للمقارنة): `/tmp/claude-0/-home-user-new/821674db-a196-55af-97b7-080b6c8aa6d4/scratchpad/gaps/gap-community/L09-live-member-inside-group.png`

**بنود الفحص الأصلي اللي اتقفلت بالشغل ده:**

| بند الفحص الأصلي | الشدة | الحالة |
|---|---|---|
| عضو يفتح الجروب يقرا وينشر ويناقش | blocker | **اتقفل** (ديمو + live) |
| admin الجروب يدير الأعضاء (ترقية، تنزيل، شيل) | blocker | **اتقفل** — الأعضاء من الداتابيز والأدوار بتتحفظ (d3b). الـ Sub-Admin مخفي في الـ live (الداتابيز admin/member بس) → G-15 |
| admin يعدّل اسم/وصف/خصوصية الجروب | major | **اتقفل** — الأرشفة لسه → G-06 |
| admin يتعامل مع بلاغات جوّه الجروب | major | **اتقفل جوّه الجروب** (`group_post_reports`). بلاغ بوست الفيد وطابور Admin → Review لسه → S-09 وA-03 |
| طلب انضمام لجروب خاص / قبول دعوة | major | **اتقفل** — فتح الجروب من الإشعار لسه → G-05 |
| مستخدم جديد يكتشف جروبات حقيقية | blocker | **لسه** — اتقسم لـ G-02 وG-03 وG-04 وG-07 |
| Deal room: RFQ وعروض وأسعار | major | **ديمو اتعمل، live لسه** → G-01 (بقى blocker لأن الزرار ظاهر ومش بيشتغل) وG-13 |
| كتم إشعارات الجروب | minor | لسه → G-08 |
| Leave / Joined من الكارت | minor | الديمو اتظبط (Leave بتأكيد)؛ عدّاد My Groups لسه → G-10 |

**اللي فاضل في المجموعات:** البنود G-01 لـ G-15 في الجدول تحت (3 blockers، 3 majors، 9 minors). أهمهم: كروت الجروبات الديمو في الـ live بتقبل Join وهمي (G-02)، والقايمة الجانبية بتفتح جروب غلط وتخلّي المستخدم Admin عليه (G-03)، وListings الـ deal room في الـ live فاضي وزرار النشر بيقول "opens soon" (G-01).

**ملاحظات أمانة عن الـ commit:**
- `ee2b5f8` اتعمل بـ `git add -A`، فدخل فيه شغل تاني لسه ماشي: `tests/journeys/` و`tools/qa/deadend_crawler.py` و`qa_lib.js` و`tools/qa/README.md`. الملفات دي ممكن تتغير تاني (وفيه تعديلات عليها لسه مش متعملها commit).
- نفس مشكلة الهيدر المتعصر موجودة في الفيد الرئيسي المعتمد على 390 px لبوست مثبّت (عمود الاسم حوالي 63px). ما اتلمسش لأنه واجهة معتمدة — محتاج موافقتك (S-28).

---

## 3. جدول كل الفجوات

**المفتاح:** `demo` = في الديمو بس، `live` = في الـ live بس، `both` = الاتنين. الترتيب جوّه كل قسم: blocker ← major ← minor. الأرقام (S-01…) للرجوع ليها في القسم 4.

### 3.1 السوشيال: الدخول، البروفايل، الفيد، الشبكة، الرسايل، الإشعارات، البحث

المصدر: فحص gap-social — الصور (47) في `scratchpad/gaps/gap-social/` (`L*` = live)، والسكريبتات في `scratchpad/finish/gap-social-w/`.

| # | الشغلانة | فين | demo/live | الشدة | أصغر تصليح كامل |
|---|---|---|---|---|---|
| S-01 | أعدّل بروفايلي (اسم، headline، شركة، bio، تليفون، موقع) | Profile → ✏️ Edit Profile → Save (`saveProfile`، `web/base/app.html:3136`) | live | blocker — اتقفل | ✅ **اتقفل في المرحلة 1:** الـ adapter بيكتب في `profiles` الأول وبعدين يعرض، والرفض بيسيب المودال مفتوح برسالة؛ Location وOpen to work اتضافوا للمودال؛ migration 0029 (حد لطول الخانات، والموقع لازم يبقى عنوان حقيقي). `J-SOCIAL-22` عدّت ديمو وlive، والمراجع ملا الـ 9 خانات (EN 1440 وAR 390) ولقى الداتابيز مطابقة بعد الـ reload. التليفون مش ظاهر للناس عن قصد. — **الأصل:** الـ adapter يلف `saveProfile` ويعمل `profiles.update(...)`؛ لو فشل يرجّع الشاشة و`toastErr`. يتأكد إن الـ column guard بتاع 0020 بيسمح. e2e يملا المودال الحقيقي ويدوس Save ويعمل reload ويشيّك الداتابيز |
| S-02 | Like / reaction على بوست | زرار Like وقايمة الـ reactions (`doReact`) | live | major (كانت blocker) | 🟡 **اتصلّح الجزء الأساسي في المرحلة 1، لسه مفتوح:** الـ reaction بيتخزّن بنوعه (migration 0028)، و`like_count` صح، وإشعار واحد، والعدد بيفتح قايمة الناس؛ `J-SOCIAL-13` عدّت ديمو وlive. **فاضل (لقاه المراجع):** على العربي 390px قايمة التفاعلات بتطلع برّه الشاشة من الشمال (4 من 6 مايتداسوش)، ومفيش ضغطة طويلة على الموبايل. موجودة في الديمو المعتمد من قبل، وتصليحها تغيير واجهة محتاج موافقتك. — **الأصل:** الـ adapter يلف `doReact(pid, kind)` (upsert/delete في `reactions`). migration توسّع `reactions.kind` لأنواع الواجهة (like, celebrate, insightful, support, appreciation, curious) + GRANT. `b2_feed_test` يدوس `[data-lp]` بدل `likePost()` |
| S-03 | أبعت رسالة لشخص جديد من الـ inbox | Messages → ✎ → To → Send | live | blocker | 🔴 **اتصلّح أغلبه في المرحلة 1، لسه مفتوح:** ✎ New message بقى بيبعت للي اتختار في To بس، والاسم اللي مش عضو أو اللي أكتر من عضو شايلينه بيترفض برسالة؛ `J-SOCIAL-36` عدّت ديمو وlive. **فاضل (لقاه المراجع):** لو عضوين ليهم نفس الاسم ونفس الشركة (أو نفس الاسم ونفس الـ headline الافتراضي، شوف S-15)، الاختيارات بتطلع متطابقة والرسالة بتروح لآخر واحد في `NM.map` من غير تحذير (`adapter.js` `nmOptions`/`nmResolve`). التصليح: قيمة كل اختيار تبقى فريدة (حتة من الـ id لما تتكرر)، أو رفض لما القيمة تطابق أكتر من شخص، وe2e بعضوين متطابقين. — **الأصل:** **ثغرة خصوصية**: الرسالة راحت لآخر شات مفتوح (Bassem) مش للي اتكتب اسمه. الـ adapter يمسك ✎ والـ Send، يدوّر على المستلم live (الاتصالات الأول)، ويبعت بس لو شخص واحد مطابق (`MX.open = aid(uuid)`)، غير كده "اختار عضو". الـ datalist من الاتصالات الحقيقية. e2e يشيّك `receiver_id` |
| S-04 | أقبل طلب اتصال / أشوف طلباتي | My Network → Pending invitations (`renderNetwork`) | both | blocker — اتقفل | ✅ **اتقفل في المرحلة 1:** Pending invitations من الطلبات الجاية ليّا بـ Accept/Decline بيتحفظوا، Sent requests بـ Withdraw، الـ badge حقيقي، وConnect بيفضل في البروفايل (migration 0030). `J-SOCIAL-29` و`-30` و`-31` عدّت ديمو وlive، والمراجع جرّبها (EN 1440 وAR 390) ووافق. — **الأصل:** الكارت يتبني من الطلبات **الجاية ليّا** مش اللي بعتّها، و`.pending-row` ياخد handler مفوَّض بـ `acceptConnection`/`declineConnection`. طلباتي أنا تظهر "Pending" على كروت الاقتراحات. نفس الـ template المعتمد |
| S-05 | أرجّع باسورد نسيته | صفحة الدخول | both | blocker | (موافقة) لينك "Forgot password?" وكارت باسورد جديد. الـ adapter: `resetPasswordForEmail` وعلى `PASSWORD_RECOVERY` → `updateUser({password})`. الـ gateway يحاكي `/recover` للاختبارات |
| S-06 | أحط صورتي والغلاف | Profile → 📷 (`handleAvatarChange`)، Edit cover | both | blocker | migration: bucket `avatars` (public، `<uid>/…`، صور، 2 MB) بـ policies وGRANTs. الـ adapter يرفع ويحدّث `profiles.avatar_url` والشريط و`USERS`. الغلاف: file input و`profiles.cover_url` (تغيير ديمو) |
| S-07 | أحفظ بوست وألاقيه بعدين | Save، ⋯ → 🔖، "Saved items"، صفحة Saved | both | major | 🟡 **اتصلّح في المرحلة 1، مستني تحقق مستقل:** Save بيكتب في `saved_posts` ويتحوّل لـ "🔖 Saved"، و"Saved items" بيفتح Saved بالبوستات (الأحدث الأول)؛ `J-SOCIAL-17` عدّت ديمو وlive. الوظايف والإعلانات في Saved لسه (J-06، `J-SOCIAL-48`). — **الأصل:** زراير Save تنادي `savePost(id)` واللينك `goto('saved')`. الـ adapter يحمّل `saved_posts` في Saved ويلف `unsavePost`. e2e بيدوس الزرار |
| S-08 | Repost / Copy link | زرار Repost، ⋯ → 🔗 | both | major | الحد الأدنى: Repost يفتح كارت الـ share (`share.js`) وCopy link ينسخ `#/post/<id>`. الكامل: جدول `reposts` بعدّاد واحد على `posts.share_count` + RLS + GRANTs |
| S-09 | أبلّغ عن بوست/شخص/شات، أعمل Block | ⋯ → 🚩 Report؛ Messages ⋯ → Report / Block / Clear / Mute / Favorites | both | major | 🟡 **اتعمل جزء في المرحلة 1:** بلاغ البوست بأسباب (`post_reports`، 0028)، وBlock وMute وReport في الرسايل (`user_blocks`، `conversation_mutes`، `message_reports`، 0031 — والداتابيز بترفض الرسايل في الاتجاهين بعد Block)؛ `J-SOCIAL-20` و`-40` عدّت ديمو وlive. **فاضل:** بلاغ عن شخص أو كومنت، وطابور الأعضاء المبلّغ عنهم (`J-SOCIAL-51`)، واللي عملك Block لسه بيظهر في اقتراحات New message. — **الأصل:** migration: `content_reports` (post/comment/user/message)، `user_blocks` + policy على `messages` ترفض المحظور، `conversation_prefs`. الـ adapter يوصّلهم، وتاب Reports في `dxModeration` |
| S-10 | أشوف كل اتصالاتي وأديرهم | My Network | both | major | 🟡 **اتصلّح في المرحلة 1، مستني تحقق مستقل:** قايمة "My connections" ببحث وMessage وRemove (بتأكيد، وبيتمسح للطرفين)؛ `J-SOCIAL-32` عدّت ديمو وlive. — **الأصل:** (موافقة) Connections stat يفتح قايمة من template الـ sugg-card بـ Message وRemove. policy مسح للطرفين + GRANT. `clearSeeds` يمسح `CONN_STATE` ≤ 1000 (أرقام "2 CONNECTIONS / 2 PENDING" الديمو) |
| S-11 | أعمل Follow لشخص | بروفايل حد → + Follow | both | major | 🟡 **اتصلّح في المرحلة 1، مستني تحقق مستقل:** Follow بيتحفظ (migration 0030) بإشعار واحد وعدّاد متابعين صح؛ `J-SOCIAL-33` عدّت ديمو وlive. — **الأصل:** migration: `user_follows` بعدّاد واحد على `profiles.followers_count` + RLS + GRANTs + إشعار. أو نشيل الزرار لحد ما يتبني |
| S-12 | أعدّل بوست بعد نشره | ⋯ → ✏️ Edit | both | major | نفس مودال Create Post متملي. policy تعديل للبوست بتاعي (body/category بس) + `edited_at` |
| S-13 | أرد على كومنت، Like لكومنت، أمسح كومنتي | صف الكومنت | both | major | `comments.parent_id` للردود، `comment_reactions` بعدّاد، policy مسح، load more، `showReactors` يفتح قايمة |
| S-14 | أبني بروفايل مهني (خبرة، تعليم، مهارات، لغات) | تابات About / Experience / Skills | both | major | (موافقة) "+ Add" بـ `DBK.modal`. الـ adapter يقرا ويكتب `profiles.experience/education/skills/languages`. نشيل أرقام الـ endorsements المتألفة أو جدول `endorsements` |
| S-15 | أسجّل بشركتي وتخصصي | فورم التسجيل | both | major | 🟡 **اتصلّح في المرحلة 1، لسه مفتوح:** الشركة والتخصص بيتحفظوا (`handle_new_user` في 0029)، والديمو مابقاش بيورّث هوية د. هيثم؛ `J-SOCIAL-01` عدّت ديمو وlive. **فاضل (لقاه المراجع):** خانة Role أول اختيار فيها "Regulatory Affairs" متختار لوحده، فكل اللي مابيغيّروهاش بياخدوه، وفي الواجهة العربي بيتخزّن "الشؤون التنظيمية" — ده بيكتّر الأسامي المتشابهة في S-03 وبيخلّط لغات الـ headline. التصليح: اختيار فاضي "اختار تخصصك" وقيمة إنجليزي ثابتة. — **الأصل:** الـ adapter يبعت `{name, company, specialty}`. migration: `handle_new_user` ينسخهم. الديمو: `doSignup` ما ياخدش headline الدكتور هيثم |
| S-16 | أأكد إيميلي ولو الإيميل ما جاش | التسجيل في الـ live | live | major | رسالة تنبيه مش خطأ، "Resend" (`auth.resend`)، و`emailRedirectTo` |
| S-17 | إعدادات الحساب (إيميل، باسورد، إشعارات، خصوصية، مسح) | — | both | (مدموج في X-01) | نفس شغل X-01، ما اتعدّش مرتين |
| S-18 | ألاقي شخص/شركة/إعلان/وظيفة بالاسم | Ctrl+K والبحث في الشريط | live | major | migration: RPC `search(q, kinds, limit)` بـ trigram + GRANTs. الـ adapter يستبدل مصادر `buildIndex` بنداء debounced، و`clearSeeds` يفضّي `PRODUCTS` |
| S-19 | أثق إن اللي شايفه في حساب جديد حقيقي | badges الشريط الجانبي، الشبكة، الفيد، الرسايل | live | major | 🟡 **اتصلّح أغلبه في المرحلة 1، لسه مفتوح:** badges السايد بار والموبايل حقيقية، وYour shortcuts وجروبات صفحة Network من جروباتي، وEvents وTrending اتشالوا، و"12K+" بقى العدد الحقيقي، وOnline now وهيدر الشات الديمو اتخبّوا، وUnread حقيقي. المراجع شاف Network وMessages وGroups وNotifications وSaved نضاف على داتابيز فاضية. **فاضل:** (1) الـ ticker فوق كل صفحة بيعرض إعلانات الديمو ("Metformin HCl GMP $5.80/kg"، "WHO-GMP Tablets — Quadra Pharm"، "Fette 1200 Tablet Press $45K"…) لحد ما الماركت يتفتح وفيه إعلانات، لأن `paintMarket` في الـ adapter هو بس اللي بيبدّل `TICKER_ITEMS` — لازم يتبدّل عند الدخول (من `ticker_items` أو الإعلانات) أو يتخبّى؛ (2) Home فيه 6 صور stock جنب "N professionals" وكارت TODAY فاضي على داتابيز فاضية؛ (3) صفحة الدخول لسه بتقول "12K+". — **الأصل:** نفس طريقة F-54: `.nl-badge` تمشي مع العدادات الحقيقية؛ نشيل أو نملا Groups وEvents وTrending و"12K+ professionals" و"Online now" و"Unread (2)" وهيدر الشات |
| S-20 | أفتح الحاجة اللي الإشعار بيتكلم عنها | صفوف الإشعارات | both | major | 🟡 **اتعمل جزء في المرحلة 1:** إشعار التفاعل والكومنت بيفتح البوست (والكومنتات مفتوحة) في الـ live. **فاضل:** "View profile" على إشعار طلب الاتصال، وإشعارات الديمو مش مربوطة ببوست (`J-SOCIAL-42`)، وإشعارات الجروبات (G-05). — **الأصل:** الضغط يروح للهدف (بوست → feed + `dgJump`، شخص → `gotoProfile`، صفقة/وظيفة → صفحتها). بعدها ملخص إيميل من Edge Function |
| S-21 | زرار Back، الـ refresh، لينك لصفحة أو بوست | الأبلكيشن كله (`goto`) | both | major | hash routes (`#/network`، `#/profile/<id>`، `#/post/<id>`، `#/messages/<id>`) بـ `pushState` و`popstate`. محتاج parity جديد |
| S-22 | لينك، hashtag، mention في بوست | Create Post والبوستات | both | major | linkify آمن (http/https، `rel=noopener`)، #tag يفتح البحث، autocomplete للـ @mention، و`post_mentions` بإشعار |
| S-23 | أنشر منتج أو وظيفة من الـ composer؛ فيديو أو استطلاع | اختصارات الـ composer | both | minor | Product → مودال "Post supply"، Job → نشر الوظيفة (الاتنين موجودين وشغالين live). فيديو البوست بـ `dxMedia` |
| S-24 | أكلّم أو أفتح بروفايل اللي بشات معاه | هيدر الشات 📞 👤 | both | minor | 👤 → `gotoProfile`. 📞 يتشال أو `tel:` لو الطرف التاني شارك رقمه |
| S-25 | أعرف مين شاف بروفايلي وأداء بوستاتي | إحصائيات البروفايل | live | minor | الـ adapter ينادي `increment_profile_view` و`increment_post_views` (موجودين في الداتابيز وما حدّش بيناديهم) |
| S-26 | أدوّر جوّه الرسايل | Messages → 🔍 | both | minor | 🟡 **اتصلّح في المرحلة 1، مستني تحقق مستقل:** البحث بيدوّر جوه الرسايل (في الـ live من الداتابيز) ويفتح المحادثة على الرسالة، وفيه حالة فاضية؛ `J-SOCIAL-39` عدّت ديمو وlive. — **الأصل:** RPC `search_my_messages(q)` بـ trigram |
| S-27 | الأبلكيشن بالعربي من غير إنجليزي | toasts الحاجات اللي مش متعملة | both | minor | "Reposted!"، "Edit coming soon"، "Cover upload coming soon"… للـ `i18n.js`، والأحسن تتبني الحاجات نفسها |
| S-28 | هيدر بوست مثبّت على الموبايل | الفيد الرئيسي 390 px | both | minor | نفس تصليح الجروبات في `groups.css` (الـ pills تنزل تحت الاسم). تغيير واجهة معتمدة — محتاج موافقة (لقاه grp-gate) |
| S-29 | أعرف إيه اللي حصل لطلب الاتصال بتاعي، وأكتب ملاحظة مع الطلب | My Network → Sent requests؛ Connect | both | minor | (جديد، لقاه التحقق بعد المرحلة 1 — محتاج قرارك) لما الطرف التاني يرفض، الطلب بيفضل "Pending" عند اللي بعته على طول. ده مقصود في 0030 عشان اللي رفض مايتحرجش، ومحتاج تأكيدك. ومفيش نافذة ملاحظة مع Connect |

### 3.2 البيزنس: الشركات، الصفقات، الماركت، الدفع، VIP

المصدر: فحص gap-business — الصور في `scratchpad/gaps/gap-business/` (`L*` = live)، والسكريبتات في `scratchpad/gb/`.

| # | الشغلانة | فين | demo/live | الشدة | أصغر تصليح كامل |
|---|---|---|---|---|---|
| B-01 | ألاقي مصنع أو CMO أو مورّد، أو أعمل claim لصفحة شركتي | Companies → الدليل؛ Add or claim | live | blocker | الدليل فاضي (`companies=0`، `L01-live-companies-empty.png`) والـ README بيقول "pre-filled from public lists" ومفيش importer. `tools/import_companies.py` + CSV من قوايم EDA/IDA/الغرفة: `status='unclaimed'`، `source='public_list'`، مواقع ومنتجات، idempotent. يتشغّل في `supabase_deploy.sh` للـ staging. مفيش تغيير واجهة |
| B-02 | صاحب الشركة ينشر كتالوج منتجاته (صور، logo، غلاف) | Workspace → Page → Edit page | live | blocker | بيقول "published" وبعدين "not saved online yet"؛ `company_products=0`. migration: price/unit/moq/description/image_path + policy كتابة لـ owner/admin + GRANTs + مسار `companies/<id>/…`. `persistEdits` يعمل diff ويكتب ويرفع، ويتشال الـ toast |
| B-03 | أضيف مصانعي ومخازني بشهادات GMP/ISO وتواريخ انتهاء | Workspace → Sites | live | blocker | `company_sites=0` والموقع بيختفي بعد reload (L03)؛ الشركة عمرها ما توصل Level 2/3 لوحدها. الـ adapter يكتب `company_sites` و`site_certificates` بالملف في `documents/verification/…`؛ `checked_at` للأدمن بس. policies + GRANTs |
| B-04 | أدخّل زمايلي في حساب الشركة (sales / QA / HR) | Workspace → Team؛ "Ask to join the team" | both | blocker | الدعوة بتقول "sent" و`company_members=1`. RPCs `company_invite` / `company_join_request` / `company_member_respond`، ربط الدعوة في `handle_new_user`، الفريق من `company_members`، `company_routing` من الأدوار، Accept/Decline في الإشعارات، وإيميل دعوة |
| B-05 | المشتري يكلّم الشركة من صفحتها | Company page → Message | live | blocker — اتقفل | ✅ **اتقفل في المرحلة 1:** الداتابيز هي اللي بتختار المستلم (العضو المتوجّه له لو موافق يبان للناس، وإلا المالك)، بإشعار واحد في اليوم لكل مشتري وشركة؛ والشركة اللي مالهاش حد بتقول كده وبتفتح تاب Contact (migration 0032). `J-BUSINESS-06` عدّت ديمو وlive، والمراجع جرّبها بشركة لسه متعملة من المعالج (EN 1440 وAR 390): الرسالة وصلت للمالك بإشعار، والرد وصل للمشتري. — **الأصل:** بيفشل لأن الفريق فاضي. المستلم من `company_routing` (`quote`) وإلا `companies.owner_id`، بالـ UUID مش بالاسم |
| B-06 | أشوف ماركت حقيقي قبل ما أنشر أو أدفع boost | Marketplace → Browse | live | blocker | 🟡 **اتصلّح أغلبه في المرحلة 1، لسه مفتوح:** الأرقام من `market_stats()` (migration 0033)، و"Live now" والخدمات والوظايف حقيقية أو حالة فاضية، وجدول Free vs Sponsored و"150,000+" و"8×" اتشالوا؛ المراجع شاف Browse نضيف على داتابيز فاضية. **فاضل:** My Intents بتعرض لمستخدم جديد اختيارات جاهزة ماختارهاش ("📦 APIs: I have this to sell"، "🏭 CMO: I have a facility to offer"…) تحت "How this appears on your profile"، والـ ticker (S-19). و`J-BUSINESS-34` لسه واقفة: فلتر Demand في الـ live مابيعرضش إعلانات الطلب. — **الأصل:** مع 0 إعلانات: "1.2K listings"، "Live now: Vivian Zhou…"، "Showing 853"، خدمات ووظايف ديمو، "150,000+"، "8× more views". **إعلان مضلِّل لمنتج مدفوع.** RPC `market_stats()`، "Live now" من آخر إعلانات حقيقية أو يتخبّى، `.scard`/`.jcard` من الداتابيز بالـ template، ونخبّي أرقام Free vs Sponsored لحد ما يبقى فيه analytics |
| B-07 | أدير إعلاناتي (سعر، مخزون، إيقاف، تجديد، مسح، مشاهدات) | Marketplace → My Listings | both | blocker | 🟡 **اتعمل جزء في المرحلة 1:** صفوف الديمو اتشالت — My Listings بتعرض إعلاناتي وطلباتي بس (والمراجع شافها فاضية لحساب جديد)، ومشاهدات واستفسارات الديمو اتخبّت. **فاضل:** Edit/Pause/Delete/Renew (`J-BUSINESS-40` بتقف عند "مفيش Edit"). — **الأصل:** ولا حاجة بتتحفظ، والـ live بيعرض صفوف ديمو جنب الحقيقي (L09). migration: expires_at, paused, views, enquiries + policy تعديل/مسح للمالك + job يومي. الصفوف من منتجات المستخدم، وhandlers لـ Edit/Pause/Delete/Renew/Boost. الديمو يحفظ في `DBK.store` |
| B-08 | أبعت RFQ منظّم وأستقبل عرض بسعر وأقارن | Contact Supplier / Request Quote / Quote → | both | major | يمشي في محرك الصفقات (`dxDeals.create('quote', …)`). `deal_create` يقبل بايع فرد أو شركة + `deals.listing_id`/`enquiry_id`. Requests & deals والمقارنة يشتغلوا من غير تغيير |
| B-09 | إعلانات موثوقة: صور، COA، شهادات متوثقة، سعر بعملة | Create Listing | both | major | `products.company_id, currency, image_path, coa_path, certs_verified` (أدمن بس). الشهادات المدّعاة تبان tag عادي و✓ بس لو متوثقة. `data-cat` من الفئة (CMO/Equipment/… بتتحفظ كلها supply دلوقتي) |
| B-10 | أدوّر في الماركت كله | بحث وفلاتر الماركت | live | major | بيحمّل آخر 40 بس. RPC `market_search(...)` بـ full-text/trigram وعدد كلّي، "Show more"، ولينك `?l=<id>` |
| B-11 | أثبت الـ compliance بمستندات (CEP, DMF, GDP…) | Compliance passport | both | major | محفوظ في `localStorage` بس ومفيش رفع ملف. `docsOf/addDoc` على `company_documents` برفع، وAdmin → Review يراجعها |
| B-12 | أخلّص صفقة بورق حقيقي (COA، PO، فاتورة، NDA، data room) | deal thread | both | major | جدول `deal_files` + تخزين خاص للطرفين، NDA كـ deal_event بالنسخة والموقّع، حقل ملف اختياري في الفورمز، "Download PO (PDF)" |
| B-13 | يوصلني خبر برّه الأبلكيشن (RFQ، رد، دفع) | الصفقات والدفع | live | major | Edge function `notify-dispatch` من outbox على الإشعارات (إيميل SMTP/Resend، WhatsApp اختياري) + اختيار on/off في الإعدادات |
| B-14 | أشوف مدفوعاتي وإيصالاتي وفواتيري، وأرجع لرقم Fawry | Plan & verification | live | major | قسم Payments من `payment_orders` (رقم Fawry وانتهاؤه، الحالة، vip_until) بـ "Pay again" و"Download receipt". رقم فاتورة متسلسل في `confirm_payment`، `create_order` يرفض طلب pending مكرر، وعنوان Featured في `checkout.js` |
| B-15 | أختار VIP وأنا بعمل الشركة وأدفع | Add or claim → 3 of 3 | live | major | بيقول "is live on VIP" والشركة free ومفيش طلب دفع (L13). نفس طريقة "Pay for VIP": طرق الدفع الحقيقية، `persistCreated` الأول وبعدين `dxPay.start(...)`، والـ toast "VIP يبدأ لما الدفع يتأكد" |
| B-16 | آخد مزايا VIP اللي دفعتها | كارت خطة VIP | both | major | subdomain و"3 boosts شهرياً" والـ analytics مش متبنيين. يا نشيلهم من `PLANS.feats` (`directory.js`) دلوقتي، يا نبنيهم (`company_credits`، `company_view_log`، wildcard domain) |
| B-17 | أقرا تقييمات الطلبات وأرد عليها كمورّد | Reviews tab؛ Reports & reviews | live | major | الـ adapter بيرجّع `{}` لـ `supplier_reviews`. RPC `company_reviews(p_company)` من أحداث rate + رد ونزاع في الداتابيز + طابور في Admin → Review |
| B-18 | badge عضوية الغرفة / مجلس التصدير | Workspace → Memberships | both | minor | صف `company_documents` نوع membership وتأكيد من أدمن Drugbox |
| B-19 | مين في الفريق عمل إيه | Workspace → Activity | live | minor | جدول `company_activity` + `companies.updated_sections`، hook في `dxStoreHook` |
| B-20 | أعرف مين هيستلم طلب السعر | Medsinia → Request a quote | demo | minor | الاسم مختلف في 3 أماكن. `dxHub.route(slug,'quote')` في المودال والـ toast، والوحدة من المنتج |
| B-21 | شاشات البيزنس بالعربي | "Do it"، "Back" في الـ deal thread | both | minor | للـ `i18n.js` |
| B-22 | صفحة شركة جديدة تبان صح | صفحة الشركة → البانر وتاب Contact | live | minor | (جديد، لقاه التحقق) شركة اتعملت من دقيقة بتطلّع "Some information on this page was last updated more than 6 months ago (about, products, sites, contact)" (وبالإنجليزي في العربي كمان)، و"Who answers" بيقول عن المالك "(Admin)" / "(مدير)" بدل Owner. الحساب من آخر تحديث حقيقي للشركة، والنص للـ `i18n.js`، و"Owner" للمالك |

### 3.3 المجموعات (اللي فاضل بعد `ee2b5f8`)

المصدر: التحقق المستقل grp-verify — الصور في `scratchpad/v-grp/`، والسكريبتات في `scratchpad/vg/`.

| # | الشغلانة | فين | demo/live | الشدة | أصغر تصليح كامل |
|---|---|---|---|---|---|
| G-01 | أنشر RFQ أو عرض في deal room وأسعّر على RFQ غيري | live → deal room → 📦 Listings (`adapter.js:1762` بيرجّع `undefined`) | live | major (كانت blocker) | 🟡 **الحل المؤقت اتعمل في المرحلة 1:** تاب Listings متخبّي في الـ live (بيرجع لوحده لما الـ adapter يحط `window.dxLiveGroupListings`)، فمابقاش فيه زرار بيقول "opens soon". **فاضل:** بناء الإعلانات جوه الـ deal room؛ `J-COMMUNITY-02` و`-13` بيقفوا عنده عن قصد. — **الأصل:** migration (`group_id` على الإعلانات أو `group_listings` + `group_listing_quotes`، RLS للأعضاء، GRANTs) والـ hooks `groupListings`/`groupListing` (create, quote) — والـ quote يفتح شات مع المشتري. **لحد ما يتعمل: نخبّي تاب Listings في الـ live** بدل زرار بيقول "opens soon" (`L06_A_listings.png`) |
| G-02 | أتصفّح الجروبات وأنضم كمستخدم جديد | live → Groups: كروت من غير `data-gid` (CMO, QA/QC "14 of your connections", Nutraceuticals, Packaging, Careers, MedDev) | live | blocker — اتقفل | ✅ **اتقفل في المرحلة 1:** كل كروت الجروبات في الـ live من الداتابيز، و`links.js` مابيعملش Join محلي في الـ live. `J-COMMUNITY-09` عدّت ديمو وlive، والمراجع شاف صفحة Groups نضيفة على داتابيز فاضية (أرقام 0 وحالات فاضية). — **الأصل:** Join بيقول "You joined" ويفتح جروب فاضي بـ composer، ومفيش حاجة في الداتابيز، وبعد reload يرجع (`L10_B_sample_QAQC.png`). `paintGroups` يشيل كل `#gx .gcard` من غير `data-gid` في كل الأقسام، و`links.js` ما يعملش Join محلي لما `window.dxLive` موجود. e2e: مفيش كارت من غير `data-gid` في الـ live |
| G-03 | أفتح جروب من قايمة "Your Groups" الجانبية | live → `.mygroup` | live | blocker — اتقفل | ✅ **اتقفل في المرحلة 1:** القايمة من جروباتي الحقيقية وكل صف بيفتح جروبه، وبتتحدّث مع Join/Leave (في الديمو كمان). `J-COMMUNITY-09` عدّت ديمو وlive، وخطوة فتح الجروب من السايد بار في `J-COMMUNITY-02` عدّت في الـ live، والمراجع شاف الصفحة نضيفة. — **الأصل:** حساب جديد شايف 4 جروبات ديمو؛ الضغط على واحد فتح جروب **تاني** وخلّى المستخدم ADMIN بـ Manage وInvite (`L11_B_side_row.png`). القايمة تتبني من `GX.mine` + `group_activity` وكل صف → `dxLive.openGroup(gid)`، وحالة فاضية لو مفيش |
| G-04 | أشوف نشاط جروباتي بنظرة | شريط النبض، "My Groups (4)"، "View all 4"، Activity Score، قسم "Your Groups" | live | major | 🟡 **اتصلّح في المرحلة 1، لسه مفتوح رسمياً:** شريط النبض و"My Groups (N)" و"View all N" والجروب الـ trending وعدد أعضاء Manage والـ Danger Zone من الداتابيز، والـ Activity Score متخبّي في الـ live؛ خطوات 2 و3 في `J-COMMUNITY-01` (الأرقام وMy Groups) عدّت في الـ live. مش مقفول لأن الرحلة كلها لسه واقفة عند By Country (G-07) في الـ live وعند فلتر Pharma في الديمو. — **الأصل:** أرقام متألفة ("27 unread"، "top 12%"…) وقسم "Your Groups" فيه جروبات مش عضو فيها. من `GX.mine` و`group_activity`، ونخبّي الـ Activity Score أو نحسبه |
| G-05 | أفتح الجروب من الإشعار (اتقبلت، كومنت أو reaction على بوستي) | Alerts → إشعار | live | major | ما بيعملش حاجة (`L21_B_notifs.png`، `L23_A_notif_commented.png`). في handler الإشعارات: `group_id` → `dxLive.openGroup(gid)`، وبوست جروب → يفتح الجروب ويـ scroll لـ `[data-gpp=postId]` |
| G-06 | أمسح أو أأرشف جروبي بأمان | Manage → Danger Zone | live | major | جروب بعضو واحد مكتوب عليه "412 real members… forever" (`L20_A_manage_requests.png`)، و"Archive Instead" بيقول "not available yet". العدد من `g.member_count`، والأرشفة يا تتخبّى يا تتعمل بـ `groups.archived_at` |
| G-07 | أدوّر على جروب بالاسم وأفلتر بالدولة/القطاع | Groups → الفلاتر | both | minor | مفيش بحث، و"By Country" و"Pharma/Cosmetics" مجموعات ديمو ثابتة. `groups.country` و`groups.sector` في مودال Create، و`ilike` على الاسم |
| G-08 | أكتم إشعارات جروب | هيدر الجروب → 🔔 | both | minor | بيغيّر الكلام بس. `group_members.muted` (أو `localStorage` في الديمو) ويتحترم في إشعارات بوستات الجروب (وهي أصلاً مش موجودة لسه) |
| G-09 | الجروب بالعربي لأي مستخدم live | placeholder الـ composer (والفيد) | live | minor | "What's on your mind, Member?" — `i18n.js:91` بيترجم جملة الديمو بالاسم بس. قاعدة PATTERNS: `/^What's on your mind, (.+)\?$/` → "بماذا تفكر يا $1؟" |
| G-10 | "Your Groups" و"My Groups" يتحدّثوا بعد الانضمام | Groups بعد + Join | both | minor | بعد join/leave نعيد رسم `.mygroup` وعدّاد الـ cf-tag من الكروت المنضم ليها |
| G-11 | أثق في أرقام النشاط | API Sourcing: الكارت "12 new posts" وجوّه "2 new posts today" و5 بوستات بس | demo | minor | الأرقام من نفس الـ seed، و"1 new post" مفرد في `paintHeader` |
| G-12 | أشوف كل الأعضاء / كل جروباتي | "+ 3,794 more members"، "View all →" | demo | minor | شكلهم بيتداس وما بيعملوش حاجة. الأول caption من غير cursor، والتاني يغيّر للفلتر المناسب |
| G-13 | أتابع الـ RFQ بتاعي في deal room | demo → Listings → "Your request" | demo | minor | مفيش "Quotes (n)" ولا Close/Edit، والعرض اللي ببعته ما بيوصلش للمشتري. يتصمم مع G-01 |
| G-14 | أقرا بوست طويل بالعربي | "see more" (`web/base/app.html:2479`) | both | minor | جوّه `.post-body` اللي الـ i18n بيتخطاه. node ليه ترجمة "عرض المزيد" — تغيير في الصفحة المعتمدة، parity جديد |
| G-15 | Like لكومنت جوّه جروب live، ودور Sub-Admin | live → كومنت جوّه جروب؛ Manage → Roles | live | minor | بيطلع "Liking comments is not available yet"، والـ Sub-Admin مخفي لأن الداتابيز admin/member بس. `comment_reactions` (نفس S-13) و`moderator` في الـ role check أو نشيل الصف (لقاه grp-gate) |
| G-16 | أدوس على اسم شخص في كارت جروب | Groups → `span.dx-entity` (مثلاً "Dr. Alia Mourad") | demo | minor | (جديد، لقاه الـ crawler) البروفايل بيتفتح وبعدين `open()` في `groups.js` بينادي `openGroup` وبيقع بـ `Cannot read properties of null (reading 'classList')` لأن `#groupDetail` مش موجود. الـ handler بتاع كروت الجروبات يتجاهل الضغط على `.dx-entity`، أو `open()` يتأكد إن الصفحة موجودة. موجود في الديمو المعتمد من قبل المرحلة 1 |

(الـ badges الجانبية 3/5/8 لحساب جديد اللي لقاها grp-verify هي نفسها S-19، ما اتعدّتش تاني.)

### 3.4 الوظايف

المصدر: فحص gap-community — الصور في `scratchpad/gaps/gap-community/` (مثلاً `L02-live-employer-jobs.png`).

| # | الشغلانة | فين | demo/live | الشدة | أصغر تصليح كامل |
|---|---|---|---|---|---|
| J-01 | صاحب الشغل يشوف مين قدّم ويعمل shortlist / رفض / تعيين | Jobs (I'm Hiring)؛ إشعار "X applied" | both | blocker | B قدّم بـ CV واتحفظ، وA مش شايف أي حاجة. على كارت وظيفتي "Applicants (n)" بدل Apply → `DBK.modal`: الاسم، الملاحظة، "Open CV" (signed URL)، Message، وstatus. الإشعار يفتح القايمة. trigger إشعار للمتقدم لما الحالة تتغير. الداتابيز والـ policies جاهزين |
| J-02 | الباحث يتابع طلباته أو يسحب واحد | Jobs / البروفايل | both | major | "My applications" (job, company, date, status) بـ Withdraw (الـ policy موجودة) + trigger إشعار |
| J-03 | الباحث ينشر بروفايله عشان الشركات تلاقيه | Jobs → I'm Job Hunting → Post My Profile | both | blocker | ما بيحفظش (`open_to_work` فاضل false) و"Upload CV" مش file input، فقايمة "Available Candidates" دايماً فاضية في الـ live وهي مكتوب عليها "4 candidates". الـ adapter يلف `submitGeneric` لما `#postCandidateModal` مفتوح ويكتب في `profiles`، file input للـ CV في `documents/cv/<uid>/` + `profiles.cv_path` بـ RPC signed URL للشركات الموثّقة، وزرار "Open to work" |
| J-04 | أقرا تفاصيل الوظيفة قبل ما أقدّم | كارت الوظيفة | both | major | مودال تفاصيل (requirements, benefits, deadline). Post a Job: الدولة من الـ location (دبي بتتحفظ EG دلوقتي)، شركة أو "Independent recruiter"، اسم في الـ toast، و"My jobs" بـ Edit/Close |
| J-05 | أدوّر وأقلّب في كل الوظايف والأرقام صح | هيدر وقوايم Jobs | both | major | 🔴 **لسه مفتوح (المراجع أكّده بعد المرحلة 1):** على داتابيز فاضية وعلى داتابيز فيها 63 وظيفة الصفحة بتقول 76، و"Open Positions 76 jobs" فوق "No open jobs yet" على طول، و"Available Candidates 4 profiles" فوق قايمة فاضية. — **الأصل:** "76 open positions"، "6 this week"، أرقام الـ seniority، "150,000+" ثابتين. من `JX.jobs`/`TR.cands` أو `jobs_stats`، بحث، و"Load more" (بيحمّل 60 بس) |
| J-06 | Saved: الوظايف والبوستات والإعلانات | الشريط → Saved | both | major | `saved_jobs` بيتحفظ ومفيش صفحة بتعرضه. تابات Posts · Jobs · Listings من templates كل نوع. الديمو يحفظ الوظايف والتسجيلات في `DBK.store` (الوظيفة اللي اتنشرت في الديمو بتختفي والـ toast بيقول "now visible") |
| J-07 | تنبيه وظايف ("وظيفة QA في القاهرة") | Jobs | both | minor | `job_alerts` + trigger على `jobs` بإشعارات محدودة + "Save this search" |

### 3.5 التدريب

| # | الشغلانة | فين | demo/live | الشدة | أصغر تصليح كامل |
|---|---|---|---|---|---|
| T-01 | أفتح كورس وأذاكره وأخلّصه وآخد شهادة | Training (`renderTraining`؛ E3؛ 0019) | both | blocker | الكورس كارت + Enroll بس: مفيش دروس ولا مدرّب ولا ميعاد ولا سعر ولا تقدّم ولا شهادة ولا Unenroll، والكورسات بـ SQL بس، والعناوين إنجليزي في العربي. migration: instructor/format/starts_at/price/title_ar، `course_lessons`، `lesson_progress`، `complete_course()`، `certificates` بصفحة تحقق عامة. مودال الكورس، "My courses"، شهادة بـ QR (`qrcode.min.js` موجود)، تاب Courses للأدمن، والمدفوع بـ `dxPay` |

### 3.6 الأدمن

| # | الشغلانة | فين | demo/live | الشدة | أصغر تصليح كامل |
|---|---|---|---|---|---|
| A-01 | أدمن Drugbox يدير المحتوى والحسابات (مسح بوست، توثيق، إيقاف، دور) | Admin → Users / Posts / Market Board / Dashboard | live | blocker | Posts → Delete بيقول "Post deleted" والبوست موجود؛ Verify بيقول "verified" ومفيش تغيير؛ Users بيعرض اللي اتحمّلوا في المتصفح بس؛ Dashboard أرقام ثابتة؛ خطأ `u is not defined`. `profiles.status` (active/suspended) + RLS، RPCs أدمن (`admin_set_role`، `admin_verify_profile`، `admin_suspend`، `admin_delete_post`) كلها بتكتب `admin_actions`، وقوايم بصفحات وبحث |
| A-02 | الأدمن يدير الـ ticker والـ sponsors وإعدادات الموقع | Admin → Ticker / Sponsors / Settings / Design | live | major | "Ticker item added!" والجدول 8→8. الجداول والـ policies موجودة. الـ adapter يقرا ويكتب `ticker_items` و`sponsored_suppliers` (بفورم إضافة) و`settings`، ويطبّق الإعدادات على الكل عند الفتح |
| A-03 | الأدمن يراجع التوثيق والشهادات والبلاغات والدفع | Admin → 🛡️ Review | both | major | 🟡 **اتعمل جزء في المرحلة 1:** طابورين جداد: 💬 بلاغات الرسايل و🚩 البوستات المبلّغ عنها (Remove بملاحظة للكاتب وإشعار للمبلّغين، أو Dismiss). **فاضل:** طابور الأعضاء المبلّغ عنهم، "Decided" بـ undo، بحث وفلاتر، والعربي. — **الأصل:** شغال في الـ live. ناقص: طابور "Content reports" (من S-09)، تاب "Decided" بـ undo، بحث وفلاتر (limit 100)، الشاشة كلها إنجليزي في العربي، والديمو فاضي فحضرتك مش شايف الـ workflow (seed بند أو اتنين لكل طابور) |
| A-04 | العضو العادي مايشوفش مدخل الأدمن | آخر السايد بار → "⚙️ Admin" | live | minor | (جديد، لقاه التحقق — هو `J-COMMUNITY-50`) ظاهر لأي عضو جديد. الضغط عليه بيقول "Admin access required" فمفيش حاجة بتتسرّب، بس اللينك ظاهر للكل. يتخبّى لو `profiles.role` مش admin أو moderator |

### 3.7 عام

| # | الشغلانة | فين | demo/live | الشدة | أصغر تصليح كامل |
|---|---|---|---|---|---|
| X-01 | ألاقي الإعدادات والمساعدة وسياسة الخصوصية والشروط | المنيو، الشريط، الفوتر | both | blocker | مفيش أي صفحة منهم، ومنصة بتجمع CVs ومستندات شركات ودفع. قانون 151/2020 وonboarding Paymob/Fawry بيطلبوهم. "Settings" و"Help & legal" في `SB_NAV` بنفس شكل Saved: باسورد/إيميل (`auth.updateUser`)، إشعارات، "Open to work"، مسح الحساب بـ RPC بيعمل anonymise ويسيب الشركات. Privacy وTerms بالعربي والإنجليزي ولينك من التسجيل ("I agree") ومن الدفع. **النص من محامي أو منك** (يشمل S-17) |
| X-02 | الوظايف والتدريب والأدمن بالعربي | Apply modal، Admin Review، الكورسات، toasts الـ adapter | both | major | جوّه الجروبات اتحل مع `ee2b5f8` (`groups_test` ar 64 / 64). الباقي للـ `i18n.js`، وtoasts الـ adapter تعدّي على دالة الترجمة، و`title_ar`/`description_ar` للكورسات |

**العدد (المفتوح بعد المرحلة 1):** S: 3 / 16 / 7 · B: 6 / 10 / 5 · G: 0 / 4 / 10 · J: 2 / 4 / 1 · T: 1 / 0 / 0 · A: 1 / 2 / 1 · X: 1 / 1 / 0 → **14 blocker / 37 major / 24 minor = 75** (S-17 مدموج في X-01). البنود اللي اتقفلت (S-01، S-04، B-05، G-02، G-03) فضلت في الجداول للرجوع ليها ومش محسوبة. قبل المرحلة 1: 21 / 35 / 20 = 76.

**المفتاح بتاع الحالة:** ✅ اتقفل (رحلاته عدّت ديمو وlive والمراجع المستقل وافق) · 🟡 اتصلّح كله أو جزء منه بس لسه مفتوح (مكتوب إيه اللي فاضل، أو مستني تحقق مستقل) · 🔴 لسه مفتوح ومهم. البنود اللي من غير علامة ما اتلمستش في المرحلة 1.

---

## 4. ترتيب البناء المقترح

المقاس: **S** = يوم أو اتنين (adapter أغلبه)، **M** = 3–5 أيام (migration + adapter + e2e)، **L** = أسبوع لاتنين أو أكتر (جداول وواجهة وموافقة). كل بند يقفل بنفس القواعد: migration بـ GRANTs وsweep "none"، e2e **بيدوس على الزرار الحقيقي** ويشيّك الداتابيز، parity، وقياس السرعة قبل وبعد، وتسليم `drugbox.html` لو الواجهة اتغيرت.

### المرحلة 1 — نوقف الكدب والتسريب (blockers صغيرة، adapter أغلبها) — **اتنفّذت 14–15 أكتوبر**

| الترتيب | البنود | المقاس | ليه الأول | بعد التنفيذ (15 أكتوبر، `d0b2cfe`) |
|---|---|---|---|---|
| 1 | S-03 رسالة جديدة بتروح لشخص غلط | S | ثغرة خصوصية | 🔴 **لسه مفتوح** — اتصلّح للأسامي المختلفة والمكررة، بس عضوين بنفس الاسم ونفس الشركة بيطلعوا اختيارين متطابقين والرسالة بتروح للتاني |
| 2 | S-02 الـ like / reactions (+ migration الـ kind) | S | أكتر زرار بيتداس | 🟡 **الداتا اتقفلت، البند لسه مفتوح (major)** — قايمة التفاعلات على العربي 390px |
| 3 | S-01 حفظ البروفايل | S | بيقول "اتحفظ" وما حفظش | ✅ **اتقفل** |
| 4 | محتوى الديمو في الـ live: G-02، G-03 (+ G-04، S-19 معاهم) | M | Join وهمي، وجروب غلط بصلاحية Admin | ✅ **G-02 وG-03 اتقفلوا** · 🟡 G-04 اتصلّح بس رحلته واقفة عند G-07 · 🟡 S-19 فاضل الـ ticker وصور Home و"12K+" في صفحة الدخول |
| 5 | B-06 الماركت (+ صفوف My Listings الديمو من B-07) | M | أرقام مضلِّلة جنب منتج مدفوع | 🟡 Browse وMy Listings بقوا نضاف؛ فاضل My Intents الجاهزة والـ ticker (B-06)، وEdit/Pause/Renew (B-07) |
| 6 | G-01 — نخبّي Listings في الـ live فوراً (S)، وبعدين نبنيه | S ثم M | زرار ظاهر ومش بيشتغل | 🟡 **الإخفاء اتعمل** (نزل لـ major)؛ البناء لسه |
| 7 | S-04 دعوات الاتصال | M | الشبكة هي قلب المنتج | ✅ **اتقفل** |
| 8 | B-05 مراسلة الشركة (fallback للـ owner) | S | المشتري مش عارف يوصل للمورّد | ✅ **اتقفل** |

**اتعمل كمان في نفس الشغل (مش من بنود المرحلة 1):** S-07 الحفظ، S-10 قايمة الاتصالات، S-11 Follow، S-15 التسجيل بالشركة، S-26 البحث في الرسايل، وأجزاء من S-09 (بلاغ البوست، Block/Mute/Report في الرسايل) وS-20 (الإشعار بيفتح البوست) وA-03 (طابورين بلاغات). رحلاتهم عدّت ديمو وlive، بس فاضلين مفتوحين لحد ما يتحقق منهم مستقل (S-15 كمان فيه مشكلة الـ headline الافتراضي).

**migrations المرحلة 1:** 0028 التفاعلات وبلاغات البوستات، 0029 البروفايل والتسجيل، 0030 الشبكة والمتابعة، 0031 أمان الرسايل، 0032 مراسلة الشركة، 0033 `market_stats()`. كلهم بـ GRANTs صريحة و`notify pgrst`، والـ sweep "none" في الست فحوص، و`migration_check` OK.

**الفحوص على الـ build المدموج:** 14 سويت SQL كلهم عدّوا (منهم `messages_safety` 25/25، `network_followups` 34/34، `company_contact` 22/22، `launch_readiness` 30/30)، الديمو والـ legacy 28/28، e2e على الـ stack المشترك 23/23 (منهم الجديد `p1_no_sample_content` 18/18)، السرعة 12.7 ms مقابل 12.6 ms للمرجع القديم (مفيش بطء)، والـ build بيطلع نفس الـ sha مرتين، وPARITY OK بعد تحديث المرجع.

**فاضل من المرحلة 1 قبل ما نقول إنها خلصت:** S-03 (الأسامي المتطابقة)، الـ ticker وصور Home (S-19)، My Intents (B-06)، وأرقام Jobs الثابتة (J-05، مش من المرحلة 1 بس من نفس النوع "كدب"). دول كلهم S تقريباً.

### المرحلة 2 — اللي محتاجه أي حد عشان يستخدم المنتج بجد (باقي الـ blockers)

| الترتيب | البنود | المقاس | ملاحظة |
|---|---|---|---|
| 9 | X-01 الإعدادات + الخصوصية + الشروط + مسح الحساب | M (+ النص القانوني) | شرط للـ onboarding بتاع Paymob/Fawry |
| 10 | S-05 نسيت الباسورد | M | تغيير واجهة صغير — موافقة |
| 11 | S-06 الصورة والغلاف (bucket `avatars`) | M | |
| 12 | B-01 import الدليل من القوايم العامة | M (+ تجميع الداتا) | محتاج مصدر الداتا منك أو من EDA/الغرفة |
| 13 | B-02 كتالوج المنتجات | L | |
| 14 | B-03 المواقع والشهادات | L | هو اللي بيوصّل الشركة لـ Level 2/3 |
| 15 | B-04 فريق الشركة (دعوات وأدوار وrouting) | L | بعده B-05 بيوصل للشخص الصح |
| 16 | B-07 إدارة الإعلانات | M | |
| 17 | J-03 "Post My Profile" + CV | M | |
| 18 | J-01 قايمة المتقدمين وحالاتهم | M | |
| 19 | A-01 أدوات الأدمن الحقيقية + suspend + سجل | L | محتاجها قبل ما يبقى فيه مستخدمين حقيقيين |
| 20 | T-01 التدريب | L | أو قرار مؤقت: نسمّيه "كتالوج" ونأجّل |

### المرحلة 3 — الـ majors (بالترتيب ده تقريباً)

| الترتيب | البنود | المقاس |
|---|---|---|
| 21 | S-20 + G-05 الإشعار يفتح الحاجة | S |
| 22 | S-07 + J-06 Saved كامل (بوستات، وظايف، إعلانات) | M |
| 23 | S-15 التسجيل بالشركة والتخصص، S-16 تأكيد الإيميل | S + S |
| 24 | S-18 البحث الحقيقي، B-10 بحث الماركت | M + M |
| 25 | B-15 VIP في معالج الإنشاء، B-14 مدفوعاتي والفواتير | S + M |
| 26 | B-16 مزايا VIP (نشيل اللي مش متبني فوراً، S؛ بناؤها L) | S / L |
| 27 | S-09 البلاغات والـ Block، A-03 طابور البلاغات وDecided | M + M |
| 28 | S-14 البروفايل المهني، S-10 قايمة الاتصالات، S-11 Follow | M + M + M |
| 29 | S-12 تعديل البوست، S-13 الردود والكومنتات، S-08 Repost/Copy link | S + M + M |
| 30 | J-02 طلباتي، J-04 تفاصيل الوظيفة، J-05 أرقام وبحث الوظايف | M + M + S |
| 31 | B-08 RFQ عن طريق محرك الصفقات، B-09 إعلانات موثوقة | M + M |
| 32 | B-11 مستندات الـ compliance، B-12 ورق الصفقات، B-17 التقييمات | M + L + M |
| 33 | B-13 إشعارات برّه الأبلكيشن (إيميل) | M |
| 34 | A-02 ticker/sponsors/settings، G-06 الـ Danger Zone والأرشفة | S + S |
| 35 | S-21 الـ routing وزرار Back (parity جديد) | M |
| 36 | S-22 اللينكات والـ hashtags والـ mentions | M |
| 37 | X-02 العربي المتبقي | S |

### المرحلة 4 — الـ minors

كلها S تقريباً، وممكن تتلم في دفعة أو اتنين: G-07 لـ G-15، S-23 لـ S-28، B-18 لـ B-21، J-07. اللي محتاج موافقتك فيهم: S-28 وG-14 (تغيير في الصفحة المعتمدة).

### محتاج منك

0. **مراجعة واجهة المرحلة 1 (أهم حاجة دلوقتي):** `web/reference/demo-approved.html` اتحدّث بالواجهة المدموجة عشان الـ parity، بس حضرتك لسه ماشفتهاش. افتح `/home/user/new/web/dist/drugbox.html` وشوف: قايمة التفاعلات ونافذة "Reactions"، Save و"🔖 Saved"، نافذة Report بأسباب، تابين Admin → Review الجداد (💬 بلاغات الرسايل، 🚩 البوستات المبلّغ عنها)، Location وOpen to work في Edit Profile، "Sent requests" و"My connections" و× على الاقتراحات و"✓ Following"، ✓/✓✓ وUnmute/Unblock والبحث جوه الرسايل في Messages، والأرقام الحقيقية في الشبكة والجروبات.
1. **موافقة على تغييرات الواجهة:** لينك نسيت الباسورد (S-05)، صفحة الإعدادات والقانوني (X-01)، الغلاف (S-06)، أقسام البروفايل المهني (S-14)، الـ routing (S-21)، هيدر البوست المثبّت على الموبايل (S-28)، "see more" بالعربي (G-14)، وقايمة التفاعلات على العربي 390px (S-02). (قايمة الاتصالات S-10 اتعملت في المرحلة 1 وداخلة في البند 0.)
2. **نص سياسة الخصوصية والشروط** (أو محامي).
3. **مصدر داتا الدليل** (B-01): القوايم العامة اللي نقدر نستوردها قانونياً.
4. **قرار التدريب** (T-01): نبنيه دلوقتي ولا نأجّله.
5. **قرار مزايا VIP** (B-16): نشيل اللي مش متبني من الكارت دلوقتي ولا نستنى نبنيه — **قبل** ما حد يدفع.
6. المفاتيح والوصول لخطوات الإطلاق E5 (`docs/LAUNCH.md`).
7. **قرار في الشبكة (S-29):** اللي طلبه اترفض يفضل شايف "Pending" (زي دلوقتي، عشان اللي رفض مايتحرجش) ولا يتقاله؟

---

**المصادر:** فحوص الاكتمال `scratchpad/finish/gap-social.md` و`gap-business.md` و`gap-community.md`، والـ gate `scratchpad/finish/grp-gate.md`، والتحقق `scratchpad/finish/grp-verify.md` (المسار الكامل: `/tmp/claude-0/-home-user-new/821674db-a196-55af-97b7-080b6c8aa6d4/scratchpad/`). آخر commit اتفحص عليه: `ee2b5f8`. **تحديث المرحلة 1 (15 أكتوبر 2026، `d0b2cfe`):** ملاحظات الـ workstreams `scratchpad/finish/p1-{msg,react,profile,network,compmsg,purge}.md`، الدمج والفحوص `scratchpad/finish/p1-merge.md` (الرحلات في `pmjr/` و`pmjr2/`، الـ crawler في `pmcrawl/`)، والتحقق المستقل `scratchpad/finish/p1-verify.md` (سكريبتات وصور في `scratchpad/p1v/`).
