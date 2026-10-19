# Payments — setup (Paymob, Fawry, InstaPay)

| Method | Provider | Confirmation |
|---|---|---|
| Card (Visa, Mastercard, Meeza) | Paymob — Unified Checkout (Intention API) | automatic: Paymob's signed callback (HMAC-SHA512) |
| Vodafone Cash, Orange Cash, e& money, WE Pay | Paymob — mobile-wallet integration | automatic, same callback |
| Fawry (any outlet or the Fawry app) | FawryPay — PAYATFAWRY reference number | automatic: Fawry's signed server notification V2 (SHA-256) |
| InstaPay | transfer to your InstaPay address + receipt | manual: Admin → Review → Payments (InstaPay has no public merchant API; Paymob lists InstaPay as "coming soon" — switch when it is live) |

Amounts always come from `payment_products` (VAT 14% added in the database). Activation happens only in `confirm_payment`
(server-only) after the signature, the amount **and the currency** match; repeated callbacks never activate twice.

How a callback finds its order (migration 0023):
- **Paymob** — by Paymob's own order id (`obj.order.id`), which is inside the HMAC. `payments-create` stores it
  (`intention_order_id` of the intention) with the order; `merchant_order_id` is *not* signed, so it is only logged.
- **Fawry** — by `merchantRefNumber` (`DBX<id>`), which is inside Fawry's signature, and only with the Fawry reference number
  `payments-create` received for that order (migration 0024): Fawry's signed string has no separators, so the webhook also
  requires `paymentAmount` = `orderAmount` (Drugbox pays Fawry's fee; the customer pays exactly the order amount).
- Only a `pending` order paid by that provider's method is confirmed: an InstaPay order is confirmed only in Admin → Review.
  One provider transaction pays one order (unique in the database).
- If the listing or company page was deleted (or the buyer no longer manages the company) before the money arrived, the order
  is recorded as paid but **nothing is activated**: the buyer is told a refund is due and every Drugbox admin gets a
  "refund due" notification (`provider_payload.not_activated` says why). Refund it from the Paymob / Fawry dashboard.

VIP ends at `companies.vip_until`: `is_vip(company)` (also `companies?select=*,is_vip`) is false after that date, and
`expire_vip_plans()` puts `plan` back to `free` — scheduled daily by the migration when **pg_cron** is enabled
(Supabase → Database → Extensions → pg_cron, then re-run 0023), otherwise call it daily as the service role
(`POST /rest/v1/rpc/expire_vip_plans`).

## Secrets (Supabase → Edge Functions → Secrets — never in the browser)
```
supabase secrets set APP_URL=https://app.drugbox.app/ \
  ALLOWED_ORIGINS=https://app.drugbox.app,https://drugbox.app \
  PAYMOB_SECRET_KEY=egy_sk_live_… PAYMOB_PUBLIC_KEY=egy_pk_live_… PAYMOB_HMAC_SECRET=… \
  PAYMOB_CARD_INTEGRATION_ID=… PAYMOB_WALLET_INTEGRATION_ID=… \
  FAWRY_BASE=https://www.atfawry.com FAWRY_MERCHANT_CODE=… FAWRY_SECURE_KEY=… \
  INSTAPAY_ADDRESS=yourname@instapay INSTAPAY_NAME="Drugbox Egypt"
supabase functions deploy payments-create
supabase functions deploy paymob-webhook --no-verify-jwt
supabase functions deploy fawry-webhook --no-verify-jwt
```
Test first with Paymob test keys / integration IDs and Fawry staging (`FAWRY_BASE=https://atfawry.fawrystaging.com`).
`payments-create` answers browsers only from `ALLOWED_ORIGINS` (comma-separated; if unset, the origin of `APP_URL`) —
list every address the app is opened from.

## Provider dashboards
- Paymob: set the transaction **processed** callback of both integrations (card, wallet) to
  `https://<project>.supabase.co/functions/v1/paymob-webhook`; copy the HMAC secret from your profile.
- Fawry: ask Fawry to set the server notification V2 URL to `https://<project>.supabase.co/functions/v1/fawry-webhook`.

## Prices
Change prices in `payment_products` (Drugbox admins can edit). Seeded: VIP EGP 2,500/month, 25,000/year;
boost EGP 1,450 (7 days) and featured EGP 3,950 (30 days) — the demo's USD 29/79 at EGP 50; **set your real prices**.

## Local test
`tools/local-supabase/start-payments.sh <env file>` runs the functions (Deno) and a Paymob/Fawry stand-in;
`python3 tests/e2e/e4_payments_test.py` — 20 checks, signatures computed independently from the providers' formulas.
A test Paymob callback must carry the order's stored Paymob order id (`payment_orders.provider_order`) as `obj.order.id`.
Database checks: `supabase/tests/payments_storage.rls.sql`.

## Orders, invoices and VIP boosts (migration 0055)
- **Failed / expired:** a signed Paymob callback for a finished, unsuccessful payment and Fawry's EXPIRED / FAILED / CANCELED
  notification call `fail_payment` (server-only): the order becomes `failed` / `expired`, nothing is activated, the buyer is
  notified. A paid order is never turned back.
- **Duplicates:** `create_order` refuses a second pending Fawry (or InstaPay) order for the same thing by the same method — the
  first reference / transfer is still payable and is shown in My payments. A new card / wallet order supersedes the older pending
  card / wallet orders for the same thing (`expired`, `provider_payload.superseded`); if a superseded order is paid anyway, its
  callback is still honoured (the money arrived: it activates).
- **Fawry expiry:** `payments-create` stores the reference's expiry (`fawry_expires_at`) so the buyer finds it again.
- **Invoices:** every order keeps its VAT split (`net_cents` + `vat_cents` = `amount_cents`, from `payment_products`). When an order
  becomes `paid` (webhook, InstaPay review, or any correction) the database gives it the next tax-invoice number
  `DBX-INV-<year>-<000001>`. `order_invoice(order)` returns the invoice data to its buyer, the company's owners / admins and Drugbox;
  the app prints it (Print or save as PDF). Seller details come from `billing_settings` — **set Drugbox's legal name, tax
  registration number and address there** (Supabase → Table editor, or as a Drugbox admin). Egypt's ETA e-invoice / e-receipt
  submission is not connected (needs Drugbox's ETA credentials).
- **VIP included boosts:** a current VIP company has 3 Marketplace boosts per calendar month: `use_included_boost(listing, company)`
  (owner / admin of the company, own active listing; counted under a row lock in `vip_boost_uses`), `included_boosts_left(company)`.
- **Reminder:** `vip_reminders()` notifies the owner 3 days before VIP ends (daily with pg_cron, like `expire_vip_plans`).
Database checks: `supabase/tests/payments_area.rls.sql` (52 checks, including tampering through the API roles).
