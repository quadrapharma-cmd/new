# تشغيل «منشئ الملفات» أونلاين

النسخة السحابية هي نفس الأداة، وفيها زيادة:
- **تسجيل دخول إجباري.**
- **حفظ دائم** للملفات على قرص خاص.
- **HTTPS** تلقائي.

اتجرّبت كاملة داخل الحاوية (Docker) على البنود دي:
- تسجيل الدخول.
- رفع الملفات.
- توليد خطاب بالعربي.
- تصدير CTD و eCTD 3.2.2 و eCTD 4.0.
- التحقق من المخرجات.

## اختار طريقة واحدة

### (أ) سيرفر خاص (VPS) — **الأنسب لملفات الشركة**
أي سيرفر Linux عليه Docker، زي Hetzner أو DigitalOcean أو AWS Lightsail أو سيرفر الشركة.

**المواصفات:**
- 2 vCPU و 4 جيجا رام، وده كفاية لفريق صغير.
- قرص على حسب حجم ملفاتكم، وابدأ من 50 جيجا.

1. **الدومين:** اعمل سجل DNS نوعه **A** لاسم زي `dossier.your-company.com`، وخلّيه يشاور على IP السيرفر.
2. **نزّل المشروع على السيرفر:**
   ```bash
   git clone <رابط المستودع> && cd new/apps/dossier-builder/deploy
   cp .env.example .env && nano .env
   ```
3. **املا ملف `.env`:**
   - `DOMAIN`
   - `DB_ADMIN_USER`
   - `DB_ADMIN_PASSWORD`: 10 حروف على الأقل.
4. **شغّل:**
   ```bash
   docker compose up -d --build
   ```
   - Caddy بيطلع شهادة HTTPS من Let's Encrypt لوحده.
   - افتح `https://dossier.your-company.com` وسجّل دخول.
5. **بعد أول دخول:** امسح `DB_ADMIN_PASSWORD` من ملف `.env`، لأن الحساب اتحفظ خلاص.

### (ب) منصة جاهزة (Render / Railway / Fly.io)
1. اعمل خدمة **Web Service** من نوع **Docker**.
2. **Dockerfile path:** `apps/dossier-builder/deploy/Dockerfile`.
3. **Build context:** جذر المستودع.
4. ضيف **قرص دائم** (Persistent Disk / Volume) على المسار **`/data`**. ده إجباري؛ من غيره الملفات هتضيع مع كل إعادة تشغيل.
5. **متغيرات البيئة:**
   - `DB_ADMIN_USER`
   - `DB_ADMIN_PASSWORD`
   - `DB_COOKIE_SECURE=1`: المنصة بتدّي HTTPS.
   - `PORT`: بتحدده المنصة.

## إضافة مستخدمين

```bash
docker compose exec app python apps/dossier-builder/tools/adduser.py /data <الاسم> --role user
```
البرنامج هيطلب كلمة السر مرتين. نفس الأمر بيغيّر كلمة سر مستخدم موجود.

## الأمان (اللي اتعمل)

**الدخول وكلمات السر:**
- مفيش أي صفحة أو ملف بيتفتح من غير تسجيل دخول.
- كلمات السر متخزنة مشفّرة (scrypt)، والملف بصلاحيات `0600`.
- **5 محاولات غلط ← قفل 15 دقيقة** لنفس المستخدم ونفس الجهاز.

**الجلسات:**
- كوكي موقّع، `HttpOnly`، `SameSite=Strict`، و `Secure` على HTTPS.
- الجلسة بتنتهي بعد 12 ساعة.
- حماية من CSRF: أي عملية تعديل لازم تيجي من واجهة الأداة نفسها.

**المتصفح:**
- هيدرز `CSP` و `X-Frame-Options: DENY` و `HSTS`.

**السيرفر:**
- الحاوية شغالة بمستخدم عادي (مش root).
- كل عمليات الدخول بتتسجل في سجل النشاط.

## نسخ احتياطي (مهم)
كل البيانات في مكان واحد: الـ volume `/data`. جواه قاعدة البيانات والملفات والتصديرات وسجل التسلسلات.

```bash
docker run --rm -v deploy_dossier-data:/data -v $PWD:/b alpine tar czf /b/dossier-$(date +%F).tgz -C /data .
```
اعمله يومي، واحتفظ بنسخة برّا السيرفر. وجرّب الاسترجاع مرة على الأقل.

## ملاحظات
- **الحجم:** الصورة أكتر من جيجا، لأن فيها LibreOffice. (مفيش OCR: الملف اللي من غير نص بيترفض وقت الرفع.)
- **الشبكة:** لو شبكتكم بتعيد توقيع HTTPS (proxy شركات):
  ```bash
  docker build --secret id=extra_ca,src=<شهادة الـ CA> ...
  ```
- **التحديث:**
  ```bash
  git pull && docker compose up -d --build
  ```
  البيانات مش بتتلمس.
