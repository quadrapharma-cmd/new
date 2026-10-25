# W-trade — one data model for structured trade offers (design)

Branch `claude/w-trade` · migrations 0071–0089 · items W-01 … W-07, W-09, W-13 … W-15, W-18 · journeys `J-BUSINESS-W01…`
Progress log: `docs/areas/w-trade-progress.md` · report: `docs/areas/w-trade-report.md`.

## Scope rules this design follows (owner, 25 Oct)
- Trade is business-to-business **before the pharmacy** (manufacturers, toll manufacturers, file/brand owners, importers/exporters,
  distributors/agents/warehouses, API/excipient/packaging/equipment suppliers, service providers). No listing kind, field or
  wording offers sales to pharmacies, to the public or to patients. New labels say «تجارة بين الشركات/المنشآت», never "Rx sale".
- Individuals post, answer and deal **as themselves**. A company page posts trade offers **as the company** only when Drugbox has
  verified it (`companies.status = 'verified'`) — checked by the database (`products_trade_guard`), not by the browser.
- No legal-review gate; no fake members; prices of paid placement come from `payment_products` (Boost 1,450 / Featured 3,950 + 14 % VAT).

## The model: `products` stays the one listing table
The marketplace already keeps listings in `products` (0001, 0054: status, expiry, company, currency, COA, views, inquiries, boost,
featured, saved, quotes through the deals engine). Every new kind of offer is a `products` row; nothing new competes with it.
`company_listings` (the company hub's surplus / dossier cards, J-BUSINESS-38/39) stays as it is — it feeds the deals engine's
`surplus` / `dossier` flows and its tests; marketplace file listings reach the same `dossier` flow (below).

### New columns on `products` (0071)
| column | what | written by |
|---|---|---|
| `kind` | the trade post kind (W-13): `stock` متوفر · `wanted` مطلوب صنف · `file_sale` ملف للبيع · `file_wanted` مطلوب ملف · `company_sale` شركة للبيع · `agency` فرصة وكالة · `distributor` موزّع بيدوّر على منتج · `toll` سعة تول · `toll_wanted` مطلوب مصنع · `materials` خامات/عبوات · and the approved forms' `equipment`, `service` | browser (checked); old rows derived from type/category |
| `attrs` | kind-specific fields (jsonb, allow-listed keys per kind, typed, length-limited — `trade_attrs_clean()`) | browser (cleaned by the server) |
| `price_mode` | `amount` (a number + currency) · `discount` (خصم % off the public price) · `ask` (اطلب سعر — no price on purpose) | browser (checked) |
| `discount_pct` | 0–95 with `price_mode = 'discount'` | browser (checked) |
| `item_key`, `roots` | normalised item key of the listing and its match roots (drug roots, `form:*`, `cat:*`) | server only (`trade_publish`, line trigger) |
| `search_text` | canonical words of name, description, lines and attrs, Arabic and English (W-06) | server only |
| `fingerprint` | md5 of the normalised content (W-07 duplicates) | server only |
| `bumped_at` | the last free renewal — the marketplace orders by it after paid placement (W-07) | server only (`listing_renew`) |
| `published_at` | first publication through `trade_publish` | server only |
| `closed_reason` | `sold` · `withdrawn` (W-09) | server only (`listing_close`) |
| `docs_checked_at`, `docs_checked_by` | Drugbox saw the file's documents (W-18) | Drugbox moderators only (`listing_docs_review`) |
`status` gains `reserved` (محجوز: still shown, with the badge; quotes and price requests closed). `active` = status in (active, reserved).

Kind → side and category (kept by the database, so every existing reader keeps working):
`stock`/`materials`/`file_sale`/`company_sale`/`agency`/`toll`/`equipment`/`service` → `type = 'supply'`;
`wanted`/`file_wanted`/`distributor`/`toll_wanted` → `type = 'demand'`. Category: stock → finished, materials → api,
toll/toll_wanted → cmo, file_* → registration, equipment, service, others → other (the tiles read category).
Expiry: stock/wanted/materials 30 days, toll/agency/distributor/company_sale/toll_wanted 90 days, file_* none (as licences before).

### `listing_lines` — one post, many items (W-01, W-14)
`id, listing_id → products, pos, name (as written), name_ar, strength, form, qty, unit, expiry (month), source
(company / factory / authority / importer), origin_country, pack_state (intact / opened / damaged / repacked), cold,
price, discount_pct, item_key, root, search_text`. At most 300 lines a listing. The browser writes only the descriptive
columns of lines of its own draft/active listings (RLS through the parent); `item_key`/`root`/`search_text` are derived by
a trigger. Read: whoever can read the listing.

### Normalisation and synonyms (W-06)
`trade_norm(text)`: lower case, Arabic letters unified (أإآٱ→ا, ة→ه, ى→ي, ؤ→و, ئ→ي), harakat and tatweel removed,
Arabic-Indic and Persian digits → 0-9, `٫`→`.`, punctuation → space, strength joined to its unit (`500 مجم`, `٥٠٠ ملجم`, `500mg` → `500mg`).
`trade_terms(term, canon, kind)`: a dictionary (dosage forms, units, market words, drug names in Arabic and English) seeded from
`tools/trade/terms.tsv` — the same file generates `web/src/trade_terms.js` for the demo and the paste parser
(`python3 tools/trade/gen_terms.py`, checked by `--check` in the suite). Moderators may add words (`trade_term_add`).
`trade_tokens(text)` → canonical tokens; `search_text` = ` original-normalised + canonical tokens `.
Not handled on purpose (owner's item): Franco-Arabic (عربي بحروف لاتيني) and «باتش» (it means a patch in this trade far more
often than a batch — it is neither mapped to batch nor to patch).
`market_search(q, …)` matches when every canonical query token begins a word of `search_text` (trigram index).

### Publishing goes through the database (`trade_publish`)
The browser inserts the listing as a **draft**, writes its lines, then calls `trade_publish(id)`. The server checks the kind's
required fields (W-05 toll: dosage forms, minimum batch, lead time, GMP with date or «لا»; W-04 file: authority and stage;
stock: at least one line with a name and quantity), recomputes keys / roots / search text / fingerprint, refuses an exact
duplicate of the same member's own open listing (W-07: error `DUPLICATE` naming it → the page offers "Renew that one"),
publishes, runs matching (W-03) and saved-search alerts. A draft of a structured kind cannot be switched to active by a plain
update (guard); "Resume" of a paused, already published listing stays a plain update.

### Matching (W-03)
Pairs: stock ↔ wanted, materials ↔ wanted, file_sale ↔ file_wanted, toll ↔ toll_wanted, agency ↔ distributor.
Two listings match when they are on opposite sides of a pair, both open, by different members not blocking each other, and
their `roots` overlap (drug roots for items and files; `form:*` for toll; `cat:*` + governorates for agency/distributor).
`trade_matches(a, b)` keeps each pair once (renewals never notify again). Each side's owner gets a `trade_match` notification
(«عرض مطابق لطلبك» / «طلب مطابق لعرضك»), at most 50 per publication, and the poster one summary. `trade_match` joins the
e-mail outbox kinds (0059 path → `notify-dispatch`; the provider waits for the owner's keys). Saved searches (0043) on the
marketplace are matched on canonical words when a listing is published. "My matches" lists `my_trade_matches()`.

### Price (W-02)
`price_mode`: amount with currency, discount %, or «اطلب سعر». "Ask for price" (`listing_price_ask(id, line, qty, note)`):
when both sides act for companies → a `quote` request in the deals engine linked to the listing (the seller answers with a
priced quote — Requests & deals); otherwise a message to the lister naming the listing and the line, a `price_ask`
notification, one inquiry counted. Never on a reserved, paused or own listing.

### Renew, duplicates, paid feature (W-07)
`listing_renew`: free once every 7 days per listing (moves it up: `bumped_at`, and extends the expiry); sooner → the page offers
«ميّز إعلانك» (Boost / Featured through the existing checkout, the listing preselected). Duplicate publication → refused, with
"Renew the one you posted" (merge).

### Sold / reserved (W-09)
`listing_close(id, 'reserved' | 'sold' | 'withdrawn' | 'reopen', buyer, note)` (owner only). Sold → closed with
`closed_reason = 'sold'` and a `trade_outcomes` row naming the buyer chosen among the members who contacted, asked for a price or
quoted on it (or nobody). The buyer is asked to confirm and rate (`trade_outcome_confirm(id, stars, note)`); the seller may rate
the buyer (`trade_outcome_rate`). When both act for companies, the confirmed sale is also recorded in the deals engine (a
`quote` deal at `delivered`, linked to the listing) so the rating counts in the company's track record (`deal_act` rate).
`trade_record(user)` gives the confirmed sales and average stars (for the trust session's trade profile).

### Registration files (W-04, W-18)
`attrs` of `file_sale` / `file_wanted`: authority, decision (قرار: number shown only in the private box), stage (checklist:
تقديم · تسعير · لجنة فنية · تحليل · إخطار · تسجيل نهائي), notification valid until, public price per pack, price increase
(none / مقدَّمة / معتمدة), asking price, commission, included in the deal (brand, dossier, studies, artwork, stock, …), buyer
conditions (own factory / toll / licensed warehouse …), sales per year in units, factory, expiry of the registration.
`listing_private(listing_id, notif_no, reg_no, doc_paths)`: the notification number and the documents, read only by the owner,
Drugbox moderators and members the owner shared it with (`listing_private_share`), through `listing_private_get`.
Drugbox checks the documents (Admin → Review → Trade documents, `listing_docs_review`) → card badge «📑 مستندات اتشافت»
with the date and the disclaimer (EN + AR: Drugbox saw the papers; the transfer needs the authority's approval).
"Request the file" on a file listing opens a `dossier` deal when both sides act for companies; the buyer's «اتفقنا» (agree)
requires the checklist (all boxes) — enforced in `deal_act` for dossier deals.

### Toll capacity (W-05)
`attrs` of `toll`: dosage forms (required), pack types, minimum batch (required), lead time (required), free months,
licence (EDA licence yes/no + number private), contract manufacturing for registration (yes/no), GMP issuer + date (required,
or «no GMP»), capacity per month. `toll_wanted` mirrors it (forms, batch, by when).

### Agency both ways (W-15)
`agency` (owner of a product/registration looks for a distributor/agent): product or category, governorates (map), exclusive,
contract years, bonus %, target, credit terms. `distributor` (a distributor looks for products): categories, governorates,
warehouses, cold chain, fleet, current agencies. Matching on categories + governorates. "Apply for the agency" → a new deals
engine kind `agency` (requested → talks → agreed, either side declines) when both act for companies; else a message.
`distributor_profiles(company_id, govs, categories, warehouses, cold_chain, fleet, note)` shows on the company page.
Governorates are the 27 of Egypt, grouped by region as a tap-grid ("map"); `all` = all Egypt.

### Hooks for the trust session (W-10, W-16, W-25)
Every trade card the demo or the live app draws carries `data-trade-kind`, `data-trade-poster="company|person"`,
`data-trade-company` (slug) and calls `window.dxTradeBadge(card, row)` when defined (badges: verified company / individual /
broker). Before the composer publishes it awaits `window.dxTradeGate(kind, {asCompany})` when defined (the trade-profile gate);
a `false` stops publishing. Both are inert when not defined.

## Interface (EN + AR, 390 and 1440 — every change is listed for the owner in the report)
The approved Create Listing stays: Step 1 (offering / seeking), the type pills, the approved forms. trade.js adds, inside the
approved markup and classes (`.field`, `.row2`, `.chip-row`, `.radio-row`): new pills for the new kinds, the stock-line fields
in the Supply form, "Add another item" and «الزق قايمتك» (paste a list → editable lines), price mode, the file and toll fields,
the agency/distributor forms (built from the approved form markup), and on cards: lines summary, expiry, source, discount,
«اسأل عن السعر», reserved / sold, documents-seen badge, matches. The demo keeps everything in the browser (`DBK.store`),
including matching (an in-app notification) — the live app keeps it in the database.
