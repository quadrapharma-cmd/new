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

## 2. Migrations
<!-- filled at the end -->

## 3. Interface changes for the owner's approval (EN + AR, 1440 + 390)
<!-- filled at the end -->

## 4. Where the trade session plugs in (offer cards and composer)
<!-- filled at the end -->

## 5. Independent verification
<!-- filled at the end -->

## 6. Suites
<!-- filled at the end -->

## 7. Open problems / waiting on the owner
<!-- filled at the end -->
