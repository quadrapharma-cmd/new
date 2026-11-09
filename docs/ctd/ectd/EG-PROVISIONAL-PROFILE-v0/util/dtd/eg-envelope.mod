<!--
PROVISIONAL - NOT ISSUED BY THE EGYPTIAN DRUG AUTHORITY (EDA).
In the eCTD File Organisation: "util/dtd/eg-envelope.mod" (file name: SPEC p.7 l.50-51).
Part of the "EG provisional profile v0" for ICH eCTD v3.2.2, built 2026-11-06.
Derived from the EU Module 1 eCTD util package v3.1 (eu-envelope.mod v3.1, EMA, June 2024) and adapted to the
element and attribute names of the EDA draft "EG Module 1 eCTD Specification" v1.0/2026 and the EDA draft
"Technical Guidance for eCTD Submissions in Egypt" v1.0/2026. EDA has not published an EG DTD; replace this
file with the EDA-issued one as soon as it exists. Provenance of every name and value: README.md and vocab/*.yaml
(EG-DRAFT = stated by EDA draft, EU-DERIVED = taken from EU, ASSUMPTION = our choice).
-->

<!-- Changes from eu-envelope.mod 3.1 (all logged in README.md):
     - element 'procedure' removed (not in SPEC App. 1.1 nor TG 3.2.2)                       decision D-12
     - elements 'registration' and 'marketing' (EMPTY, @type required) added                SPEC p.18-19, decision D-26
     - order of envelope children follows SPEC App. 1.1 table (p.14-20)                      decision D-24
     - vocabularies replaced by the EG ones (vocab/*.yaml)                                   -->

<!-- ................................................................... -->
<!ELEMENT eg-envelope (
	envelope+
)>

<!ELEMENT envelope (
	identifier,
	submission,
	submission-unit,
	applicant,
	agency,
	invented-name+,
	registration,
	marketing,
	inn*,
	sequence,
	related-sequence+,
	submission-description
)>

<!-- ................................................................... -->
<!ELEMENT identifier             ( #PCDATA )>
<!ELEMENT submission             ( number?, procedure-tracking )>
<!ELEMENT procedure-tracking     ( number+ )>
<!ELEMENT number                 ( #PCDATA )>
<!ELEMENT submission-unit        EMPTY>
<!ELEMENT applicant              ( #PCDATA )>
<!ELEMENT agency                 EMPTY>
<!ELEMENT invented-name          ( #PCDATA )>
<!ELEMENT registration           EMPTY>
<!ELEMENT marketing              EMPTY>
<!ELEMENT inn                    ( #PCDATA )>
<!ELEMENT sequence               ( #PCDATA )>
<!ELEMENT related-sequence       ( #PCDATA )>
<!ELEMENT submission-description ( #PCDATA )>

<!-- submission/@type: TG Annex 6 (vocab/submission-type.yaml); @mode: SPEC p.8 l.79 (vocab/submission-mode.yaml) -->
<!ATTLIST submission
type (maa | var-pac-n | var-pac-b | var-pac-a | var-pac-ii | renewal | asmf | cep | none | preass | pacstab | paccadc | paci | pacqr | 5yr | appeal | preappinq | pmf | withdrawal | maa-inn | ipv-admc | ipv-admlc | ipv-tlc | ipv-pu | ipv-safeffc | imv-majvar | imv-minvar | imv-not | ibv-majqualc | ibv-modqualc | ibv-minqualc | ibv-qcnoimp | maa-nt | maa-ft | maa-sb | maa-rl1 | maa-rl2 | maa-bios | np-modqualc | np-pilc | np-majqualc | np-safeffc | np-admpilc | np-packup | np-adminc | rp-majcq | rp-modqc | rl-pilc | not-minqc | not-qcnoimp) #REQUIRED
mode (single | grouping | parallel-single | parallel-grouping) #IMPLIED
>

<!-- TG Annex 6 'EG Submission Unit' (vocab/submission-unit.yaml) -->
<!ATTLIST submission-unit
type (initial | validation-response | response | additional-info | corrigendum | reformat | re-examination) #REQUIRED
>

<!-- SPEC App. 2.4 p.78 (vocab/agency-code.yaml) -->
<!ATTLIST agency
code (EG-EDA) #REQUIRED
>

<!-- SPEC p.18; values ASSUMPTION (vocab/registration-type.yaml) -->
<!ATTLIST registration
type (local | toll | f-toll | under-license | imported-finished | imported-bulk) #REQUIRED
>

<!-- SPEC p.19; values ASSUMPTION (vocab/marketing-type.yaml) -->
<!ATTLIST marketing
type (local | tender | export | hospital) #REQUIRED
>

<!-- ................................................................... -->
<!ENTITY % env-countries "(eg)">

<!-- ................................................................... -->
<!ATTLIST envelope country %env-countries; #REQUIRED >

<!-- +++ -->
