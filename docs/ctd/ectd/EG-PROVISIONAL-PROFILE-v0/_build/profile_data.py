# -*- coding: utf-8 -*-
"""Single source of the controlled vocabularies of the EG provisional profile v0.

PROVISIONAL - not issued by EDA. Every value carries a provenance tag:
  EG-DRAFT    stated in an EDA draft (cite page)
  EU-DERIVED  taken from EU M1 v3.1.1 / EU DTD 3.1 / EU VC 8.2 (cite)
  ASSUMPTION  our choice where both are silent (reason given)

Short cites
  SPEC = EDA draft "EG Module 1 eCTD Specification" v1.0/2026 (79 p.), page / margin line
  TG   = EDA draft "Technical Guidance for eCTD Submissions in Egypt" v1.0/2026 (75 p.), PDF page / margin line
  HPG  = EDA draft "EG Human Pharmaceutical Module 1 Submission Guidance" v1/2026 (68 p.), PDF page / margin line
  EU   = EU Module 1 eCTD Specification v3.1.1 / EU util 3.1 (eu-envelope.mod, eu-regional.dtd)
  VC   = EU Region eCTD Validation Criteria v8.2 (June 2025)
"""

# ----------------------------------------------------------------------------------------------------------
# submission/@type  (TG Annex 6 "EG Submission Type", PDF pp. 59-71)
# groups: P = "EG Submission Types for Pharmaceuticals" (pp. 59-63)
#         BI = "General EG Submission Types for Biologics and Innovative Products" (pp. 64-65)
#         I = "EG Submission Types for Innovative Products" (pp. 66-68)
#         B = "EG Submission Types for Biologicals" (pp. 69-71)
# variation: True -> submission/@mode is required (SPEC p. 15; TG p. 27 l. 722-724)
# ----------------------------------------------------------------------------------------------------------
SUBMISSION_TYPES = [
    # value, label (Annex 6 "Submission Title"), groups, variation, page(s), provenance, note
    ("maa", "Marketing Authorisation Application", "P", False, "TG p.59; SPEC p.14, 22, 24", "EG-DRAFT", ""),
    ("var-pac-n", "Variation PAC-N (notification)", "P", True, "TG p.59", "EG-DRAFT", ""),
    ("var-pac-b", "Variation PAC-B", "P", True, "TG p.60; TG p.23 Table 3", "EG-DRAFT", ""),
    ("var-pac-a", "Variation PAC-A (annual)", "P", True, "TG p.60", "EG-DRAFT", ""),
    ("var-pac-ii", "Variation PAC-II (major)", "P", True, "TG p.60 (token column)", "EG-DRAFT",
     "Decision D-02: lower case. Also printed 'var-pac-II' (TG p.17 Table 1, p.23 Table 3) and 'Var PAC-II' (SPEC p.23-25 examples) - XML is case-sensitive, only the Annex 6 token is kept."),
    ("renewal", "Renewal", "P,BI", False, "TG p.61, p.64; TG p.37 l.1030", "EG-DRAFT", ""),
    ("asmf", "Active Substance Master File", "P", False, "TG p.61", "EG-DRAFT", ""),
    ("cep", "Certificate of suitability (EDQM only)", "P", False, "TG p.61", "EG-DRAFT", ""),
    ("none", "none (reformat / baseline only)", "P,BI", False, "TG p.61, p.64; SPEC p.25 Table 3", "EG-DRAFT",
     "Only with submission-unit 'reformat' (TG p.74; TG p.25 l.655-656)."),
    ("preass", "Pre-assessment", "P", False, "TG p.61", "EG-DRAFT", ""),
    ("pacstab", "Post MA Commitments (Stability Studies)", "P,BI", False, "TG p.62, p.64", "EG-DRAFT", ""),
    ("paccadc", "Post MA Commitments (CADC analysis)", "P,BI", False, "TG p.62, p.64", "EG-DRAFT", ""),
    ("paci", "Post MA Commitments (Inspection)", "P,BI", False, "TG p.62, p.65", "EG-DRAFT", ""),
    ("pacqr", "Post MA Commitments (Quality requirements)", "P,BI", False, "TG p.62, p.65", "EG-DRAFT", ""),
    ("5yr", "Fifth Year Report", "P", False, "TG p.62", "EG-DRAFT", ""),
    ("appeal", "Appeals", "P", False, "TG p.63", "EG-DRAFT", ""),
    ("preappinq", "Preliminary Approval Inquiry", "P", False, "TG p.63", "EG-DRAFT", ""),
    ("pmf", "Plasma Master File", "BI", False, "TG p.65 (printed 'PMF')", "EG-DRAFT",
     "Decision D-03: printed upper case 'PMF'; lower-cased to follow the lower-case token convention of every other Annex 6 value and EU 'pmf' (eu-envelope.mod)."),
    ("withdrawal", "Withdrawal (of the marketing authorisation entirely)", "P,BI", False,
     "TG p.65; TG p.38 l.1064; SPEC p.26 l.291-294", "EG-DRAFT",
     "Decision D-04: Annex 6 lists it only for Biologics/Innovative; SPEC p.26 and TG 4.6 present it as general, so it is also allowed for Pharmaceuticals. SPEC p.26 Table 5 prints 'Withdrawal' (capital)."),
    ("maa-inn", "MAA for an innovative product", "I", False, "TG p.66", "EG-DRAFT", ""),
    ("ipv-admc", "Innovative product variation - Administrative changes", "I", True, "TG p.66", "EG-DRAFT", ""),
    ("ipv-admlc", "Innovative product variation - Administrative product labelling information changes", "I", True,
     "TG p.66", "EG-DRAFT", "Abbreviation printed 'IPV-ADMIC'; token column 'ipv-admlc' kept."),
    ("ipv-tlc", "Innovative product variation - therapeutic labelling information changes", "I", True, "TG p.66", "EG-DRAFT", ""),
    ("ipv-pu", "Innovative product variation - pack update", "I", True, "TG p.66", "EG-DRAFT", ""),
    ("ipv-safeffc", "Innovative product variation - safety and efficacy labelling changes", "I", True, "TG p.67", "EG-DRAFT", ""),
    ("imv-majvar", "Innovative medicinal products variation - Major variation", "I", True, "TG p.67", "EG-DRAFT", ""),
    ("imv-minvar", "Innovative medicinal products variation - Minor variation", "I", True, "TG p.67", "EG-DRAFT", ""),
    ("imv-not", "Innovative medicinal products variation - Notifications", "I", True, "TG p.67", "EG-DRAFT", ""),
    ("ibv-majqualc", "Innovative biological products variation - Major quality changes", "I", True, "TG p.67", "EG-DRAFT", ""),
    ("ibv-modqualc", "Innovative biological products variation - Moderate quality changes", "I", True, "TG p.67", "EG-DRAFT", ""),
    ("ibv-minqualc", "Innovative biological products variation - Minor quality changes", "I", True, "TG p.68", "EG-DRAFT", ""),
    ("ibv-qcnoimp", "Innovative biological products variation - Quality changes with no impact", "I", True, "TG p.68", "EG-DRAFT", ""),
    ("maa-nt", "MAA - Normal Track", "B", False, "TG p.69", "EG-DRAFT", ""),
    ("maa-ft", "MAA - Fast Track", "B", False, "TG p.69", "EG-DRAFT", ""),
    ("maa-sb", "MAA - Second Brand", "B", False, "TG p.69", "EG-DRAFT", ""),
    ("maa-rl1", "MAA - Reliance level 1", "B", False, "TG p.69", "EG-DRAFT", ""),
    ("maa-rl2", "MAA - Reliance level 2", "B", False, "TG p.69", "EG-DRAFT", ""),
    ("maa-bios", "MAA - Biosimilar", "B", False, "TG p.69", "EG-DRAFT", ""),
    ("np-modqualc", "Normal pathway - Moderate quality changes", "B", True, "TG p.70", "EG-DRAFT", ""),
    ("np-pilc", "Normal pathway - Product labelling information changes", "B", True, "TG p.70", "EG-DRAFT", ""),
    ("np-majqualc", "Normal pathway - Major quality changes", "B", True, "TG p.70", "EG-DRAFT", ""),
    ("np-safeffc", "Normal pathway - Safety and efficacy changes", "B", True, "TG p.70", "EG-DRAFT", ""),
    ("np-admpilc", "Normal pathway - Administrative product labelling information changes", "B", True, "TG p.70", "EG-DRAFT", ""),
    ("np-packup", "Normal pathway - pack update", "B", True, "TG p.70", "EG-DRAFT", ""),
    ("np-adminc", "Normal pathway - Administrative changes", "B", True, "TG p.71", "EG-DRAFT", ""),
    ("rp-majcq", "Reliance pathway - Major quality changes", "B", True, "TG p.71", "EG-DRAFT", ""),
    ("rp-modqc", "Reliance pathway - Moderate quality changes", "B", True, "TG p.71", "EG-DRAFT", ""),
    ("rl-pilc", "Reliance pathway - product labelling information changes", "B", True, "TG p.71", "EG-DRAFT",
     "Prefix printed 'rl-' (not 'rp-' like the two rows above); kept as printed."),
    ("not-minqc", "Notification - Minor quality changes", "B", True, "TG p.71", "EG-DRAFT", ""),
    ("not-qcnoimp", "Notification - quality changes with no impact", "B", True, "TG p.71", "EG-DRAFT", ""),
]
SUBMISSION_TYPES_EXCLUDED = [
    ("var-type1a, var-type1ain, var-type1b, var-type2, var-nat, extension, rup, psur, psusa, rmp, pam-*, pass107n, pass107q, "
     "referral-*, annual-reassessment, usr, clin-data-pub-rp, clin-data-pub-fv, paed-*, article-58, notification-61-3, "
     "transfer-ma, lifting-suspension, article-18",
     "EU eu-envelope.mod (DTD 3.1) submission/@type",
     "EU-only regulatory activities (EU variation regulation, PSUSA, referrals, paediatric articles, EMA procedures); "
     "EDA publishes its own list in TG Annex 6 and none of these is in it."),
]
GROUP_LABELS = {"P": "Pharmaceuticals (TG pp.59-63)", "BI": "Biologics and Innovative Products - general (TG pp.64-65)",
                "I": "Innovative Products (TG pp.66-68)", "B": "Biologicals (TG pp.69-71)"}

