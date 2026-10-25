# Area report — W-trade (structured trade offers)

Branch `claude/w-trade` (from `claude/integ` f7dc703) · migrations 0071–0075 · journeys J-BUSINESS-W01…W18 (`tests/journeys/business_trade.py`)
· design `docs/areas/w-trade-design.md` · running log `docs/areas/w-trade-progress.md`. Final numbers: last section.

## Items
| Id | What | Status | Journey (demo EN/AR 1440, EN/AR 390 · live) | Where |
|---|---|---|---|---|
| W-01 | «متوفر» stock lines: name AR+EN, strength, form, qty+unit, expiry, source+country, pack, fridge; governorate, delivery, urgent; credit (آجل), currency, MOQ, COA | Closed | W01 | `listing_lines` (0072), Supply form "Available stock", items editor (`listing_lines_replace`) |
| W-02 | Price as number / discount % / «اطلب سعر»; «اسأل عن السعر» tied to the listing | Closed | W02 | `price_mode`, `discount_pct`; `listing_price_ask` (0074): company↔company → quote request in the deals engine, else a message + `price_ask` notice + inquiry |
| W-03 | Matching «عندي / محتاج» (item key, file, agency) + notice to both sides in the app and by e-mail + saved search | Closed (e-mail sending waits for the owner's provider keys) | W03 | `trade_matches`, `trade_match_run`, `trade_match` notices → `notification_outbox` (0059 path; `notify-dispatch` needs EMAIL_* keys); saved searches on canonical words (0073); My Listings → Matches |
| W-04 | Registration-file listing with structured fields + stage checklist | Closed | W04 | `attrs` of `file_sale` / `file_wanted` (0072); License form; "File details" |
| W-05 | Toll capacity with required fields (forms, packs, min batch, lead time, free months, licence, registration contract, GMP with date) | Closed | W05 | `trade_missing` (database refuses a toll without them); CMO form |
| W-06 | Arabic ⇄ English synonyms for medicines and forms, Arabic-Indic digits, market words (no Franco, no «باتش») | Closed | W06 | `trade_terms` + `trade_norm/tokens/key` (0071, generated from `tools/trade/terms.tsv`; browser copy `web/src/trade_terms.js`; parity `tools/trade/norm_parity.py`); `market_search` on canonical words; moderators extend the dictionary (`trade_term_add`) |
| W-07 | Limited renew instead of re-posting + refuse/merge duplicates + paid «ميّز إعلانك» | Closed | W07 | `listing_renew` once every 7 days (moves up: `bumped_at`); duplicate fingerprint refused → "Renew that one"; Boost/Featured through the existing checkout with the listing preselected |
| W-09 | «محجوز / اتباع» locks the listing, records the sale, asks for a rating | Closed | W09 | `listing_close`, `trade_outcomes`, confirm + rate both ways, `trade_record`; a confirmed sale between companies is a closed, rated deal (track record) |
| W-13 | Ten quick templates (post_kind + attrs + item key) | Closed | W13 | `products.kind` / `attrs` / `item_key`; pills + "Or start from a trade template" on Create Listing; the Home composer's "🛒 Product" already opens Create Listing (social area, S-23) |
| W-14 | «الزق قايمتك»: a pasted WhatsApp list becomes items | Closed | W14 | parser in `trade.js` (headers, bullets, Arabic-Indic digits, expiry incl. ISO, discount, fridge, source, fractions; contact lines dropped), review before adding |
| W-15 | Agency both ways: agency listing with governorate map, distributor listing, distributor profile, agency deal | Closed | W15 | `agency` / `distributor` kinds; new deals kind `agency` (requested → talks → agreed); `listing_respond`; `distributor_profiles` on the company page |
| W-18 | File trust: notification number in a private box, «مستندات اتشافت», price increase submitted/approved, disclaimer EN+AR, checklist before «اتفقنا» | Closed | W18 | `listing_private` + shares + `listing_private_get`; Admin → Review → Trade documents (`listing_docs_review`); checklist enforced on dossier `agree` (`deal_events_agree_guard`) |

## Owner's scope rules — how they are kept
- B2B only: no listing kind, field or label sells to pharmacies, the public or patients; "public price" appears only as a file's reference price.
- A company posts AS the company only when Drugbox verified it — enforced by the database on every way to go live (insert, resume, company change, renew of a closed listing); individuals post as themselves ("Post as").
- Prices, roles and statuses: the server keeps kind → side/category, expiry, keys, published / bumped / closed / documents-checked columns; reserved / sold only through `listing_close`; boosts priced from `payment_products` (unchanged).

## Hooks left for the trust session (W-10, W-16, W-25)
- Every trade card (demo and live): `data-trade-kind`, `data-trade-poster="company|person"`, `data-trade-company` (slug), and a call to `window.dxTradeBadge(card, row)` when defined (`trade.js` → `decorate`).
- Before publishing: `await window.dxTradeGate(kind, { asCompany })` when defined — `false` stops it (`trade.js` → `gate`).
- `trade_record(user)` (0074): confirmed sales/purchases and stars, for a trade profile.

## Shared code touched (merge notes)
- `notification_to_outbox()` (0059) redefined in 0073 with three more kinds (`trade_match`, `price_ask`, `trade_outcome`).
- `deal_flow()` / `deal_next_status()` redefined in 0075 (adds `agency`, `talk`); `deals_type_check` adds `agency`. `web/src/deals.js`: agency flow, `talk`, checklist hook before dossier `agree`.
- `products_market_derive()` and `listing_quote()` / `listing_renew()` / `my_listings()` / `market_search()` (business 0054/0065) redefined; `market_search` gains `p_kind` (the 5-argument form is dropped).
- The products saved-search trigger of 0043 is replaced by `trade_saved_search_run` (canonical words OR the old substring match; same notice shape).
- `web/src/moderation.js`: "Trade documents" queue. `web/build/build.py`: `trade_terms.js`, `trade.js`, `trade.css`.
- Tests changed: `marketplace.rls.sql` (companies verified — owner's rule; renewing the same week refused, then a week later), `launch_readiness.rls.sql` (re-applies 0071–0075), `tools/scale/seed_100k.sql` (stock lists with items, computed keys), `tools/scale/timings.py` (trade queries).
- Adapter: one block `/* ===== AREA w-trade … ===== */` at the end of `web/src/live/adapter.js`.

## Interface changes for the owner's approval (EN + AR, 390 + 1440)
- Create Listing: "Or start from a trade template" (10 templates) on step 1; new pills: File wanted, Company for sale, Agency, Distributor, Factory wanted.
- Supply form: "What are you offering?" (Available stock / Raw materials); Items (stock lines) with "＋ Add another item" and "📋 Paste your list"; governorate, delivery; price as Price / Discount % / Ask for price + currency; credit days (آجل); Urgent; "Post as". The approved price and MOQ are not required for stock (each item has its quantity; no price → «اطلب سعر»).
- Demand form: strength, dosage form, needed by, governorate. CMO form: dosage forms (required), pack types, minimum batch, lead time, free months, licensed, registration contract, GMP with issuer and date. License form: registration type, stage + steps done, decision, notification validity, public price/pack, price increase, asking price, commission, sales, buyer conditions, factory, validity, private box, documents for Drugbox, disclaimer.
- New forms (approved wizard markup): File wanted, Company for sale, Agency (governorate tap-map by region), Distributor, Factory wanted.
- Cards: the kind tag, items summary, "N items", discount ("28% off" / «خصم 28%»), "Ask for price", «محجوز», «📑 مستندات اتشافت» (with disclaimer), governorate / fridge / urgent / credit chips, the answer button (Request the file, Apply for the agency, Offer your products, Request capacity, Offer capacity, Offer your file), "File details".
- My Listings: "🔒 Reserved / sold" in ···, "📦 Edit items" in Edit, "🎯 Matches for your listings", "🤝 Sales and purchases" (confirm and rate), renew once a week → "⭐ Feature this listing".
- Deals: "Agency request" (Open talks / Agree terms); the checklist window before agreeing a file deal.
- Admin → Review: "📑 Trade documents". Company page (Distribution sector): "Distributor profile" (+ edit for the team).

## Waiting on the owner
- E-mail provider keys (EMAIL_PROVIDER / EMAIL_API_KEY / EMAIL_FROM / NOTIFY_DISPATCH_SECRET) and the scheduler: match / price-request / sale notices are queued in `notification_outbox` and sent when they exist.
- The free-renewal period (set to once every 7 days, from the study's 16-hour median repost interval) and the pair cap on recorded sales (3 per 30 days) are policy numbers he may change.
- The medicine dictionary (`tools/trade/terms.tsv`) holds 70+ common names in Arabic and English; Drugbox moderators extend it (`trade_term_add`) — a fuller list is a content task.

## Known limits
- The governorate "map" is a tap-grid grouped by region, not a drawn map of Egypt.
- Group composers (Groups) keep their own deal-room listings (0061); the templates are on Create Listing.
- A deal between two companies is needed for the deals-engine paths (quote request, file / agency / toll deals); members without a company page reach the lister by message (as before).
