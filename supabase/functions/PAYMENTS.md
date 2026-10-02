# Payments — setup (Paymob, Fawry, InstaPay)

| Method | Provider | Confirmation |
|---|---|---|
| Card (Visa, Mastercard, Meeza) | Paymob — Unified Checkout (Intention API) | automatic: Paymob's signed callback (HMAC-SHA512) |
| Vodafone Cash, Orange Cash, e& money, WE Pay | Paymob — mobile-wallet integration | automatic, same callback |
| Fawry (any outlet or the Fawry app) | FawryPay — PAYATFAWRY reference number | automatic: Fawry's signed server notification V2 (SHA-256) |
| InstaPay | transfer to your InstaPay address + receipt | manual: Admin → Review → Payments (InstaPay has no public merchant API; Paymob lists InstaPay as "coming soon" — switch when it is live) |

Amounts always come from `payment_products` (VAT 14% added in the database). Activation happens only in `confirm_payment`
(server-only) after the signature and the amount match; repeated callbacks never activate twice.

## Secrets (Supabase → Edge Functions → Secrets — never in the browser)
```
supabase secrets set APP_URL=https://app.drugbox.app/ \
  PAYMOB_SECRET_KEY=egy_sk_live_… PAYMOB_PUBLIC_KEY=egy_pk_live_… PAYMOB_HMAC_SECRET=… \
  PAYMOB_CARD_INTEGRATION_ID=… PAYMOB_WALLET_INTEGRATION_ID=… \
  FAWRY_BASE=https://www.atfawry.com FAWRY_MERCHANT_CODE=… FAWRY_SECURE_KEY=… \
  INSTAPAY_ADDRESS=yourname@instapay INSTAPAY_NAME="Drugbox Egypt"
supabase functions deploy payments-create
supabase functions deploy paymob-webhook --no-verify-jwt
supabase functions deploy fawry-webhook --no-verify-jwt
```
Test first with Paymob test keys / integration IDs and Fawry staging (`FAWRY_BASE=https://atfawry.fawrystaging.com`).

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
