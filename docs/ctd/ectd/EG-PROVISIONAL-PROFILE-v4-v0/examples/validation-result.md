# Validation result — examples/1 (fictional initial MAA, sequence 1)

> PROVISIONAL profile v0. Run on 2026-11-06 in the session container.

## 1. XML Schema (ICH eCTD4-001 / -002)

Schema: `PORP_IN000001UV.xsd` from `docs/ctd/sources/ectd/ICH_eCTD_v4.0_IG_v1.7_with_XSD.zip`
(MD5 `9676ed53f13ecb18e909046753c4a31d`), folder `ICH_eCTD_v4_SchemaFiles/multicacheschemas/` (the interaction schema
named by QA #14; it includes MCCI_MT000100UV02, MCAI_MT700201UV02, PORP_MT000001UV01 and the CMETs).

```
$ xmllint --noout --schema …/multicacheschemas/PORP_IN000001UV.xsd examples/1/submissionunit.xml
examples/1/submissionunit.xml validates          (libxml 20914)
$ python3 lxml 6.0.x  XMLSchema(...).validate(...)
True   (empty error log)
```

**Result: VALID against the ICH v4.0 schema.** Note: the schema types `codeSystem`/`root` as plain strings, so the
`EG-PLACEHOLDER` OIDs do not affect schema validity.

## 2. Package checksum (eCTD4-062)

`sha256.txt` = `c1ebe8382782103f6a1e9261ac3cf8822f4cd7367a37bd359c0893b828550882` = `sha256sum submissionunit.xml`.
Format used: 64 lower-case hex digits, no file name, no newline (the IG does not fix the byte format — ASSUMPTION).

## 3. Business rules (`examples/check_example.py`)

`python3 -I examples/check_example.py examples/1 <…>/PORP_IN000001UV.xsd` — **143 PASS / 1 FAIL**.
The single FAIL is **expected and intended**: the 13 distinct `2.16.840.1.113883.3.989.5.x.EG-PLACEHOLDER…` code
systems are not registered OIDs, so ICH rules eCTD4-008/009/031/081/083/084 would reject this message at any real
receiver. It becomes PASS only when EDA registers OIDs (README §4.1).

Negative test (copy of the example with three injected errors: language keyword removed from the English SmPC CoU, the
application form moved to folder-only heading `eg_1.2.2`, a stray unreferenced PDF): the checker reported exactly
eCTD4-062 (checksum now wrong), EG-V4-022, eCTD4-070 and eCTD4-069 as FAIL — i.e. it does catch these errors.

## 4. What was NOT checked

* ICH rules needing receiver history: eCTD4-014/015 (sequence uniqueness), -025/-026/-080 (lifecycle against earlier
  SUs), -046 (UUID collisions across submissions), -068 (keyword display-name history), -076/-078 (FC leaf references).
* ICH CoU keyword rules for the one M2–M5 CoU (`ich_3.2.p.1`) are checked only for code-system membership, not against the
  ICH CV R/O columns (the `product` keyword used is allowed as O by the CV row `ich_3.2.p.1`).
* PDF conformance (version, fonts, security) — the six PDFs are 1-page placeholders written by `tools/gen_example.py`.
* No commercial or regulator validator was available; EDA has published no v4 validation criteria.

## 5. Full checker output

```
PASS  eCTD4-059                                                            
PASS  eCTD4-060                                                            
PASS  eCTD4-062                                                            sha256.txt vs computed
PASS  eCTD4-001/002                                                        XSD PORP_IN000001UV.xsd
PASS  eCTD4-005                                                            
PASS  eCTD4-003/004                                                        
PASS  eCTD4-006/007 (EG list)                                              eg_su_initial
PASS  eCTD4-010                                                            
PASS  eCTD4-011                                                            
PASS  eCTD4-012/013                                                        1
PASS  EG-V4-002 folder = sequence                                          
PASS  eCTD4-017/018                                                        1000
PASS  eCTD4-020/021                                                        0e5f7a32-6c41-4b8e-9d13-2a7c4f6e8b01
PASS  eCTD4-022/023                                                        
PASS  eCTD4-027/076                                                        eg_1.0
PASS  eCTD4-075 (EG CoU)                                                   eg_1.0
PASS  EG-V4-022 documents allowed on heading                               eg_1.0
PASS  eCTD4-071 keyword type allowed                                       eg_1.0:cover
PASS  EG-V4-023 keyword value in EG list                                   eg_1.0:cover
PASS  eCTD4-072 one keyword per type                                       eg_1.0
PASS  eCTD4-017/018                                                        1000
PASS  eCTD4-020/021                                                        0e5f7a32-6c41-4b8e-9d13-2a7c4f6e8b02
PASS  eCTD4-022/023                                                        
PASS  eCTD4-027/076                                                        eg_1.0
PASS  eCTD4-075 (EG CoU)                                                   eg_1.0
PASS  EG-V4-022 documents allowed on heading                               eg_1.0
PASS  eCTD4-071 keyword type allowed                                       eg_1.0:tracking
PASS  EG-V4-023 keyword value in EG list                                   eg_1.0:tracking
PASS  eCTD4-072 one keyword per type                                       eg_1.0
PASS  eCTD4-017/018                                                        1000
PASS  eCTD4-020/021                                                        0e5f7a32-6c41-4b8e-9d13-2a7c4f6e8b03
PASS  eCTD4-022/023                                                        
PASS  eCTD4-027/076                                                        eg_1.2.1
PASS  eCTD4-075 (EG CoU)                                                   eg_1.2.1
PASS  EG-V4-022 documents allowed on heading                               eg_1.2.1
PASS  eCTD4-072 one keyword per type                                       eg_1.2.1
PASS  eCTD4-017/018                                                        1000
PASS  eCTD4-020/021                                                        0e5f7a32-6c41-4b8e-9d13-2a7c4f6e8b04
PASS  eCTD4-022/023                                                        
PASS  eCTD4-027/076                                                        eg_1.3.1
PASS  eCTD4-075 (EG CoU)                                                   eg_1.3.1
PASS  EG-V4-022 documents allowed on heading                               eg_1.3.1
PASS  eCTD4-071 keyword type allowed                                       eg_1.3.1:spc
PASS  EG-V4-023 keyword value in EG list                                   eg_1.3.1:spc
PASS  eCTD4-071 keyword type allowed                                       eg_1.3.1:en
PASS  EG-V4-023 keyword value in EG list                                   eg_1.3.1:en
PASS  eCTD4-071 keyword type allowed                                       eg_1.3.1:eg
PASS  EG-V4-023 keyword value in EG list                                   eg_1.3.1:eg
PASS  eCTD4-072 one keyword per type                                       eg_1.3.1
PASS  eCTD4-070 required keyword present                                   eg_1.3.1:eg document type (product information)
PASS  eCTD4-070 required keyword present                                   eg_1.3.1:eg language
PASS  eCTD4-070 required keyword present                                   eg_1.3.1:eg country
PASS  eCTD4-017/018                                                        1000
PASS  eCTD4-020/021                                                        0e5f7a32-6c41-4b8e-9d13-2a7c4f6e8b05
PASS  eCTD4-022/023                                                        
PASS  eCTD4-027/076                                                        eg_1.3.1
PASS  eCTD4-075 (EG CoU)                                                   eg_1.3.1
PASS  EG-V4-022 documents allowed on heading                               eg_1.3.1
PASS  eCTD4-071 keyword type allowed                                       eg_1.3.1:pl
PASS  EG-V4-023 keyword value in EG list                                   eg_1.3.1:pl
PASS  eCTD4-071 keyword type allowed                                       eg_1.3.1:ar
PASS  EG-V4-023 keyword value in EG list                                   eg_1.3.1:ar
PASS  eCTD4-071 keyword type allowed                                       eg_1.3.1:eg
PASS  EG-V4-023 keyword value in EG list                                   eg_1.3.1:eg
PASS  eCTD4-072 one keyword per type                                       eg_1.3.1
PASS  eCTD4-070 required keyword present                                   eg_1.3.1:eg document type (product information)
PASS  eCTD4-070 required keyword present                                   eg_1.3.1:eg language
PASS  eCTD4-070 required keyword present                                   eg_1.3.1:eg country
PASS  eCTD4-017/018                                                        1000
PASS  eCTD4-020/021                                                        0e5f7a32-6c41-4b8e-9d13-2a7c4f6e8b06
PASS  eCTD4-022/023                                                        
PASS  eCTD4-027/076                                                        ich_3.2.p.1
PASS  ICH CoU list (not checked in detail)                                 ich_3.2.p.1
PASS  eCTD4-032 keyword code defined                                       PROD001
PASS  eCTD4-020 CoU ids unique                                             
PASS  eCTD4-043..046                                                       5b0c2e57-8d0a-4f43-9a35-6f0b8e2a1c01
PASS  eCTD4-047                                                            
PASS  eCTD4-050/051                                                        m1/cover-seq1.pdf
PASS  eCTD4-064                                                            m1/cover-seq1.pdf
PASS  eCTD4-065 file name <= 64                                            m1/cover-seq1.pdf
PASS  eCTD4-067 path <= 180 (from first-level folder; +1 seq folder here)  m1/cover-seq1.pdf
PASS  eCTD4-074 characters / lower case                                    m1/cover-seq1.pdf
PASS  EG-V4-020 text@language ar|en                                        m1/cover-seq1.pdf
PASS  eCTD4-082 new document referenced by a CoU in this SU                5b0c2e57-8d0a-4f43-9a35-6f0b8e2a1c01
PASS  eCTD4-043..046                                                       5b0c2e57-8d0a-4f43-9a35-6f0b8e2a1c02
PASS  eCTD4-047                                                            
PASS  eCTD4-050/051                                                        m1/tracking.pdf
PASS  eCTD4-064                                                            m1/tracking.pdf
PASS  eCTD4-065 file name <= 64                                            m1/tracking.pdf
PASS  eCTD4-067 path <= 180 (from first-level folder; +1 seq folder here)  m1/tracking.pdf
PASS  eCTD4-074 characters / lower case                                    m1/tracking.pdf
PASS  EG-V4-020 text@language ar|en                                        m1/tracking.pdf
PASS  eCTD4-082 new document referenced by a CoU in this SU                5b0c2e57-8d0a-4f43-9a35-6f0b8e2a1c02
PASS  eCTD4-043..046                                                       5b0c2e57-8d0a-4f43-9a35-6f0b8e2a1c03
PASS  eCTD4-047                                                            
PASS  eCTD4-050/051                                                        m1/form-af.pdf
PASS  eCTD4-064                                                            m1/form-af.pdf
PASS  eCTD4-065 file name <= 64                                            m1/form-af.pdf
PASS  eCTD4-067 path <= 180 (from first-level folder; +1 seq folder here)  m1/form-af.pdf
PASS  eCTD4-074 characters / lower case                                    m1/form-af.pdf
PASS  EG-V4-020 text@language ar|en                                        m1/form-af.pdf
PASS  eCTD4-082 new document referenced by a CoU in this SU                5b0c2e57-8d0a-4f43-9a35-6f0b8e2a1c03
PASS  eCTD4-043..046                                                       5b0c2e57-8d0a-4f43-9a35-6f0b8e2a1c04
PASS  eCTD4-047                                                            
PASS  eCTD4-050/051                                                        m1/spc-en.pdf
PASS  eCTD4-064                                                            m1/spc-en.pdf
PASS  eCTD4-065 file name <= 64                                            m1/spc-en.pdf
PASS  eCTD4-067 path <= 180 (from first-level folder; +1 seq folder here)  m1/spc-en.pdf
PASS  eCTD4-074 characters / lower case                                    m1/spc-en.pdf
PASS  EG-V4-020 text@language ar|en                                        m1/spc-en.pdf
PASS  eCTD4-082 new document referenced by a CoU in this SU                5b0c2e57-8d0a-4f43-9a35-6f0b8e2a1c04
PASS  eCTD4-043..046                                                       5b0c2e57-8d0a-4f43-9a35-6f0b8e2a1c05
PASS  eCTD4-047                                                            
PASS  eCTD4-050/051                                                        m1/pl-ar.pdf
PASS  eCTD4-064                                                            m1/pl-ar.pdf
PASS  eCTD4-065 file name <= 64                                            m1/pl-ar.pdf
PASS  eCTD4-067 path <= 180 (from first-level folder; +1 seq folder here)  m1/pl-ar.pdf
PASS  eCTD4-074 characters / lower case                                    m1/pl-ar.pdf
PASS  EG-V4-020 text@language ar|en                                        m1/pl-ar.pdf
PASS  eCTD4-082 new document referenced by a CoU in this SU                5b0c2e57-8d0a-4f43-9a35-6f0b8e2a1c05
PASS  eCTD4-043..046                                                       5b0c2e57-8d0a-4f43-9a35-6f0b8e2a1c06
PASS  eCTD4-047                                                            
PASS  eCTD4-050/051                                                        m3/32-prod/description-composition.pdf
PASS  eCTD4-064                                                            m3/32-prod/description-composition.pdf
PASS  eCTD4-065 file name <= 64                                            m3/32-prod/description-composition.pdf
PASS  eCTD4-067 path <= 180 (from first-level folder; +1 seq folder here)  m3/32-prod/description-composition.pdf
PASS  eCTD4-074 characters / lower case                                    m3/32-prod/description-composition.pdf
PASS  EG-V4-020 text@language ar|en                                        m3/32-prod/description-composition.pdf
PASS  eCTD4-082 new document referenced by a CoU in this SU                5b0c2e57-8d0a-4f43-9a35-6f0b8e2a1c06
PASS  eCTD4-069 no unassociated file                                       set()
PASS  eCTD4-033/077                                                        
PASS  EG-V4-040 one submission id item (EU-IG "Submission")                
PASS  eCTD4-034..037 (EG list)                                             eg_st_maa
PASS  EG-V4-041 mode present for variation types                           eg_st_maa
PASS  EG-V4-042 at least one contact party (EU-IG "Contact Party")         
PASS  EG-V4-043 review with product name for initial MAA                   
PASS  EG-V4-044 registration + marketing type present                      
PASS  eCTD4-038                                                            
PASS  eCTD4-039..042 (EG list)                                             
PASS  EG-V4-045 recipient EG-EDA                                           
PASS  eCTD4-057 exactly one value item                                     
PASS  eCTD4-058 displayName                                                
PASS  eCTD4-084 two header OIDs present                                    2.16.840.1.113883.3.989.2.2.1.11.6 | 2.16.840.1.113883.3.989.5.x.EG-PLACEHOLDER.6.1.0
FAIL  eCTD4-008/009/031/081/083/084 registered OIDs                        13 distinct EG-PLACEHOLDER OIDs - EXPECTED FAIL until EDA registers OIDs

143 PASS / 1 FAIL
```
