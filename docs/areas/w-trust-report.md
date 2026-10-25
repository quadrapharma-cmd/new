# Area w-trust — trust, safety and groups: report

Branch `claude/w-trust` (from `claude/integ` f7dc703) · migrations **0090–0094** · running log `docs/areas/w-trust-progress.md`.
Numbers below are from runs on this branch's head on a fresh local stack (October 2026). <!-- FINAL NUMBERS: section 6 -->

## 1. Items

| Item | Status | Journeys (demo EN/AR 1440 · EN/AR 390 · live EN/AR 1440) | Where |
|---|---|---|---|
| **W-10** trade profile before the first trade post, card on the profile and when joining a group | closed | J-BUSINESS-W10; join card in J-COMMUNITY-W08 (Requests) | 0090 `trade_profiles`, `private.trade_gate` (DX410), `trade_card()`; wtrust.js |
| **W-16** a company page posts as the company only with the badge; individuals as themselves; every card says which | closed | J-BUSINESS-W16 | 0090 `posted_as` + `trade_offer_guard` on products / group_listings, `company_listings_trade_guard`; wtrust2.js chips; adapter `dxTradeAs` |
| **W-25** broker label + owner's authorisation + commission | closed | J-BUSINESS-W25 | 0090 broker columns; authorisation in `documents/listings/<uid>/`, readable by members who can read the offer (0092 `can_read_document`) |
| **W-17** sensitive posts / offers / deal-room listings held for Drugbox review (no silent deletion; the member is told) | closed | J-COMMUNITY-W17 | 0091 `private.review_rules` (EN + AR, whole words), `review_hold`, `content_holds`, `held_review_queue/decide`; Admin → Review → 🔎 Held for review |
| **W-19** trader report with evidence, right to reply, two moderators; mutual rating after a deal | closed | J-COMMUNITY-W19, J-BUSINESS-W19 | 0092 `trader_reports`, `trader_report_votes`, `deal_ratings`, `buyer_rating`; Admin → Review → ⚖️ Trader reports; deal window ★ Rate the buyer |
| **W-20** verified private phone, member since, new-account notice, history kept | closed in the app; **SMS provider waiting on the owner** | J-SOCIAL-W20; e2e `w_sms_test.py` | 0093 `member_verifications`, `phone_verify_start/confirm`, `sms_outbox` + `sms_claim/sms_done`; `supabase/functions/sms-dispatch` (Twilio / Vonage) |
| **W-08** group admin tools: rules on join, daily limit, slow mode, duplicates, invite links, review queue, post category | closed | J-COMMUNITY-W08 | 0094 groups columns, `posts_group_rules` (DX420–425), `group_rule_acceptances`, `group_publish_post`, Manage → ⏳ Pending posts |
| **W-44** moving a WhatsApp group honestly: invite link the admin shares, each member joins by themselves, partner group | closed | J-COMMUNITY-W44 | 0094 `group_invite_links`, `group_link_*`, `group_join_by_link`, `group_partner_*`; Manage → 🔗 Invite link; Admin → Review → 🤝 Partner groups |
| **SIM-01** sign-in / sign-up fields emptied on sign-out and after success | closed | J-SOCIAL-04 (strengthened: types into the form) | soc_account.js (delimited block) |

## 2. Migrations (none applied anywhere yet — the merge renumbers them)

| Migration | Content | Test |
|---|---|---|
| 0090_trade_identity | `trade_profiles` (members read, owner writes; no pharmacy role; 28 governorates incl. "Outside Egypt"); `posted_as` / `broker_for` / `broker_auth_path` / `broker_commission` on `products` and `group_listings`; `private.trade_gate()` (DX410 trade profile, DX411–416 company / broker / Drugbox rules) used by `trade_offer_guard` (products, group_listings) and `company_listings_trade_guard`; `trade_card()` | w_trust.rls.sql |
| 0091_auto_review | `private.review_rules` (EN + AR rules, whole Arabic words, letter variants folded by `private.review_norm`), `review_hold` on posts / products / group_listings (database only), restrictive read policies, `content_holds`, `held_review_queue` / `held_review_decide` (decided once, logged), held group posts tell nobody until published; `search_all` (0065 copy) leaves held posts out; `admin_actions.kind` + `held`, `trader_report`, `partner` | w_trust.rls.sql (+ a phrase table: 14 ordinary trade phrases pass, 14 sensitive ones are caught) |
| 0092_trader_reports | `trader_reports` (evidence 1–5 files, reply, two-moderator votes in `trader_report_votes`), `trader_report` / `_reply` / `_vote` / `_queue`, `my_trader_reports`; `deal_ratings` + `deal_rate_buyer`, `buyer_rating`; `trade_card` with upheld reports and buyer rating; `can_read_document` / `can_write_document` (0059/0060 + the broker authorisation + `trader-reports/`) | w_trust.rls.sql |
| 0093_member_identity | `member_verifications` (members read only "verified"), `private.phone_codes` (hash only), `phone_verify_start` / `_confirm` (rate limits, one number one account), Edit Profile with another number un-verifies; `private.sms_outbox` + `sms_claim` / `sms_done` (service role) | w_trust.rls.sql, e2e w_sms_test.py |
| 0094_group_tools | groups: `rules_required`, `daily_post_limit`, `slow_mode_minutes`, `block_duplicates`, `block_links`, `review_posts`, `require_category`, `partner_at` (Drugbox only); `posts_group_rules` (DX420–425), `group_pending` + restrictive policy, `group_publish_post`, `group_pending_posts`; `group_rule_acceptances` + guards on joins / requests; `group_invite_links` + `group_link_create / revoke / preview`, `group_join_by_link`; `group_partner_requests` + request / queue / decide | w_trust.rls.sql |