SUBMISSION_UNITS = [
    ("initial", "Initial submission to start any regulatory activity", "TG p.73; SPEC p.24 l.269-273", "EG-DRAFT", ""),
    ("validation-response", "Rectifying submission in response to content validation issues", "TG p.73; SPEC p.24 Table 1", "EG-DRAFT", ""),
    ("response", "Response to questions / outstanding issues; also the consolidation sequence after withdrawal or rejection of a single regulatory activity",
     "TG p.73; TG p.39 l.1073-1074; SPEC p.25 l.283-287", "EG-DRAFT",
     "SPEC p.25 Table 4 prints 'responses' and SPEC p.25 l.285 'Response' - both typos of this token (decision D-05)."),
    ("additional-info", "Other additional information (e.g. missing files) when validation-response or response is not suitable",
     "TG p.73; TG p.10 l.209-211; SPEC p.22", "EG-DRAFT", ""),
    ("corrigendum", "Correction of information after the regulatory activity has concluded; only after case-by-case agreement with EDA",
     "TG p.73; TG p.10 l.212-214", "EG-DRAFT", "TG p.10 l.212 calls it a 'submission type' (EU HTG remnant); Annex 6 lists it as a unit."),
    ("reformat", "Baseline: reformatting of an existing application into eCTD, no content change, not reviewed; always with submission type 'none'",
     "TG p.74; SPEC p.25 l.279-280", "EG-DRAFT", "TG p.23 l.606 says 'The submission type reformat' - wrong, reformat is a unit."),
    ("re-examination", "Request for re-examination of an authority opinion (MAA, type II variation)", "TG p.74", "EG-DRAFT", ""),
]
SUBMISSION_UNITS_EXCLUDED = [
    ("closing", "EU eu-envelope.mod", "EU centralised-procedure final documents; not in TG Annex 6."),
    ("consolidating", "EU eu-envelope.mod", "EG uses 'response' for consolidation sequences (TG p.39 l.1074; TG p.73; SPEC p.25 l.285)."),
]

