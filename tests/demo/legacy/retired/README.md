# Retired demo suites (kept for reference, not run)

Six of these suites were written for the **first company directory** (before the company hub replaced it). Against today's
approved demo they stop at their first step (the buttons and fields they click no longer exist — Playwright timeouts), so
they could only ever fail. They are kept here because their check lists describe features the hub still has.
`tests/run_all.py` does not run this folder.

| Suite | What it checked | Covered today by |
|---|---|---|
| `db1_test.py` | directory pre-populated, unclaimed pages, "Claim this page" with a code | `legacy/hub_a_test.py`, `legacy/hub_b_test.py`, live `tests/e2e/c1_companies_test.py` (unclaimed pages) |
| `db2_test.py` | directory tools bar, vendor status, questionnaire → approved supplier | `legacy/hub_b_test.py`, `legacy/deals_test.py`, live `tests/e2e/c3_listings_test.py` (questionnaire → AVL) |
| `dir_test.py` | sidebar "Company Directory", listing, filters | `legacy/hub_a_test.py`, `legacy/affordance_hub.py`, live `tests/e2e/c1_companies_test.py` |
| `dir2_test.py` | company names in Jobs link to the company page, separate supplier/employer ratings | `legacy/jobs_trust_test.py`, `legacy/b_jobs_trust_test.py`, live `tests/e2e/d2b_trust_test.py` |
| `multi_test.py` | several companies per person, the acting company switch | `legacy/hub_c_test.py`, live `tests/e2e/c1_companies_test.py` (my companies / acting) |
| `b1_test.py` | an early copy of the live sign-up test (needs the local stack, fixed e-mail `other@x.test`) — not a demo suite | live `tests/e2e/b1_auth_test.py` |
| `vip_test.py` | VIP strip, Sponsored marks, VIP listed first | `legacy/tiers_test.py`, live `tests/e2e/e4b_checkout_test.py` (VIP through checkout) |

Retired in the October 2026 code review (F-126). To bring one back, rewrite it against the hub (`dxHub.page(slug)`,
`#dxDir`), make it pass on `web/dist/drugbox.html`, and move it back to `tests/demo/legacy/`.
