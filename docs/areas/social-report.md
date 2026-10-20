# Area social & account — report (branch `claude/area-social`)

Migrations **0040–0049** (this area only). Live code: `web/src/live/social.js` (+ a delimited "AREA social" block in `adapter.js`).
Demo layers: `web/src/soc_legal.js`, `soc_account.js`, `soc_feed.js`, `soc_profile.js`, `soc_nav.js`, `soc_safety.js`, `social.css`.
Progress log: `docs/areas/social-progress.md`.

## Gap status

| Gap | Status | Notes |
|---|---|---|
| S-05 forgot / reset / change password | done | neutral "forgot" answer; reset link once; change needs the current password (5 wrong in 15 min lock it, server-side, 0040/0047). **Launch setting:** Supabase "Secure password change" on (LAUNCH.md) — without it a session alone can change the password through the Auth API |
| S-06 photo / cover | done | `avatars` bucket (5 MB, JPEG/PNG/WebP, own folder), shrink in the browser, exact own-folder address enforced (0042/0047) |
| X-01 legal + Settings + delete + export | done (legal text = **DRAFT, waiting on the owner/lawyer**) | Privacy Policy + Terms EN/AR (law 151/2020, `[TO CONFIRM]` marks), linked from sign-up and the side menu footer; Settings: e-mail, password, language, notification e-mails + digest, privacy (who-viewed, phone to connections), blocked members, download my data (v2), delete my account (password + DELETE; payments/invoices kept 5 years in `private.billing_archive`; tombstone "Deleted member") |
| S-07, S-10, S-11, S-26 | verified | independent check PASS (save post, my connections + remove, follow, search in messages) |
| S-08 repost / send | done | `reposts` (0041), "X reposted" in Home, Undo, Send in a message |
| S-09 rest | done | report person / comment (reasons, once), Admin → Review → Reported members (suspend with reason ± remove posts, dismiss; reporters told; `moderation_log`), suspension refuses writes **and edits** (0044/0047), block from profile covers message/connect/follow/comment/reply/react/repost/mention/endorse, blocked never in search, pickers or suggestions (server-side, 0043/0048) |
| S-12 edit + marker | done | `edited_at` by the database |
| S-13 replies + comment likes | done | one level, `comment_reactions` (generic per comment id — the community area wires group comments to it), like count fixed (0045), the comment author is notified (0049) |
| S-14 experience / education / skills / languages | done | validated lists (0042), endorsements |
| S-16 sign-up confirmation (Resend) | done locally; **waiting on the owner** for the Resend account / domain (Auth SMTP — LAUNCH.md) | Resend button on the sign-up form |
| S-18 search | done | `search_all` + `find_people` (pg_trgm, definer with the policies' rules — 2–6 ms at 100k), top bar (↑/↓, Enter, grouped, empty state), Ctrl+K (New post, Settings, live results), Network "find people" with specialty + country |
| S-20 notifications open their item | done | reaction/comment/reply/mention/repost/comment like → post; request/accepted/follow/endorse → profile; message → thread; saved search → Marketplace; plus `message` notices (one per unread conversation, 0045) and e-mail notices (`notify-email`, Settings prefs) |
| S-21 deep links | done | `#/profile/<uuid>`, `#/post/<id>`, `#/messages/<uuid>`, `#/network`, `#/settings`, `#/tag/x`, `#/search/x`; reload, a shared link after sign-in, Back/Forward; sign-out clears it |
| S-22 links / hashtags / mentions | done | rel=noopener nofollow; tag page; mention suggestions (connections first, keyboard), notification |
| S-25 profile views + who viewed | done | `my_profile_viewers` respects Settings → "show my visits" |
| S-23 composer shortcuts | partial | Product → Create Listing, Job → Post a Job; **video / poll in a post not built** |
| S-24 chat 👤 / 📞 | done | 📞 shows a connection's own number only if they share it (`connection_phone`, 0046), else the company phone |
| S-27 Arabic | done for this area | new texts translated; leftover: user company names that contain an English dictionary word are translated by the approved i18n (e.g. "Verify Labs") — not this area's code |
| S-28 pinned header 390 | done (interface change — approval) | |
| S-29 | waiting on the owner (left as is) | |
| Saved searches (J-47) | done | `saved_searches` per member (20), alerts → notification (+ e-mail) |
| One Saved place (J-48) | done; listings partial | posts + jobs per member; **saved listings stay in this browser** (no table for listing saves yet) |

## Journeys (J-SOCIAL-01…51) — demo EN/AR 1440, EN/AR 390, live EN 1440

41 pass everywhere, 5 are live-only and pass. Remaining (all explained, none in this area's code):
- **J-SOCIAL-09** demo (appearance kept after reload): intermittent — the headless browser sometimes gives a file:// page an empty
  localStorage on reload; reproduced on the **approved reference build** too (2 of 5 runs), so it is the test harness, not the app.
- **J-SOCIAL-49** demo: sample reach numbers in the demo — "J-SOCIAL-49 sample numbers" is outside this area (brief).
- **J-SOCIAL-01 / 10 / 21** live failed only in the 4-way parallel run (other journeys' members/posts in the same database: a member
  named like a sample person, new posts between two reads). J-21's colleague was renamed; on a fresh database all three pass.

SUITES_PLACEHOLDER

## Independent verification
Two verifiers with a fresh context (not the builder): security/privacy/permissions (strongest model) and functional (EN/AR, 1440/390 touch,
two or more live accounts, database checks, REST attacks on the other person's data).
- Security found 7 real gaps — all fixed in **0047/0048** with database tests: a deleted account's old token could still post; a suspension
  only stopped new rows (edits, groups, companies were open); the 5-try password lock could be bypassed through account deletion; a
  blocked person could reply to the blocker's comment; requests/follows to a deleted member; the picture-address check could be fooled;
  the people picker filtered blocks only in the browser. Plus: data export v2, digest timing. Remaining (launch setting): Secure password change.
- Functional found 10 issues — all fixed: addresses lost on reload, 📞 never asked for the shared phone, Send cut off at 390, saved-search
  filters on a first visit, Arabic leftovers on the search page / edited time / saved-search notice, duplicate ⋯ menu on a repost card,
  mention keyboard, comment-like notice.
Verdict after fixes: all reported items re-tested by the builder (DB suites + the affected journeys). A second verifier pass was not run.

## Migrations
0040 account (settings, password check, deletion, export) · 0041 feed (edited, reposts, replies, comment likes, mentions, tags) ·
0042 profile (avatars, lists, endorsements, who viewed) · 0043 search + saved searches · 0044 moderation (member reports, suspensions,
log, block guards) · 0045 notices (messages, e-mail outbox, fixes) · 0046 connection phone · 0047 hardening · 0048 search speed + export v2 ·
0049 comment-like notice. Each ends with `notify pgrst`, explicit grants; `supabase/tests/social.rls.sql` (98 checks) and `account.rls.sql` (32);
`launch_readiness.rls.sql` re-applies 0040–0049; schema sweep six × "none"; `tools/migration_check.py` OK (46 migrations).
Note: 0040 and 0041 were corrected in place before any deploy (0040 had dropped the members-only rule of the profiles policy; 0041 was not re-runnable).

## Interface changes (for the owner's approval)
Sign-in: "Forgot password?" link and panels (forgot / check your e-mail / new password / farewell); sign-up: Terms + Privacy line, Resend.
New pages: Settings, Privacy Policy, Terms (drafts), tag page, search results (grouped), Saved (Posts / Jobs / Listings sections).
Side menu footer: Privacy · Terms links; phone side menu: language button. Own profile: Settings button, cover edit, Experience/Education/
Skills/Languages editors, endorsements, "Who viewed". Other profiles: ⋯ (Report / Block). Posts: Repost dialog and "X reposted" cards,
Send button (icon only on phones), Edit with "edited", comment Like / Reply / Report, replies, end-of-feed marker, linked #tags/@mentions,
composer previews removable, @mention suggestions. Network: "find people" box with specialty + country. Ctrl+K: New post, Settings.
Notifications: View profile kept after Accept; phone Alerts count = real unread count (was a fixed 8). Phone Marketplace: the search box
under the top bar. Pinned post header on phones (S-28). Admin → Review: "Reported members" tab.

## Shared code touched (say so at merge)
`web/src/live/adapter.js` (AREA social block: internals for social.js; notification sentences/types/data; reset of dx_* keys),
`web/src/i18n.js` (`dxI18nAdd`), `web/src/batch3.js` (palette / saved-search hooks; saved filters re-applied), `web/src/moderation.js`
(Reported members tab), `web/build/build.py` + `live.py` (new layers), `tools/local-supabase/*` (auth/mail/Resend stand-ins, notify-email
schedule), `supabase/tests/_local_supabase_stub.sql` (auth columns), `tools/scale/timings.py`, `deploy/supabase_deploy.sh` (+account-delete,
notify-email), `docs/LAUNCH.md` (e-mail, Secure password change), demo test login helpers (a remembered demo session), journeys updated
for new dialogs/phone layouts (listed in commit messages; no assertion weakened — several strengthened: J-41, J-44, J-48, J-51, J-28).

## Open problems / waiting on the owner
- Legal texts are drafts (lawyer). Resend account + verified domain; Supabase Auth SMTP + Secure password change; notify-email schedule (LAUNCH.md).
- Saved listings per member (needs a listing-saves table; Marketplace area). Video / poll posts (S-23 rest).
- i18n translates English words inside user company names (approved i18n).
- J-SOCIAL-09 demo flakiness in headless file:// storage (harness).
