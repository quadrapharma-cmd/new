# Data contract — demo ↔ database

Extracted automatically from the approved demo (every data list the interface reads, and every key it stores).
The live data adapter must provide exactly these shapes, so the interface runs unchanged.

| Demo data | Records | Fields | Database | Status |
|---|---|---|---|---|
| `COMMENTS` | 3 | 0, 1, 2 | comments | ✅ |
| `COMPANIES` | 3 | id, uid, name, type, logo, color, location, founded… | companies (+ company hub) | ✅ |
| `DG_PHOTOS` | 5 | pos, k, t, s | interface artwork | — |
| `ENQUIRIES` | 8 | id, uid, type, cat, flag, country, title, body… | enquiries | ✅ |
| `ENQ_CATS` | 7 | id, label | fixed list in the interface | — |
| `GROUPS` | 6 | id, emoji, name, desc, type, members, joined, color | groups, group_members | ✅ |
| `JOBS` | 6 | id, uid, title, company, location, type, seniority, salary… | jobs, job_applications, saved_jobs, job_reviews, work_references, job_lists | ✅ |
| `MK_CATS` | 7 | id, label | fixed list in the interface | — |
| `MSGS` | 3 | id, uid, threads | messages | ✅ |
| `NOTIFS` | 6 | id, uid, icon, text, ts, read, type | notifications (created by DB triggers) | ✅ |
| `POSTS` | 7 | id, uid, cat, body, likeCount, liked, commentCount, shareCount… | posts, post_media, reactions | ✅ |
| `PRODUCTS` | 8 | id, uid, name, cat, type, emoji, price, priceTiers… | products | ✅ |
| `SB_NAV` | 11 | page, color, key, badge, label | interface navigation | — |
| `SPONSORS` | 3 | id, name, banner, desc, logo, color | sponsored_suppliers | ✅ |
| `TICKER_ITEMS` | 8 | label, text | ticker_items | ✅ |
| `TRAINING` | 6 | emoji, title, desc, duration, level, enrolled | — courses, enrolments | ⏳ 0003 |
| `USERS` | 7 | id, name, initials, headline, company, country, verified, color… | profiles | ✅ |
| `_profPosts` | 1 | id, uid, cat, body, likeCount, liked, commentCount, shareCount… | derived from posts | — |
| Directory companies (dxDir) | 17 | 32 fields (slug, status, registry, licensed, sectors, certs, team…) | companies, company_members, company_routing | ✅ |
| Sites & certificates (dxHubData) | — | name, type, city, certs[expiry] | company_sites, site_certificates | ✅ |
| Compliance documents (dx_passport) | — | type, product, number, expiry, status | company_documents, verification_requests | ✅ |
| Deals (dx_deals) | 6 | id, type, title, from, to, lines, status, at, updated, events, assignee, offer | — deals, deal_events | ⏳ 0002 |
| Company listings (surplus, dossiers, group buying) | — | — | — company_listings, group_orders | ⏳ 0002 |
| Saved searches, profile insights, match scores | — | — | — saved_searches, profile_views | ⏳ 0003 |
| Theme, tour, language (dx_theme, dx_tour_done, dx_lang) | — | — | stays in the browser (per-device preference) | — |
