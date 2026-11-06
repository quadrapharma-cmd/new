# -*- coding: utf-8 -*-
"""Builds the EG provisional profile v0 (PROVISIONAL - not issued by EDA) from one source.

Usage (from anywhere):
  python3 -I build_profile.py --eu-util <dir containing dtd/ and style/ of the EU M1 3.1 util package>
                              --eu-vc <EU VC v8.2 xlsx> [--out <profile dir>]
Reads: ../../EG-M1-eCTD-Specification-DRAFT-v1.0-reference.md (Appendix 2 rows), profile_data.py, rules_data.py.
Writes: vocab/*.yaml, util/dtd/*, util/style/eg-regional.xsl, folders.csv, validation-criteria.csv/.md, examples/0000/.
Deterministic: the same inputs give byte-identical outputs.
"""
import argparse, csv, hashlib, io, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import profile_data as V  # noqa: E402
import rules_data as R  # noqa: E402

DATE = "2026-11-06"
PROFILE = "EG provisional profile v0"
DTD_VERSION = "0.1"
HEADER = """PROVISIONAL - NOT ISSUED BY THE EGYPTIAN DRUG AUTHORITY (EDA).
{name}
Part of the "{profile}" for ICH eCTD v3.2.2, built {date}.
Derived from the EU Module 1 eCTD util package v3.1 ({src}, EMA, June 2024) and adapted to the
element and attribute names of the EDA draft "EG Module 1 eCTD Specification" v1.0/2026 and the EDA draft
"Technical Guidance for eCTD Submissions in Egypt" v1.0/2026. EDA has not published an EG DTD; replace this
file with the EDA-issued one as soon as it exists. Provenance of every name and value: README.md and vocab/*.yaml
(EG-DRAFT = stated by EDA draft, EU-DERIVED = taken from EU, ASSUMPTION = our choice)."""