SUBMISSION_MODES = [
    ("single", "A Single Regulatory Activity", "SPEC p.8 l.79, p.15; TG p.72", "EG-DRAFT", ""),
    ("grouping", "A Grouped Activity", "SPEC p.8 l.79, p.15; TG p.72", "EG-DRAFT",
     "Meaning differs: Human Pharmaceuticals = several variations, one product; Biological and Innovative = also one or several variations for several products (SPEC p.15; TG p.72). 'grouped' in TG p.17 l.430 read as this token."),
    ("parallel-single", "Parallel Assessment Single RA (imported products, evaluated together with the country of origin)",
     "SPEC p.8 l.79, p.15; TG p.72 ('Parallel Single')", "EG-DRAFT", "Decision D-06: hyphenated token from SPEC p.8; TG prints a title with a space."),
    ("parallel-grouping", "Parallel Assessment Grouped RA", "SPEC p.8 l.79 (p.15 prints 'parallel  grouping'); TG p.72 ('Parallel Grouping')",
     "EG-DRAFT", "Definition identical to parallel-single in both drafts (SPEC p.15)."),
]
SUBMISSION_MODES_EXCLUDED = [("worksharing", "EU eu-envelope.mod", "EU worksharing procedure; no EG equivalent in either draft.")]

# registration/@type: SPEC p.18 example token 'local'; labels SPEC p.18 / TG p.28 l.754-756; categories HPG pp.9-12 table and
# section headings (HPG p.12 l.189, p.15 l.285, p.17 l.388, p.20 l.504, p.24 l.635). The CV itself is unpublished (TG p.28 l.756).
REGISTRATION_TYPES = [
    ("local", "Locally Manufactured Products", "SPEC p.18 (example 'local'); HPG p.9 table, p.12 l.189", "EG-DRAFT",
     "Token printed in SPEC; label from HPG."),
    ("toll", "Toll Products", "HPG p.10 table, p.17 l.388", "ASSUMPTION", "Label EG-DRAFT (HPG); token is our choice."),
    ("f-toll", "F-Toll Products", "HPG p.9-10 table, p.15 l.285", "ASSUMPTION",
     "Label EG-DRAFT (HPG); 'F-' is never expanded in the draft; token is our choice."),
    ("under-license", "Under License Products", "HPG p.11 table, p.20 l.504", "ASSUMPTION", "Label EG-DRAFT (HPG); token is our choice."),
    ("imported-finished", "Imported (Finished) Products", "SPEC p.18 ('Imported Finished'); TG p.28 l.755; HPG p.11 table, p.24 l.635 ('Imported')",
     "ASSUMPTION", "Label EG-DRAFT; token is our choice."),
    ("imported-bulk", "Imported Bulk Products", "SPEC p.18; TG p.28 l.755; HPG p.11 table, p.24 l.635", "ASSUMPTION",
     "Label EG-DRAFT; token is our choice."),
]
# marketing/@type: SPEC p.19 example 'local' + "e.g. Local or Tender and Export"; TG p.28 l.757-759; HPG p.52 "Local/Tender/Export/Hospital use"
MARKETING_TYPES = [
    ("local", "Local market", "SPEC p.19 (example 'local'); TG p.28 l.758; HPG p.52", "EG-DRAFT", ""),
    ("tender", "Tender", "SPEC p.19; TG p.28 l.758; HPG p.52", "ASSUMPTION",
     "Decision D-07: 'Tender and Export' read as two values (HPG p.52 lists them separately); token is our choice."),
    ("export", "Export", "SPEC p.19; TG p.28 l.758; HPG p.52", "ASSUMPTION", "See 'tender'."),
    ("hospital", "Hospital use", "HPG p.52 (pack-type list 'Local/Tender/Export/Hospital use')", "ASSUMPTION",
     "Only evidence is a pack-type list in a variation form; included so a hospital-only pack is not rejected; drop if EDA's CV lacks it."),
]

