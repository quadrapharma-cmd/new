# Community area (jobs, groups, training, admin) — running log

Branch `claude/area-community`, migrations 0060–0069. Report: `docs/areas/community-report.md` (at the end).

## Setup after a restart
`bash tools/local-supabase/setup-session.sh`, then the stack: `start.sh` → `start-payments.sh tools/local-supabase/payments.env.example` → `python3 tests/fixtures/make_fixtures.py`.

## Baseline (before any change, 19 Oct): demo EN 1440 8 pass, live 6 pass of J-COMMUNITY-01…50
(see the table in the report).

## Done so far
- 0060_jobs.sql: jobs.company_id / search_text (trigram) / closed_at; expired jobs closed by the read policy; saved-or-applied jobs stay readable;
  jobs_search() (one call per page, keyset); employer moves applications (status_at, interview_at, employer_note, notify the candidate);
  job_applicants(), my_applications(), my_jobs(); profiles.cv_path + can_read_document for verified companies; candidate_cv(); job_alerts + trigger.
- web/src/jobsx.js + jobsx.css (new layer): search box, filters (labels, start empty, phone toggle), Clear filters, job details window,
  My applications (Withdraw), My jobs & applicants (Edit / Close / Reopen / Delete, Shortlist / Interview / Hire / Reject / No-show),
  Post a Job extra fields (country, deadline, requirements, benefits), CV file checks, Post My Profile + Hide, Saved page Jobs tab, job alerts.
  Demo behaviour in the browser; live through window.dxJobs (adapter block, TODO).
- links.js: the old job filter block removed (moved to jobsx.js).
- Journeys strengthened: J-19 clicks Clear filters (+ phone filters toggle), J-26 rejects B with a note, J-27 uses a title no sample candidate has.

## Next
- adapter block "AREA community: jobs" (window.dxJobs), i18n strings, jobs.rls.sql, then live journeys 19–29.