def md5(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def write(path, text, binary=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb" if binary else "w", encoding=None if binary else "utf-8", newline=None if binary else "\n") as f:
        f.write(text)


# ------------------------------------------------------------------ Appendix 2 parsing
def parse_appendix2(ref_md):
    lines = open(ref_md, encoding="utf-8").read().split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith("### 6.2 Appendix 2"))
    rows = []
    for l in lines[start + 1:]:
        if l.startswith("Column notes"):
            break
        if not l.startswith("| ") or l.startswith("| # ") or l.startswith("|---"):
            continue
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        if len(c) < 8:
            continue
        unq = lambda s: re.findall(r"`([^`]+)`", s)
        rows.append(dict(seq=c[0], page=c[1], ctd=c[2], title=c[3], element=(unq(c[4]) or [""])[0],
                         dir=(unq(c[5]) or [""])[0].rstrip("/"), files=unq(c[6]), comment=c[7]))
    assert len(rows) == 185, len(rows)
    return rows


def build_tree(rows):
    """Return ordered list of section nodes with parent, file patterns and sub-directories."""
    nodes, last = [], None
    for r in rows:
        if r["element"]:
            last = dict(r, children=[], patterns=[], subdirs=[], parent=None)
            nodes.append(last)
        elif r["files"]:
            last["patterns"].append((r["files"], r["seq"], r["page"], r["comment"]))
        elif r["dir"]:
            if last is not None and r["dir"].startswith(last["dir"] + "/"):
                last["subdirs"].append(r)
    byctd = {n["ctd"]: n for n in nodes if n["ctd"]}
    root = nodes[0]
    for n in nodes[1:]:
        if n["ctd"] and "." in n["ctd"] and n["ctd"].rsplit(".", 1)[0] in byctd and n["ctd"].count(".") > 1:
            p = byctd[n["ctd"].rsplit(".", 1)[0]]
        else:
            p = root
        n["parent"] = p
        p["children"].append(n)
    for n in nodes:
        n["kind"] = "root" if n is root else ("parent" if n["children"] else ("pi-doc" if n["element"] == "m1-3-1-spc-label-pl" else "leaves"))
    return nodes


def proposed_fixed(n):
    """Fixed file-name component where EDA prints none: folder name without its numeric prefix (ASSUMPTION)."""
    last = n["dir"].split("/")[-1]
    return re.sub(r"^[0-9]+-", "", last)


# ------------------------------------------------------------------ vocab YAML
def yq(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def vocab_yaml(name, field, intro, rows, excluded=None, extra=None):
    out = [f"# {name} - {PROFILE} (PROVISIONAL, not issued by EDA). Built {DATE}.",
           f"# Field: {field}", "# provenance: EG-DRAFT (stated in an EDA draft) | EU-DERIVED | ASSUMPTION (reason in note)",
           "# Sources: SPEC = EG Module 1 eCTD Specification draft v1.0/2026; TG = Technical Guidance for eCTD Submissions in Egypt draft v1.0/2026;",
           "#          HPG = EG Human Pharmaceutical Module 1 Submission Guidance draft v1/2026; EU = EU M1 v3.1.1 / eu-envelope.mod 3.1.",
           f"vocabulary: {yq(name)}", f"field: {yq(field)}", "status: PROVISIONAL", f"intro: {yq(intro)}", "values:"]
    for r in rows:
        out.append(f"  - value: {yq(r['value'])}")
        for k in [k for k in r if k != "value"]:
            v = r[k]
            out.append(f"    {k}: " + ("true" if v is True else "false" if v is False else yq(v)))
    if excluded:
        out.append("excluded_values:")
        for val, src, why in excluded:
            out += [f"  - value: {yq(val)}", f"    source: {yq(src)}", f"    reason: {yq(why)}"]
    if extra:
        out += extra
    return "\n".join(out) + "\n"


def write_vocab(out):
    d = os.path.join(out, "vocab")
    st = [dict(value=v, label=l, groups=[V.GROUP_LABELS[g] for g in grp.split(",")], variation=var, provenance=p, source=s, note=n)
          for v, l, grp, var, s, p, n in V.SUBMISSION_TYPES]
    for r in st:
        r["groups"] = "; ".join(r["groups"])
    simple = lambda L: [dict(value=v, label=l, provenance=p, source=s, note=n) for v, l, s, p, n in L]
    files = {
        "submission-type.yaml": vocab_yaml("EG submission type", "envelope/submission/@type",
            "TG Annex 6 (pp.59-71) is the only EDA list. 'variation: true' means submission/@mode is required (EG-PF-E04). The CV itself is said to be 'provided on EDA's webpage' (TG p.27 l.716-717) and was not found.",
            st, V.SUBMISSION_TYPES_EXCLUDED),
        "submission-unit.yaml": vocab_yaml("EG submission unit", "envelope/submission-unit/@type", "TG Annex 6 'EG Submission Unit' pp.73-74.",
            simple(V.SUBMISSION_UNITS), V.SUBMISSION_UNITS_EXCLUDED),
        "submission-mode.yaml": vocab_yaml("EG submission mode", "envelope/submission/@mode",
            "Only for variation activities, in every sequence of the activity (SPEC p.8 l.78-80, p.15; TG p.27 l.722-724).",
            simple(V.SUBMISSION_MODES), V.SUBMISSION_MODES_EXCLUDED),
        "registration-type.yaml": vocab_yaml("EG registration type", "envelope/registration/@type",
            "Not in the EU model (EG-only field). The 'Registration Type CV' is referenced (SPEC p.18; TG p.28 l.754-756) but unpublished; labels from SPEC/TG examples and the HPG legal-documents table (pp.9-12).",
            simple(V.REGISTRATION_TYPES)),
        "marketing-type.yaml": vocab_yaml("EG marketing type", "envelope/marketing/@type",
            "Not in the EU model (EG-only field). The 'Marketing Type CV' is referenced (SPEC p.19; TG p.28 l.757-759) but unpublished.",
            simple(V.MARKETING_TYPES), [("tender-and-export", "SPEC p.19 wording 'Tender and Export'", "Alternative reading of decision D-07; not used.")]),
        "pi-doc-type.yaml": vocab_yaml("EG product-information document type", "m1-3-1-spc-label-pl/pi-doc/@type (also PIDOC file-name component)",
            "SPEC App. 2.3 lists only spc and pl but the drafts use five more tokens (decision D-16).", simple(V.PI_DOC_TYPES), V.PI_DOC_TYPES_EXCLUDED),
        "language.yaml": vocab_yaml("EG language code", "pi-doc/@xml:lang and LL folder of 1.3.1", "SPEC App. 2.2 p.78.", simple(V.LANGUAGES),
            [("bg cs da de el es et fi fr ga hr hu is it lt lv mt nl no pl pt ro sk sl sv", "EU App. 2.2", "EU official languages; not EDA languages.")]),
        "country.yaml": vocab_yaml("EG destination/country code", "envelope/@country and pi-doc/@country", "SPEC App. 2.1 p.78. No CC folders are used (decision D-08).",
            simple(V.COUNTRIES), [("EU member-state codes, common, ema, edqm, xi", "EU App. 2.1", "EU destinations; not applicable.")]),
        "agency-code.yaml": vocab_yaml("EG agency code", "envelope/agency/@code", "SPEC App. 2.4 p.78.", simple(V.AGENCIES),
            [("EDA", "TG p.27 l.743 ('This authority code is EDA for Egypt')", "Conflicts with SPEC; decision D-01 keeps EG-EDA.")]),
    }
    for fn, txt in files.items():
        write(os.path.join(d, fn), txt)
    return files


# ------------------------------------------------------------------ DTD
def comment_block(name, src):
    return "<!--\n" + HEADER.format(name=name, profile=PROFILE, date=DATE, src=src) + "\n-->\n"


def enum(values):
    return "(" + " | ".join(values) + ")"


def write_dtd(out, nodes, eu_util):
    d = os.path.join(out, "util", "dtd")
    langs = [x[0] for x in V.LANGUAGES]
    ctry = [x[0] for x in V.COUNTRIES]
    pid = [x[0] for x in V.PI_DOC_TYPES]
    # ---- eg-envelope.mod
    env = comment_block('In the eCTD File Organisation: "util/dtd/eg-envelope.mod" (file name: SPEC p.7 l.50-51).', "eu-envelope.mod v3.1")
    env += f"""
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
type {enum([x[0] for x in V.SUBMISSION_TYPES])} #REQUIRED
mode {enum([x[0] for x in V.SUBMISSION_MODES])} #IMPLIED
>

<!-- TG Annex 6 'EG Submission Unit' (vocab/submission-unit.yaml) -->
<!ATTLIST submission-unit
type {enum([x[0] for x in V.SUBMISSION_UNITS])} #REQUIRED
>

<!-- SPEC App. 2.4 p.78 (vocab/agency-code.yaml) -->
<!ATTLIST agency
code {enum([x[0] for x in V.AGENCIES])} #REQUIRED
>

<!-- SPEC p.18; values ASSUMPTION (vocab/registration-type.yaml) -->
<!ATTLIST registration
type {enum([x[0] for x in V.REGISTRATION_TYPES])} #REQUIRED
>

<!-- SPEC p.19; values ASSUMPTION (vocab/marketing-type.yaml) -->
<!ATTLIST marketing
type {enum([x[0] for x in V.MARKETING_TYPES])} #REQUIRED
>

<!-- ................................................................... -->
<!ENTITY % env-countries "{enum(ctry)}">

<!-- ................................................................... -->
<!ATTLIST envelope country %env-countries; #REQUIRED >

<!-- +++ -->
"""
    write(os.path.join(d, "eg-envelope.mod"), env)
    # ---- eg-leaf.mod: EU leaf (= ICH leaf) unchanged below the header
    eu_leaf = open(os.path.join(eu_util, "dtd", "eu-leaf.mod"), encoding="utf-8").read()
    body = eu_leaf[eu_leaf.index("-->") + 3:]
    leaf = comment_block('In the eCTD File Organisation: "util/dtd/eg-leaf.mod" (file name: SPEC p.7 l.50-51).', "eu-leaf.mod v1.4")
    leaf += ("\n<!-- The EG leaf is identical to the ICH eCTD leaf (SPEC p.7 l.52-53: 'reference is made to Table 6-8 of the ICH eCTD\n"
             "     Specification'). Declarations below are copied unchanged from eu-leaf.mod v1.4, which is based on ich-ectd-3-2.dtd. -->\n")
    leaf += body
    write(os.path.join(d, "eg-leaf.mod"), leaf)
    # ---- eg-regional.dtd
    dtd = comment_block('PUBLIC "-//EG//DTD eCTD EG Backbone PROVISIONAL ' + DTD_VERSION + '//EN" (identifier is an ASSUMPTION, not EDA)\n'
                        'In the eCTD File Organisation: "util/dtd/eg-regional.dtd" (name ASSUMPTION, decision D-09).', "eu-regional.dtd 3.1")[:-len("-->\n")]
    dtd += """
Meaning or value of the suffixes:
? : element must appear 0 or 1 time
* : element must appear 0 or more time
+ : element must appear 1 or more times
<none>: element must appear once and only once
-->

<!-- General declarations, external modules references................... -->
<!ENTITY %% countries "%s">
<!ENTITY %% languages "%s">

<!ENTITY %% leaf-node "(( leaf | node-extension )*)">

<!ENTITY %% envelope-module SYSTEM "eg-envelope.mod" >
%%envelope-module;

<!ENTITY %% leaf-module SYSTEM "eg-leaf.mod" >
%%leaf-module;

<!-- pi-doc: SPEC App. 1.2 p.27; type list decision D-16 (vocab/pi-doc-type.yaml) -->
<!ELEMENT pi-doc (
%%leaf-node;
)>
<!ATTLIST pi-doc
xml:lang %%languages; #REQUIRED
type %s #REQUIRED
country %%countries; #REQUIRED
>

<!-- Root element (SPEC p.7 l.48-49 'eg-backbone' with 'eg-envelope' and 'm1-eg'; unprefixed, decision D-20) -->
<!ELEMENT eg-backbone (
eg-envelope,
m1-eg
)>

<!ATTLIST eg-backbone
xmlns:xlink CDATA #FIXED "http://www.w3c.org/1999/xlink"
xml:lang CDATA #IMPLIED
dtd-version CDATA #FIXED "%s"
>
""" % (enum(ctry), enum(langs), enum(pid), DTD_VERSION)
    dtd += "\n<!-- m1-eg tree: element names, order and nesting from SPEC Appendix 2 (pp.28-77); parents in 1.2 hold no\n" \
           "     documents (TG Annex 5 p.55 l.1414); optionality as in eu-regional.dtd 3.1 (decision D-28). -->\n"
    for n in nodes:
        e = n["element"]
        cite = f"<!-- {n['ctd'] or '-'} {n['title'] or ''} - SPEC p.{n['page']} row {n['seq']} -->"
        if n["kind"] in ("root", "parent"):
            if e == "m1-6-environrisk":
                model = "(\n(m1-6-1-non-gmo | m1-6-2-gmo)?\n)"
            else:
                kids = [c["element"] + ("" if (n["kind"] == "root" and c["element"] == "m1-0-cover") else "?") for c in n["children"]]
                model = "(\n" + ",\n".join(kids) + "\n)"
            dtd += f"\n<!-- ................................................................... -->\n{cite}\n<!ELEMENT {e} {model}>\n"
        elif n["kind"] == "pi-doc":
            dtd += f"{cite}\n<!ELEMENT {e} (\npi-doc+\n)>\n"
        else:
            dtd += f"{cite}\n<!ELEMENT {e} %leaf-node;>\n"
    write(os.path.join(d, "eg-regional.dtd"), dtd)
    shutil.copyfile(os.path.join(eu_util, "dtd", "ich-ectd-3-2.dtd"), os.path.join(d, "ich-ectd-3-2.dtd"))


# ------------------------------------------------------------------ XSL
def xml_esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("’", "'")


def write_xsl(out, nodes, eu_util):
    def choose(field, rows):
        w = "".join(f'\n\t\t\t<xsl:when test="{field}=\'{v}\'">{xml_esc(l)}</xsl:when>' for v, l, *_ in rows)
        return f"<xsl:choose>{w}\n\t\t\t<xsl:otherwise><xsl:value-of select=\"{field}\"/></xsl:otherwise>\n\t\t</xsl:choose>"
    st = [(v, l) for v, l, *_ in V.SUBMISSION_TYPES]
    head = comment_block("EG Module 1 style sheet (name ASSUMPTION, decision D-11).", "eu-regional.xsl v3.1").replace("<!--", "<!--", 1)
    rows = []
    for n in nodes[1:]:
        depth = 0 if not n["ctd"] else n["ctd"].count(".")
        num = n["ctd"] or ""
        title = xml_esc(n["title"] or {"m1-responses": "Responses to Questions", "m1-additional-data": "Additional Data"}.get(n["element"], n["element"]))
        pad = 4 + 16 * max(depth - 1, 0)
        if n["kind"] == "parent":
            body = ""
        elif n["kind"] == "pi-doc":
            body = '\n\t\t\t\t<xsl:apply-templates select="//m1-3-1-spc-label-pl"/>'
        else:
            body = f'\n\t\t\t\t<ul type="square"><xsl:apply-templates select="//{n["element"]}/leaf | //{n["element"]}/node-extension"/></ul>'
        rows.append(f'\t\t<tr>\n\t\t\t<td valign="top" width="9%"><b>{num}</b></td>\n\t\t\t<td style="padding-left:{pad}px">'
                    f'<b>{title}</b> <small>({n["element"]})</small>{body}\n\t\t\t</td>\n\t\t</tr>')
    xsl = f"""<?xml version="1.0" encoding="UTF-8"?>
{head}<!-- Shows every EG M1 section, populated or not (SPEC p.6 l.29-31; TG p.26 l.707-709). XSLT 1.0 so that browsers can run it.
     Templates for leaf, node-extension and the text helpers are copied from eu-regional.xsl 3.1; envelope rows and the
     section table are adapted to the EG envelope and m1-eg tree. -->
<xsl:stylesheet version="1.0"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	xmlns:xlink="http://www.w3c.org/1999/xlink">

	<xsl:output method="html" encoding="UTF-8" indent="no"/>

	<xsl:template match="/">
		<html>
			<head>
				<title>EG Module 1 (PROVISIONAL profile) - DTD version <xsl:value-of select="/eg-backbone/@dtd-version"/></title>
				<style type="text/css">
					h1, h2, h3, h4 {{margin-top:3pt ; margin-bottom:0pt}}
					ul {{margin-bottom:0pt ; margin-top:0pt}}
				</style>
			</head>
			<body>
				<center>
					<h1>EG Module 1</h1>
					<small>PROVISIONAL profile - not issued by EDA - DTD version <xsl:value-of select="/eg-backbone/@dtd-version"/></small>
				</center>
				<xsl:apply-templates select="//envelope"/>
				<br/>
				<xsl:apply-templates select="//m1-eg"/>
			</body>
		</html>
	</xsl:template>

	<xsl:template match="*|@*" mode="data"><xsl:value-of select="."/></xsl:template>
	<xsl:template match="*|@*" mode="csv">
		<xsl:value-of select="."/>
		<xsl:if test="position() != last()"><xsl:text>, </xsl:text></xsl:if>
	</xsl:template>
	<xsl:template match="*|@*" mode="line">
		<xsl:value-of select="."/>
		<xsl:if test="position() != last()"><br/></xsl:if>
	</xsl:template>

	<xsl:template match="submission" mode="submission">
		{choose("@type", st)}
		<xsl:if test="@mode"> - mode: {choose("@mode", V.SUBMISSION_MODES)}</xsl:if>
		<xsl:if test="number"> - high-level number: <xsl:value-of select="number"/></xsl:if>
	</xsl:template>
	<xsl:template match="submission-unit" mode="submission-unit">
		{choose("@type", V.SUBMISSION_UNITS)}
	</xsl:template>
	<xsl:template match="registration" mode="registration">
		{choose("@type", V.REGISTRATION_TYPES)}
	</xsl:template>
	<xsl:template match="marketing" mode="marketing">
		{choose("@type", V.MARKETING_TYPES)}
	</xsl:template>
	<xsl:template match="agency" mode="agency">
		{choose("@code", V.AGENCIES)} (<xsl:value-of select="@code"/>)
	</xsl:template>
	<xsl:template match="pi-doc" mode="pidoc-type">
		{choose("@type", V.PI_DOC_TYPES)}
	</xsl:template>

	<xsl:template match="envelope">
		<center>
			<table width="90%" border="1px" frame="border" rules="groups" cellpadding="2" cellspacing="0">
				<tr><td colspan="2"><h3>Envelope for <xsl:value-of select="translate(@country,'abcdefghijklmnopqrstuvwxyz','ABCDEFGHIJKLMNOPQRSTUVWXYZ')"/></h3></td></tr>
				<tr><td width="20%" valign="top">Identifier: </td><td><xsl:value-of select="identifier"/></td></tr>
				<tr><td valign="top">Submission: </td><td><xsl:apply-templates select="submission" mode="submission"/></td></tr>
				<tr><td valign="top">Procedure Tracking Number(s): </td><td><xsl:apply-templates select="submission/procedure-tracking/number" mode="line"/></td></tr>
				<tr><td valign="top">Submission Unit: </td><td><xsl:apply-templates select="submission-unit" mode="submission-unit"/></td></tr>
				<tr><td>Applicant: </td><td><xsl:value-of select="applicant"/></td></tr>
				<tr><td>Agency: </td><td><xsl:apply-templates select="agency" mode="agency"/></td></tr>
				<tr><td>Invented Name: </td><td><xsl:apply-templates select="invented-name" mode="csv"/></td></tr>
				<tr><td>Registration Type: </td><td><xsl:apply-templates select="registration" mode="registration"/></td></tr>
				<tr><td>Marketing Type: </td><td><xsl:apply-templates select="marketing" mode="marketing"/></td></tr>
				<tr><td>INN: </td><td><xsl:apply-templates select="inn" mode="csv"/></td></tr>
				<tr><td>Sequence: </td><td><xsl:value-of select="sequence"/></td></tr>
				<tr><td>Related Sequence: </td><td><xsl:apply-templates select="related-sequence" mode="csv"/></td></tr>
				<tr><td>Submission Description: </td><td><xsl:value-of select="submission-description"/></td></tr>
			</table>
		</center>
	</xsl:template>

	<xsl:template match="leaf">
		<li>
			<a><xsl:attribute name="href"><xsl:value-of select="@xlink:href"/></xsl:attribute><xsl:value-of select="title"/></a>
			<xsl:text> </xsl:text>(<font color="red"><xsl:value-of select="@operation"/></font>)
		</li>
	</xsl:template>

	<xsl:template match="node-extension">
		<li><xsl:value-of select="title"/>
			<ul type="square"><xsl:apply-templates select="leaf | node-extension"/></ul>
		</li>
	</xsl:template>

	<xsl:template match="m1-3-1-spc-label-pl">
		<table width="100%" cellpadding="2" cellspacing="0" border="1" style="font-size: 9pt">
			<tr><th width="15%">Language</th><th width="25%">Type</th><th>Documents</th></tr>
			<xsl:for-each select="pi-doc">
				<tr>
					<td align="center"><xsl:value-of select="@xml:lang"/> / <xsl:value-of select="@country"/></td>
					<td><xsl:apply-templates select="." mode="pidoc-type"/></td>
					<td><ul type="square"><xsl:apply-templates select="leaf | node-extension"/></ul></td>
				</tr>
			</xsl:for-each>
		</table>
	</xsl:template>

	<xsl:template match="m1-eg">
		<center>
		<table width="90%" cellpadding="3" cellspacing="1" border="0">
		<tr><td colspan="2"><h2>Module 1 EG</h2></td></tr>
{chr(10).join(rows)}
		</table>
		</center>
	</xsl:template>
</xsl:stylesheet>
"""
    write(os.path.join(out, "util", "style", "eg-regional.xsl"), xsl)
    shutil.copyfile(os.path.join(eu_util, "style", "ectd-2-0.xsl"), os.path.join(out, "util", "style", "ectd-2-0.xsl"))


# ------------------------------------------------------------------ folders.csv
def write_folders(out, nodes, rows):
    cols = ["app2_seq", "spec_page", "ctd_number", "title", "element", "parent_element", "kind", "directory",
            "file_pattern", "file_pattern_provenance", "tg_annex5", "notes"]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(cols)
    kind_name = {"root": "root", "parent": "parent (no documents)", "leaves": "leaf container", "pi-doc": "pi-doc container"}
    for n in nodes:
        parent = n["parent"]["element"] if n["parent"] else ""
        a5 = "yes (TG Annex 5 pp.55-58)" if n["ctd"].startswith("1.2") else ""
        notes = n["comment"]
        if n["kind"] == "root":
            pats, prov = [""], "n/a: regional XML listed in its own row (SPEC row 2)"
        elif n["kind"] == "parent":
            pats, prov = [""], "n/a: parent holds no documents (TG p.55 l.1414)" if n["ctd"].startswith("1.2") else "n/a: parent"
        elif n["patterns"]:
            pats = [p for grp in n["patterns"] for p in grp[0]]
            prov = "EG-DRAFT (SPEC p.%s row %s)" % (n["patterns"][0][2], n["patterns"][0][1])
        elif n["kind"] == "leaves":
            pats = [f"{n['dir']}/{proposed_fixed(n)}-VAR.EXT"]
            prov = "ASSUMPTION (EDA prints no file name; EU CC-FIXED-VAR style without CC, FIXED = folder name without its number, decision D-27)"
        else:
            pats, prov = [""], ""
        if n["element"] == "m1-2-3-18-varapp":
            notes = (notes + " " if notes else "") + "HPG p.33 l.1007-1009 asks one sub-folder per variation: allowed as <dir>/<variation-slug>/ paired with a node-extension (decision D-14)."
        if n["element"] == "m1-responses":
            notes = (notes + " " if notes else "") + "No sub-folders (TG p.20 l.520-522, decision D-18); group by node-extension."
        if n["kind"] == "pi-doc":
            for sd in n["subdirs"]:
                w.writerow([sd["seq"], sd["page"], "", "", "", n["element"], "language folder", sd["dir"], "", "EG-DRAFT", "",
                            "LL = ar | en (SPEC App. 2.2). " + sd["comment"]])
        w.writerow([n["seq"], n["page"], n["ctd"], n["title"], n["element"], parent, kind_name[n["kind"]], n["dir"],
                    " | ".join(pats), prov, a5, notes])
    for r in rows:
        if r["seq"] in ("2",):
            w.writerow([r["seq"], r["page"], "", "", "", "m1-eg", "regional XML", "m1/eg", r["files"][0], "EG-DRAFT (SPEC p.29 row 2)", "", r["comment"]])
        if r["seq"] in ("180", "181", "182", "183"):
            note = r["comment"]
            if r["seq"] in ("180", "181"):
                note += " NOT USED in this profile: EG DTD files go to util/dtd (decision D-10, EG-BP-E28)."
            if r["seq"] == "182":
                note += " Holds ich-ectd-3-2.dtd, eg-regional.dtd, eg-envelope.mod, eg-leaf.mod."
            if r["seq"] == "183":
                note += " Holds ectd-2-0.xsl and eg-regional.xsl."
            w.writerow([r["seq"], r["page"], "", "", "", "", "util folder", r["dir"], "", "EG-DRAFT (SPEC row %s)" % r["seq"], "", note])
    write(os.path.join(out, "folders.csv"), buf.getvalue())


# ------------------------------------------------------------------ validation criteria
def write_vc(out, eu_vc):
    import openpyxl
    wb = openpyxl.load_workbook(eu_vc, read_only=True)
    ws = wb["eCTD Validation Criteria"]
    eu = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        n = r[0]
        if n is None or r[1] is None:
            continue
        num = str(n).strip()
        if not re.match(r"^\d+\.", num):
            continue
        eu.append(dict(num=num, cat=str(r[1]).strip(), text=" ".join(str(r[2]).split()), type=str(r[3]).strip(), lc=(r[4] or "")))
    missing = [e["num"] for e in eu if e["num"] not in R.EU_MAP]
    extra = [k for k in R.EU_MAP if k not in {e["num"] for e in eu}]
    assert not missing and not extra, (missing, extra)
    cols = ["rule_id", "category", "rule_text", "check_logic", "provenance", "source", "eu_vc_ref", "eu_vc_category", "mapping", "mapping_reason", "lifecycle_needed"]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(cols)
    stats = {"KEEP": 0, "ADAPT": 0, "DROP": 0}
    out_rows = []
    for e in eu:
        mapping, cat, text, logic, prov, src, why = R.EU_MAP[e["num"]]
        stats[mapping] += 1
        if mapping == "DROP":
            rid, cat, text = "DROPPED-EU-" + e["num"], "n/a", e["text"]
        else:
            rid = ("EG-PF-" if cat == R.PF else "EG-BP-") + e["num"]
            text = text or e["text"]
        lc = "Y" if str(e["lc"]).strip().upper().startswith("Y") else ""
        row = [rid, cat, text, logic, prov, src, "EU VC 8.2 " + e["num"], ("Pass/Fail" if e["type"] == "P/F" else "Best Practice") + " / " + e["cat"], mapping, why, lc]
        w.writerow(row)
        out_rows.append(row)
    for rid, cat, text, logic, prov, src in R.EG_RULES:
        row = [rid, cat, text, logic, prov, src, "", "", "EG-SPECIFIC", "No EU counterpart; from the EDA drafts or a decision in README.md.", ""]
        w.writerow(row)
        out_rows.append(row)
    write(os.path.join(out, "validation-criteria.csv"), buf.getvalue())
    # markdown summary
    cnt = lambda pred: sum(1 for r in out_rows if pred(r))
    md = [f"# EG provisional validation criteria v0 - summary", "",
          "> **PROVISIONAL - not issued by EDA.** EDA says it has 'adopted a common set of technical validation criteria' (TG p.21 l.544-547) and refers to",
          "> 'EG Validation Criteria' with a 'File-Folder Structure & Names' sheet (TG p.12 l.278-279; p.31 l.844; p.40 l.1104) - none was published with the drafts.",
          "> This set maps every criterion of the EU Region eCTD Validation Criteria v8.2 (June 2025) and adds the rules the EDA drafts state.",
          "> Full table: `validation-criteria.csv` (one row per rule; columns rule_id, category, rule_text, check_logic, provenance, source, eu_vc_ref, mapping, mapping_reason).",
          "", "`EG-PF-` = Pass/Fail (the task's 'EG-P/F-'; the slash is left out so IDs are safe in file names and URLs), `EG-BP-` = Best Practice.",
          "Kept/adapted EU rules keep the EU number (`EG-PF-15.3` <- EU 15.3); EG-only rules are numbered `E01`... Dropped EU rules are listed as `DROPPED-EU-<n>`.",
          "Category meanings follow TG p.21 l.548-562 (Pass/Fail -> rejected, re-send with the same sequence number; Best Practice -> accepted).", "",
          "## Counts", "", "| Group | Rules |", "|---|---|",
          f"| EU VC 8.2 criteria read | {len(eu)} |", f"| KEEP | {stats['KEEP']} |", f"| ADAPT | {stats['ADAPT']} |", f"| DROP | {stats['DROP']} |",
          f"| EG-specific (from EDA drafts / decisions) | {len(R.EG_RULES)} |",
          f"| **Active EG rules (KEEP + ADAPT + EG-specific)** | **{cnt(lambda r: r[8] != 'DROP')}** - Pass/Fail {cnt(lambda r: r[8] != 'DROP' and r[1] == R.PF)}, Best Practice {cnt(lambda r: r[8] != 'DROP' and r[1] == R.BP)} |",
          f"| Provenance of active rules | EG-DRAFT {cnt(lambda r: r[8] != 'DROP' and r[4] == 'EG-DRAFT')}, EU-DERIVED {cnt(lambda r: r[8] != 'DROP' and r[4] == 'EU-DERIVED')}, ASSUMPTION {cnt(lambda r: r[8] != 'DROP' and r[4] == 'ASSUMPTION')} |",
          "", "## Dropped EU rules", "", "| EU rule | Reason |", "|---|---|"]
    md += [f"| {r[6].replace('EU VC 8.2 ', '')} | {r[9]} |" for r in out_rows if r[8] == "DROP"]
    md += ["", "## Adapted EU rules (what changed)", "", "| EG rule | Category | Change |", "|---|---|---|"]
    md += [f"| {r[0]} | {r[1]} | {r[2]}{(' - ' + r[9]) if r[9] else ''} |" for r in out_rows if r[8] == "ADAPT"]
    md += ["", "## EG-specific rules", "", "| Rule | Category | Rule | Provenance | Source |", "|---|---|---|---|---|"]
    md += [f"| {r[0]} | {r[1]} | {r[2]} | {r[4]} | {r[5]} |" for r in out_rows if r[8] == "EG-SPECIFIC"]
    md += ["", "## Kept EU rules", "", ", ".join(r[0] for r in out_rows if r[8] == "KEEP") + " - text unchanged from EU VC 8.2 (see CSV).", "",
           "## Notes for a validator author", "",
           "* Rules on checksums of the EG util files (EG-PF-3.3, 4.3, 5.3, 6.3) cannot pass/fail until EDA publishes the files: report a warning.",
           "* Everything the DTD enforces (vocabularies, agency code, envelope order, m1-eg tree, 1.6 choice, 1.2 parents without leaves) is caught by EG-PF-9.4;",
           "  the separate EG-PF-E rules exist so that a failure message names the EG rule.",
           "* Lifecycle rules (`lifecycle_needed = Y`, and EG-PF-9.8, 13.2, EG-BP-E09/E10) need the earlier sequences of the same UUID.",
           "* Rules tagged ASSUMPTION must stay warnings/information only in production until EDA confirms them.", ""]
    write(os.path.join(out, "validation-criteria.md"), "\n".join(md))
    return stats, len(eu), out_rows


# ------------------------------------------------------------------ example sequence 0000
def tiny_pdf(text):
    """Minimal PDF 1.4, one page, Helvetica, deterministic (no dates, no IDs)."""
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream"]
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for o in offs:
        out += b"%010d 00000 n \n" % o
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


def write_example(out):
    ex = os.path.join(out, "examples", "0000")
    if os.path.isdir(ex):
        shutil.rmtree(ex)
    m1 = os.path.join(ex, "m1", "eg")
    docs = [  # (section element, href rel. to m1/eg, title, pi-doc (lang,type) or None, leaf ID)
        ("m1-0-cover", "10-cover/cover.pdf", "Cover Letter for Sequence 0000", None, "eg-cover"),
        ("m1-0-cover", "10-cover/tracking.pdf", "Tracking Table", None, "eg-tracking"),
        ("m1-2-1-af", "12-form/121-af/form-af.pdf", "Application Form", None, "eg-form-af"),
        ("m1-2-11-pop", "12-form/1211-pop/pop.pdf", "Proof of Payment", None, "eg-pop"),
        ("m1-3-1-spc-label-pl", "13-pi/131-spclabelpl/en/spc.pdf", "Summary of Product Characteristics (English)", ("en", "spc"), "eg-spc-en"),
        ("m1-3-1-spc-label-pl", "13-pi/131-spclabelpl/ar/pl.pdf", "Package Leaflet (Arabic)", ("ar", "pl"), "eg-pl-ar"),
    ]
    sums = {}
    for _, href, title, _, _ in docs:
        p = os.path.join(m1, href)
        write(p, tiny_pdf(f"PLACEHOLDER - {title} - EG provisional profile v0 example, not a real document"), binary=True)
        sums[href] = md5(p)

    def leaf(href, title, lid, ind):
        return (f'{ind}<leaf ID="{lid}" operation="new" checksum="{sums[href]}" checksum-type="md5" xlink:href="{href}">\n'
                f'{ind}  <title>{title}</title>\n{ind}</leaf>\n')
    L = {d[4]: d for d in docs}
    reg = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE eg-backbone SYSTEM "../../util/dtd/eg-regional.dtd">
<?xml-stylesheet type="text/xsl" href="../../util/style/eg-regional.xsl"?>
<!-- EXAMPLE ONLY - PROVISIONAL EG profile v0, not issued by EDA. Fictitious product, applicant and numbers. -->
<eg-backbone xmlns:xlink="http://www.w3c.org/1999/xlink">
  <eg-envelope>
    <envelope country="eg">
      <identifier>3f2b8c1e-7d4a-4e5b-9c6d-0a1b2c3d4e5f</identifier>
      <submission type="maa">
        <procedure-tracking>
          <number>P-MAA-0001</number>
        </procedure-tracking>
      </submission>
      <submission-unit type="initial"/>
      <applicant>Example Pharma Co.</applicant>
      <agency code="EG-EDA"/>
      <invented-name>Exemplarin 500 mg film-coated tablets</invented-name>
      <registration type="local"/>
      <marketing type="local"/>
      <inn>paracetamol</inn>
      <sequence>0000</sequence>
      <related-sequence>0000</related-sequence>
      <submission-description>Original MAA for Exemplarin 500 mg film-coated tablets</submission-description>
    </envelope>
  </eg-envelope>
  <m1-eg>
    <m1-0-cover>
{leaf(*[L['eg-cover'][i] for i in (1, 2, 4)], '      ')}{leaf(*[L['eg-tracking'][i] for i in (1, 2, 4)], '      ')}    </m1-0-cover>
    <m1-2-form>
      <m1-2-1-af>
{leaf(*[L['eg-form-af'][i] for i in (1, 2, 4)], '        ')}      </m1-2-1-af>
      <m1-2-11-pop>
{leaf(*[L['eg-pop'][i] for i in (1, 2, 4)], '        ')}      </m1-2-11-pop>
    </m1-2-form>
    <m1-3-pi>
      <m1-3-1-spc-label-pl>
        <pi-doc xml:lang="en" type="spc" country="eg">
{leaf(*[L['eg-spc-en'][i] for i in (1, 2, 4)], '          ')}        </pi-doc>
        <pi-doc xml:lang="ar" type="pl" country="eg">
{leaf(*[L['eg-pl-ar'][i] for i in (1, 2, 4)], '          ')}        </pi-doc>
      </m1-3-1-spc-label-pl>
    </m1-3-pi>
  </m1-eg>
</eg-backbone>
"""
    write(os.path.join(m1, "eg-regional.xml"), reg)
    os.makedirs(os.path.join(ex, "util", "dtd"), exist_ok=True)
    for f in ("eg-regional.dtd", "eg-envelope.mod", "eg-leaf.mod", "ich-ectd-3-2.dtd"):
        shutil.copyfile(os.path.join(out, "util", "dtd", f), os.path.join(ex, "util", "dtd", f))
    os.makedirs(os.path.join(ex, "util", "style"), exist_ok=True)
    for f in ("ectd-2-0.xsl", "eg-regional.xsl"):
        shutil.copyfile(os.path.join(out, "util", "style", f), os.path.join(ex, "util", "style", f))
    idx = f"""<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="util/style/ectd-2-0.xsl"?>
<!DOCTYPE ectd:ectd SYSTEM "util/dtd/ich-ectd-3-2.dtd">
<ectd:ectd xmlns:ectd="http://www.ich.org/ectd" xmlns:xlink="http://www.w3c.org/1999/xlink">
  <m1-administrative-information-and-prescribing-information>
    <leaf ID="egm1" operation="new" checksum="{md5(os.path.join(m1, 'eg-regional.xml'))}" checksum-type="md5" xlink:href="m1/eg/eg-regional.xml">
      <title>EG Module 1</title>
    </leaf>
  </m1-administrative-information-and-prescribing-information>
</ectd:ectd>
"""
    write(os.path.join(ex, "index.xml"), idx)
    write(os.path.join(ex, "index-md5.txt"), md5(os.path.join(ex, "index.xml")))
    return ex


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eu-util", required=True)
    ap.add_argument("--eu-vc", required=True)
    ap.add_argument("--out", default=os.path.dirname(HERE))
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    ref = os.path.join(out, "..", "EG-M1-eCTD-Specification-DRAFT-v1.0-reference.md")
    rows = parse_appendix2(ref)
    nodes = build_tree(rows)
    write_vocab(out)
    write_dtd(out, nodes, a.eu_util)
    write_xsl(out, nodes, a.eu_util)
    write_folders(out, nodes, rows)
    stats, n_eu, _ = write_vc(out, a.eu_vc)
    ex = write_example(out)
    print(f"sections: {len(nodes)} (parents {sum(n['kind']=='parent' for n in nodes)}, leaf containers {sum(n['kind']=='leaves' for n in nodes)})")
    print(f"EU VC rules: {n_eu} -> {stats}; EG-specific: {len(R.EG_RULES)}")
    print(f"example: {ex}")


if __name__ == "__main__":
    main()