PI_DOC_TYPES = [
    ("spc", "Summary of Product Characteristics", "SPEC App. 2.3 p.78", "EG-DRAFT", "Required by EDA (SPEC p.58 row 130)."),
    ("pl", "Package Leaflet", "SPEC App. 2.3 p.78", "EG-DRAFT", "Required by EDA (SPEC p.58 row 130)."),
    ("interpack", "Outer and immediate labelling submitted as one file", "SPEC App. 2.3 footnote p.78", "EG-DRAFT",
     "The footnote '*' is attached to no row; meaning taken from the footnote text."),
    ("outer", "Outer packaging (labelling)", "SPEC p.11 l.171 (file name 'outer-tablet10mg.pdf'); EU App. 2.3", "EU-DERIVED",
     "Used in an EG file-name example; value list from EU."),
    ("impack", "Immediate packaging (labelling)", "EU App. 2.3; eu-regional.dtd pi-doc/@type", "EU-DERIVED",
     "Needed when outer and immediate labelling are separate files (counterpart of 'interpack')."),
    ("combined", "Combined product information (SmPC + labelling + PL in one file)", "SPEC p.27 (App. 1.2 example); SPEC p.11 l.172-173; TG p.19 l.471",
     "EG-DRAFT", ""),
    ("other", "Other product information", "TG p.19 l.473 (example type=\"other\"); EU App. 2.3", "EG-DRAFT", "Not in SPEC App. 2.3."),
]
PI_DOC_TYPES_EXCLUDED = [("annex2", "EU App. 2.3", "Annex II of an EU centralised marketing authorisation; no EG equivalent.")]

LANGUAGES = [("ar", "Arabic", "SPEC App. 2.2 p.78", "EG-DRAFT", ""), ("en", "English", "SPEC App. 2.2 p.78", "EG-DRAFT", "")]
COUNTRIES = [("eg", "Egypt", "SPEC p.14 (envelope/@country), App. 2.1 p.78 (ISO-3166-1-alpha-2)", "EG-DRAFT", "")]
AGENCIES = [("EG-EDA", "Egyptian Drug Authority", "SPEC p.18, App. 2.4 p.78 l.336-337", "EG-DRAFT",
             "Decision D-01: TG p.27 l.743 says 'EDA'; SPEC (the XML specification) and the EU CC-ACRONYM pattern give EG-EDA.")]
