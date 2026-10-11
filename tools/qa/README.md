# tools/qa — dead-end crawler

`deadend_crawler.py` answers one question for every page: **does every control a person can click lead somewhere?**
The feature tests check that code keeps working; this checks that nothing on screen is a dead end — a button that does
nothing, a card that opens an empty panel or someone else's detail, a "coming soon" toast.

```
python3 tools/qa/deadend_crawler.py                                   # the demo: web/dist/drugbox.html, EN+AR × 1440+390
python3 tools/qa/deadend_crawler.py --target http://localhost:54321/  # the live app (local stack), fresh account per configuration
python3 tools/qa/deadend_crawler.py --pages groups --langs en --widths 1440 --out /tmp/crawl   # one page, one configuration
```

Output in `--out` (default `qa-crawl/`): `crawl.md` (readable, by page, dead ends first) and `crawl.json` (every click,
every skipped element, settings, timing). Exit code 1 when a JavaScript error was seen or a dead end is not in the
allow-list, 0 when clean, 2 when the crawler itself could not run.

## What it does

1. Signs in (demo account; live: signs up a brand-new account per configuration through the sign-up form).
2. Crawls the start page and its navigation; every page a click leads to is queued at once and crawled in parallel
   (`--workers`, default 4), one level deeper too (e.g. a company page inside the directory).
3. On each page it lists every visible control — links, buttons, `[onclick]`, `role=button/tab/…`, and cards made
   clickable from script (outermost `cursor:pointer`) — and clicks them **one at a time from a fresh state**: the whole
   visible page must equal the snapshot taken after a clean sign-in; if not, it closes dialogs and re-opens the page, and
   if that is not enough it reloads in a new browser context and signs in again.
4. Controls revealed by a click (dialog contents, menus, tab panels) are clicked too, one level deep, by replaying the
   opening click each time.
5. Each click is classified from what changed: navigated, dialog (with its content measured), changed in place, toast,
   clipboard/share/print/new window/download/file picker, network requests and their status (live), JS errors.

## Outcomes

Dead ends (fail): `no_effect`, `toast_only`, `placeholder_toast` ("coming soon"…), `placeholder_href` (`#p-need`),
`dialog_empty`, `dialog_thin` (a large panel with almost nothing in it, or a card's detail that shows nothing the card did
not already show — e.g. a group that opens to its header only), `confirm_no_effect`, `alert_only`, `wrong_item`,
`network_error`, `js_error`, and for repeated cards: `family_partial` (only some respond), `family_wrong_detail` (cards open
another item's detail, e.g. "only the first 2 of 9 cards open their own group"), `family_same_detail` (every card opens
the same template).

Warnings: `self_only` (only the button changed), `stored_only`, `request_only`, `needs_input` (does nothing while its text
box is empty — the crawler does not type), `unsaved_change` (live: changed on screen, nothing sent), `click_failed`,
`console_error`.

Fine: `navigated`, `dialog`, `dialog_confirm`, `changed`, `focused_input`, `closed`, `validation`, `already_active`,
`disabled`, `new_window`, `clipboard`, `share`, `print`, `download`, `file_picker`, `native_dialog`, `left_app`.

## Limits — never silent

Every element not clicked is listed under "Skipped" with its reason.

| option | default | meaning |
|---|---|---|
| `--family-sample` | 6 | repeated elements of one family (same tag/class/handler shape; cards: same look): first 3, middle, last 2 |
| `--max-per-page` | 70 | elements per page after sampling, in page order |
| `--reveal-cap` / `--max-depth2` | 8 / 25 | revealed elements per dialog/menu / per page |
| `--max-views` | 30 | pages per configuration (two navigation steps deep) |
| `--view-timeout` | 240 s | per page and configuration |
| `--secondary-*` | 3 / 40 / 10 | lighter sampling for the 2nd…4th configuration (AR, phone); `--full` crawls them as deeply |

Navigation (top bar, side menu, the phone menu) is never sampled or capped. Sign-out and external links are never clicked.

The demo runs offline (all network requests are blocked) with a seeded `Math.random`, and Playwright's clock skips the
fixed waits (splash hand-over, sign-in loader, numbers counting up) — the crawl is deterministic and takes about
15 minutes for the four configurations on 4 CPUs. In the live app actions persist in the database (the account is new and
used only by the crawler); after a reload the crawler re-learns the resting state.

## Allow-list (`deadend_allow.json`)

Starts empty: every dead end fails the run until it is fixed or the owner approves it. To approve one, copy its id from
`crawl.md` (`page:kind:hash`):

```json
{"allow": [{"id": "admin:placeholder_toast:1a2b3c4d5e", "why": "sponsor form is phase 2", "approved_by": "owner", "date": "2026-10-11"}]}
```

## Files

- `deadend_crawler.py` — the crawler (the only Drugbox-specific part is the `APP` dictionary at the top).
- `qa_lib.js` — injected into the page before the app loads: lists controls, takes DOM snapshots and measures dialogs.
  It replaces only the calls that would leave the page (`window.open`, print, share, clipboard) with recorders, and
  records storage writes, so "a toast after the link was copied" is not mistaken for "a toast and nothing else".