Every new table / sequence / function has explicit GRANT / REVOKE; RLS with policies everywhere; `notify pgrst` at the end; schema_sweep six × "none";
`tools/migration_check.py` OK (re-run safe). Other suites follow the new rule with a precondition (trade profile; the company verified when it posts as the
company): groups, marketplace, payments_storage, security_core, social, listings_groups (SQL) · c3, d1 (e2e) · demo groups_test; `launch_readiness`
replays 0090–0094; `privacy_names` and e2e `name_paths` list `phone_verify_confirm` (the only new profile writer: the phone column).
New function: `supabase/functions/sms-dispatch` (deploy script, local stand-in and LAUNCH updated).

## 3. Interface changes for the owner's approval (EN + AR, 1440 + 390; the demo shows every one)

- **Profile:** a trust line under the headline — «Member since …», «📱 Phone verified» (own profile: «📱 Verify my phone»), «🆕 New account» (others,
  under 30 days), «⚠️ n reports upheld by Drugbox». A **🏷 Trade profile** card at the top of the right column (role, company, governorate, sells, buys,
  offers published, rating as a buyer) with Edit / + Add on my own, «⚑ Report a trade problem» on others', «⚖️ My trade reports» on mine.
- **Windows:** Your trade profile · First, your trade profile · Verify your phone / Enter the code (demo: the code is shown — no SMS) · Report a trade
  problem · My trade reports (reply with my side and files) · The group's rules (I accept) · Join a group (from an invite link) · Ask Drugbox: partner
  group · Rate the buyer · The Drugbox badge first.
- **Marketplace → Create Listing:** a «Posting as» field (myself / a verified company / a broker — owner, commission, authorisation file); a company
  page without the badge is listed but cannot be chosen. **Offer cards** (marketplace and deal-room): «✓ Verified company» / «👤 Individual» /
  «🤝 Broker · n% commission» + the owner + «📄 Authorisation»; a held offer says «⏳ Waiting for Drugbox review». My Listings marks a held offer.
- **Home / groups:** a held post shows «⏳ Waiting for Drugbox review — only you can see this post» to its author; a group post waiting for the
  admins says so.
- **Groups → Manage:** Settings gets «Admin tools» (rules on join, posts a day, slow mode, duplicates, outside links, review first, a category);
  new tabs «⏳ Pending posts» and «🔗 Invite link» (the honest-move steps, make / copy / stop links, ask Drugbox for a partner badge); Requests rows show
  the person's trade card; group cards / header show «🤝 Drugbox partner group».
- **Messages:** a conversation with a new account (under 30 days) shows «🆕 New account — joined N days ago. Check who you trade with before you pay
  or ship.»
- **Deals:** «★ Rate the buyer» for the supplier after delivery; the buyer's average as a buyer next to the parties.
- **Admin → Review:** new queues «🔎 Held for review», «⚖️ Trader reports» (two votes), «🤝 Partner groups».
- **Company workspace:** posting surplus / a dossier asks for the badge and the trade profile first.
- **Sign-in / sign-up:** the fields are emptied after success and on sign-out (no visible change).

## 4. Where the trade session (claude/w-trade) plugs in — offer cards and composer

- **Database:** call `private.trade_gate(user, company, posted_as, broker_for, auth_path, commission)` from any new offer table (or attach
  `public.trade_offer_guard()` as a BEFORE INSERT OR UPDATE trigger if the table has `user_id, company_id, posted_as, broker_*` columns). For the
  review rules, add the table to `private.review_text()` and attach `review_hold_before` / `review_hold_after` / `review_hold_gone` (0091 shows
  the pattern) — the `review_hold` column and a restrictive read policy go with it.
- **Composer:** the «Posting as» field is `asField(type)` in `web/src/wtrust2.js` (inserted into the approved Create Listing forms); a new composer
  sets `window.__wtAs = { as: 'individual'|'company'|'broker', slug, broker_for, commission, file }` before it saves, and `window.dxTradeAs(d, row)`
  (live, `web/src/live/wtrust.js`) turns it into the row's columns (it uploads the authorisation). Call `window.dxTrustUI.needTradeProfile(go)` before
  the first offer.
- **Cards:** `window.dxTrustUI.badge(cardElement, { as, commission, broker_for, held, id })` draws the chip into the card's `.trust-bar` (or a row of
  its own under the description). Live cards with `data-live="p<id>"` (marketplace) and `[data-lid]` (deal rooms) are decorated automatically.
- **Shared files I touched** (all in delimited "AREA w-trust" blocks / one-line hooks): `web/src/live/adapter.js` (hooks block at the end; one line
  each in `insertListing`, `submitPost`, group post create, `groupCard`, deal-room listing create), `web/src/moderation.js` (`window.dxModX`
  extension point), `web/src/groups.js` (`current()` returns id / rules / role), `web/src/deals.js` (`data-dl` marker), `web/src/directory3.js`
  (badge gate before surplus / dossier), `web/src/soc_account.js` (SIM-01), `web/build/build.py` (layers), `tools/scale/timings.py`,
  `tools/local-supabase/*` (SMS stand-in), `deploy/supabase_deploy.sh` (sms-dispatch). `web/src/i18n.js` is untouched (Arabic is in `wtrust_ar.js`).

## 5. Independent verification
<!-- filled at the end -->

## 6. Suites
<!-- filled at the end -->

## 7. Open problems / waiting on the owner
<!-- filled at the end -->
