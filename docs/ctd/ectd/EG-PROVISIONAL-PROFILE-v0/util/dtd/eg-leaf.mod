<!--
PROVISIONAL - NOT ISSUED BY THE EGYPTIAN DRUG AUTHORITY (EDA).
In the eCTD File Organisation: "util/dtd/eg-leaf.mod" (file name: SPEC p.7 l.50-51).
Part of the "EG provisional profile v0" for ICH eCTD v3.2.2, built 2026-11-06.
Derived from the EU Module 1 eCTD util package v3.1 (eu-leaf.mod v1.4, EMA, June 2024) and adapted to the
element and attribute names of the EDA draft "EG Module 1 eCTD Specification" v1.0/2026 and the EDA draft
"Technical Guidance for eCTD Submissions in Egypt" v1.0/2026. EDA has not published an EG DTD; replace this
file with the EDA-issued one as soon as it exists. Provenance of every name and value: README.md and vocab/*.yaml
(EG-DRAFT = stated by EDA draft, EU-DERIVED = taken from EU, ASSUMPTION = our choice).
-->

<!-- The EG leaf is identical to the ICH eCTD leaf (SPEC p.7 l.52-53: 'reference is made to Table 6-8 of the ICH eCTD
     Specification'). Declarations below are copied unchanged from eu-leaf.mod v1.4, which is based on ich-ectd-3-2.dtd. -->


<!-- ============================================================= -->
<!ELEMENT node-extension (title, (leaf | node-extension)+)>
<!ATTLIST node-extension
	ID ID #IMPLIED
	xml:lang CDATA #IMPLIED
>

<!-- ============================================================= -->
<!ENTITY % show-list " (new | replace | embed | other | none) ">
<!ENTITY % actuate-list " (onLoad | onRequest | other | none) ">
<!ENTITY % operation-list " (new | append | replace | delete) ">
<!ENTITY % leaf-element " (title, link-text?) ">
<!ENTITY % leaf-att '
 ID                  ID                #REQUIRED
 application-version CDATA             #IMPLIED
 version             CDATA             #IMPLIED
 font-library        CDATA             #IMPLIED
 operation           %operation-list;  #REQUIRED
 modified-file       CDATA             #IMPLIED
 checksum            CDATA             #REQUIRED
 checksum-type       CDATA             #REQUIRED
 keywords            CDATA             #IMPLIED
 xmlns:xlink         CDATA             #FIXED    "http://www.w3c.org/1999/xlink"
 xlink:type          CDATA             #FIXED    "simple"
 xlink:role          CDATA             #IMPLIED
 xlink:href          CDATA             #IMPLIED
 xlink:show          %show-list;       #IMPLIED
 xlink:actuate       %actuate-list;    #IMPLIED
 xml:lang            CDATA             #IMPLIED
 '>

<!ELEMENT leaf %leaf-element;>
<!ATTLIST leaf
	%leaf-att; 
>
<!ELEMENT title (#PCDATA)>
<!ELEMENT link-text (#PCDATA | xref)*>

<!ELEMENT xref EMPTY>
<!ATTLIST xref
	ID ID #REQUIRED
	xmlns:xlink CDATA #FIXED "http://www.w3c.org/1999/xlink"
	xlink:type CDATA #FIXED "simple"
	xlink:role CDATA #IMPLIED
	xlink:title CDATA #REQUIRED
	xlink:href CDATA #REQUIRED
	xlink:show %show-list; #IMPLIED
	xlink:actuate %actuate-list; #IMPLIED
>

<!-- +++ -->
