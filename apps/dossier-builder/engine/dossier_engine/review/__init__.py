"""Regulatory Reviewer — reviews a dossier the way the EDA departments (and the international assessors) do.

pack      the assessor knowledge pack (rulepacks/eda.review.v1): questions with sources, letters, clocks
evidence  text evidence from the dossier's documents (per-page) and data
checks    named data checks a question can reference (auto.kind == data)
run       the review pipeline: resolve → screening → technical → data → text → aggregate → clock → diff
storage   review_run / review_finding / review_response tables on the dossier store
letters   deficiency letter and assessment report (DOCX, PDF when LibreOffice is present)
ai        prompt and answer handling for the AI assessor (browser «sample» capability or the Anthropic SDK)
"""
