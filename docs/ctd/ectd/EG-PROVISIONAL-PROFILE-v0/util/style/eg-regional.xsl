<?xml version="1.0" encoding="UTF-8"?>
<!--
PROVISIONAL - NOT ISSUED BY THE EGYPTIAN DRUG AUTHORITY (EDA).
EG Module 1 style sheet (name ASSUMPTION, decision D-11).
Part of the "EG provisional profile v0" for ICH eCTD v3.2.2, built 2026-11-06.
Derived from the EU Module 1 eCTD util package v3.1 (eu-regional.xsl v3.1, EMA, June 2024) and adapted to the
element and attribute names of the EDA draft "EG Module 1 eCTD Specification" v1.0/2026 and the EDA draft
"Technical Guidance for eCTD Submissions in Egypt" v1.0/2026. EDA has not published an EG DTD; replace this
file with the EDA-issued one as soon as it exists. Provenance of every name and value: README.md and vocab/*.yaml
(EG-DRAFT = stated by EDA draft, EU-DERIVED = taken from EU, ASSUMPTION = our choice).
-->
<!-- Shows every EG M1 section, populated or not (SPEC p.6 l.29-31; TG p.26 l.707-709). XSLT 1.0 so that browsers can run it.
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
					h1, h2, h3, h4 {margin-top:3pt ; margin-bottom:0pt}
					ul {margin-bottom:0pt ; margin-top:0pt}
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
		<xsl:choose>
			<xsl:when test="@type='maa'">Marketing Authorisation Application</xsl:when>
			<xsl:when test="@type='var-pac-n'">Variation PAC-N (notification)</xsl:when>
			<xsl:when test="@type='var-pac-b'">Variation PAC-B</xsl:when>
			<xsl:when test="@type='var-pac-a'">Variation PAC-A (annual)</xsl:when>
			<xsl:when test="@type='var-pac-ii'">Variation PAC-II (major)</xsl:when>
			<xsl:when test="@type='renewal'">Renewal</xsl:when>
			<xsl:when test="@type='asmf'">Active Substance Master File</xsl:when>
			<xsl:when test="@type='cep'">Certificate of suitability (EDQM only)</xsl:when>
			<xsl:when test="@type='none'">none (reformat / baseline only)</xsl:when>
			<xsl:when test="@type='preass'">Pre-assessment</xsl:when>
			<xsl:when test="@type='pacstab'">Post MA Commitments (Stability Studies)</xsl:when>
			<xsl:when test="@type='paccadc'">Post MA Commitments (CADC analysis)</xsl:when>
			<xsl:when test="@type='paci'">Post MA Commitments (Inspection)</xsl:when>
			<xsl:when test="@type='pacqr'">Post MA Commitments (Quality requirements)</xsl:when>
			<xsl:when test="@type='5yr'">Fifth Year Report</xsl:when>
			<xsl:when test="@type='appeal'">Appeals</xsl:when>
			<xsl:when test="@type='preappinq'">Preliminary Approval Inquiry</xsl:when>
			<xsl:when test="@type='pmf'">Plasma Master File</xsl:when>
			<xsl:when test="@type='withdrawal'">Withdrawal (of the marketing authorisation entirely)</xsl:when>
			<xsl:when test="@type='maa-inn'">MAA for an innovative product</xsl:when>
			<xsl:when test="@type='ipv-admc'">Innovative product variation - Administrative changes</xsl:when>
			<xsl:when test="@type='ipv-admlc'">Innovative product variation - Administrative product labelling information changes</xsl:when>
			<xsl:when test="@type='ipv-tlc'">Innovative product variation - therapeutic labelling information changes</xsl:when>
			<xsl:when test="@type='ipv-pu'">Innovative product variation - pack update</xsl:when>
			<xsl:when test="@type='ipv-safeffc'">Innovative product variation - safety and efficacy labelling changes</xsl:when>
			<xsl:when test="@type='imv-majvar'">Innovative medicinal products variation - Major variation</xsl:when>
			<xsl:when test="@type='imv-minvar'">Innovative medicinal products variation - Minor variation</xsl:when>
			<xsl:when test="@type='imv-not'">Innovative medicinal products variation - Notifications</xsl:when>
			<xsl:when test="@type='ibv-majqualc'">Innovative biological products variation - Major quality changes</xsl:when>
			<xsl:when test="@type='ibv-modqualc'">Innovative biological products variation - Moderate quality changes</xsl:when>
			<xsl:when test="@type='ibv-minqualc'">Innovative biological products variation - Minor quality changes</xsl:when>
			<xsl:when test="@type='ibv-qcnoimp'">Innovative biological products variation - Quality changes with no impact</xsl:when>
			<xsl:when test="@type='maa-nt'">MAA - Normal Track</xsl:when>
			<xsl:when test="@type='maa-ft'">MAA - Fast Track</xsl:when>
			<xsl:when test="@type='maa-sb'">MAA - Second Brand</xsl:when>
			<xsl:when test="@type='maa-rl1'">MAA - Reliance level 1</xsl:when>
			<xsl:when test="@type='maa-rl2'">MAA - Reliance level 2</xsl:when>
			<xsl:when test="@type='maa-bios'">MAA - Biosimilar</xsl:when>
			<xsl:when test="@type='np-modqualc'">Normal pathway - Moderate quality changes</xsl:when>
			<xsl:when test="@type='np-pilc'">Normal pathway - Product labelling information changes</xsl:when>
			<xsl:when test="@type='np-majqualc'">Normal pathway - Major quality changes</xsl:when>
			<xsl:when test="@type='np-safeffc'">Normal pathway - Safety and efficacy changes</xsl:when>
			<xsl:when test="@type='np-admpilc'">Normal pathway - Administrative product labelling information changes</xsl:when>
			<xsl:when test="@type='np-packup'">Normal pathway - pack update</xsl:when>
			<xsl:when test="@type='np-adminc'">Normal pathway - Administrative changes</xsl:when>
			<xsl:when test="@type='rp-majcq'">Reliance pathway - Major quality changes</xsl:when>
			<xsl:when test="@type='rp-modqc'">Reliance pathway - Moderate quality changes</xsl:when>
			<xsl:when test="@type='rl-pilc'">Reliance pathway - product labelling information changes</xsl:when>
			<xsl:when test="@type='not-minqc'">Notification - Minor quality changes</xsl:when>
			<xsl:when test="@type='not-qcnoimp'">Notification - quality changes with no impact</xsl:when>
			<xsl:otherwise><xsl:value-of select="@type"/></xsl:otherwise>
		</xsl:choose>
		<xsl:if test="@mode"> - mode: <xsl:choose>
			<xsl:when test="@mode='single'">A Single Regulatory Activity</xsl:when>
			<xsl:when test="@mode='grouping'">A Grouped Activity</xsl:when>
			<xsl:when test="@mode='parallel-single'">Parallel Assessment Single RA (imported products, evaluated together with the country of origin)</xsl:when>
			<xsl:when test="@mode='parallel-grouping'">Parallel Assessment Grouped RA</xsl:when>
			<xsl:otherwise><xsl:value-of select="@mode"/></xsl:otherwise>
		</xsl:choose></xsl:if>
		<xsl:if test="number"> - high-level number: <xsl:value-of select="number"/></xsl:if>
	</xsl:template>
	<xsl:template match="submission-unit" mode="submission-unit">
		<xsl:choose>
			<xsl:when test="@type='initial'">Initial submission to start any regulatory activity</xsl:when>
			<xsl:when test="@type='validation-response'">Rectifying submission in response to content validation issues</xsl:when>
			<xsl:when test="@type='response'">Response to questions / outstanding issues; also the consolidation sequence after withdrawal or rejection of a single regulatory activity</xsl:when>
			<xsl:when test="@type='additional-info'">Other additional information (e.g. missing files) when validation-response or response is not suitable</xsl:when>
			<xsl:when test="@type='corrigendum'">Correction of information after the regulatory activity has concluded; only after case-by-case agreement with EDA</xsl:when>
			<xsl:when test="@type='reformat'">Baseline: reformatting of an existing application into eCTD, no content change, not reviewed; always with submission type 'none'</xsl:when>
			<xsl:when test="@type='re-examination'">Request for re-examination of an authority opinion (MAA, type II variation)</xsl:when>
			<xsl:otherwise><xsl:value-of select="@type"/></xsl:otherwise>
		</xsl:choose>
	</xsl:template>
	<xsl:template match="registration" mode="registration">
		<xsl:choose>
			<xsl:when test="@type='local'">Locally Manufactured Products</xsl:when>
			<xsl:when test="@type='toll'">Toll Products</xsl:when>
			<xsl:when test="@type='f-toll'">F-Toll Products</xsl:when>
			<xsl:when test="@type='under-license'">Under License Products</xsl:when>
			<xsl:when test="@type='imported-finished'">Imported (Finished) Products</xsl:when>
			<xsl:when test="@type='imported-bulk'">Imported Bulk Products</xsl:when>
			<xsl:otherwise><xsl:value-of select="@type"/></xsl:otherwise>
		</xsl:choose>
	</xsl:template>
	<xsl:template match="marketing" mode="marketing">
		<xsl:choose>
			<xsl:when test="@type='local'">Local market</xsl:when>
			<xsl:when test="@type='tender'">Tender</xsl:when>
			<xsl:when test="@type='export'">Export</xsl:when>
			<xsl:when test="@type='hospital'">Hospital use</xsl:when>
			<xsl:otherwise><xsl:value-of select="@type"/></xsl:otherwise>
		</xsl:choose>
	</xsl:template>
	<xsl:template match="agency" mode="agency">
		<xsl:choose>
			<xsl:when test="@code='EG-EDA'">Egyptian Drug Authority</xsl:when>
			<xsl:otherwise><xsl:value-of select="@code"/></xsl:otherwise>
		</xsl:choose> (<xsl:value-of select="@code"/>)
	</xsl:template>
	<xsl:template match="pi-doc" mode="pidoc-type">
		<xsl:choose>
			<xsl:when test="@type='spc'">Summary of Product Characteristics</xsl:when>
			<xsl:when test="@type='pl'">Package Leaflet</xsl:when>
			<xsl:when test="@type='interpack'">Outer and immediate labelling submitted as one file</xsl:when>
			<xsl:when test="@type='outer'">Outer packaging (labelling)</xsl:when>
			<xsl:when test="@type='impack'">Immediate packaging (labelling)</xsl:when>
			<xsl:when test="@type='combined'">Combined product information (SmPC + labelling + PL in one file)</xsl:when>
			<xsl:when test="@type='other'">Other product information</xsl:when>
			<xsl:otherwise><xsl:value-of select="@type"/></xsl:otherwise>
		</xsl:choose>
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
		<tr>
			<td valign="top" width="9%"><b>1.0</b></td>
			<td style="padding-left:4px"><b>Cover Letter</b> <small>(m1-0-cover)</small>
				<ul type="square"><xsl:apply-templates select="//m1-0-cover/leaf | //m1-0-cover/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2</b></td>
			<td style="padding-left:4px"><b>Application Forms</b> <small>(m1-2-form)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.1</b></td>
			<td style="padding-left:20px"><b>Application Form</b> <small>(m1-2-1-af)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-1-af/leaf | //m1-2-1-af/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2</b></td>
			<td style="padding-left:20px"><b>Legal Documents</b> <small>(m1-2-2-legal)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.1</b></td>
			<td style="padding-left:36px"><b>Letter of Attorney for Company Representative</b> <small>(m1-2-2-1-loattor)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-1-loattor/leaf | //m1-2-2-1-loattor/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.2</b></td>
			<td style="padding-left:36px"><b>Manufacturing License and IDA License</b> <small>(m1-2-2-2-manlic)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-2-manlic/leaf | //m1-2-2-2-manlic/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.3</b></td>
			<td style="padding-left:36px"><b>GMP Certificate(s) / Alternative Documents</b> <small>(m1-2-2-3-gmpcert)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-3-gmpcert/leaf | //m1-2-2-3-gmpcert/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.4</b></td>
			<td style="padding-left:36px"><b>The Register of Trade</b> <small>(m1-2-2-4-trade)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-4-trade/leaf | //m1-2-2-4-trade/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.5</b></td>
			<td style="padding-left:36px"><b>Toll Manufacturer License</b> <small>(m1-2-2-5-toll)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-5-toll/leaf | //m1-2-2-5-toll/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.6</b></td>
			<td style="padding-left:36px"><b>Scientific Office License</b> <small>(m1-2-2-6-sol)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-6-sol/leaf | //m1-2-2-6-sol/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.7</b></td>
			<td style="padding-left:36px"><b>Importers Register License</b> <small>(m1-2-2-7-import)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-7-import/leaf | //m1-2-2-7-import/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.8</b></td>
			<td style="padding-left:36px"><b>Store License</b> <small>(m1-2-2-8-storelic)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-8-storelic/leaf | //m1-2-2-8-storelic/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.9</b></td>
			<td style="padding-left:36px"><b>Authorisation Letter / Agency Agreement</b> <small>(m1-2-2-9-authlet)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-9-authlet/leaf | //m1-2-2-9-authlet/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.10</b></td>
			<td style="padding-left:36px"><b>Manufacturing Agreement</b> <small>(m1-2-2-10-managre)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-10-managre/leaf | //m1-2-2-10-managre/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.11</b></td>
			<td style="padding-left:36px"><b>Packaging Agreement</b> <small>(m1-2-2-11-pacagre)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-11-pacagre/leaf | //m1-2-2-11-pacagre/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.12</b></td>
			<td style="padding-left:36px"><b>Storage Agreement</b> <small>(m1-2-2-12-storeagre)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-12-storeagre/leaf | //m1-2-2-12-storeagre/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.13</b></td>
			<td style="padding-left:36px"><b>Other Agreements</b> <small>(m1-2-2-13-othagre)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-13-othagre/leaf | //m1-2-2-13-othagre/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.14</b></td>
			<td style="padding-left:36px"><b>Termination / Waiver</b> <small>(m1-2-2-14-term)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-14-term/leaf | //m1-2-2-14-term/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.15</b></td>
			<td style="padding-left:36px"><b>Tax Card</b> <small>(m1-2-2-15-tax)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-15-tax/leaf | //m1-2-2-15-tax/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.16</b></td>
			<td style="padding-left:36px"><b>List of Distributors</b> <small>(m1-2-2-16-distribut)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-16-distribut/leaf | //m1-2-2-16-distribut/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.17</b></td>
			<td style="padding-left:36px"><b>IP Protection Law No. 82 of 2002 Commitment</b> <small>(m1-2-2-17-ipp)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-17-ipp/leaf | //m1-2-2-17-ipp/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.18</b></td>
			<td style="padding-left:36px"><b>NEW local MA legal Agreement</b> <small>(m1-2-2-18-newlegag)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-18-newlegag/leaf | //m1-2-2-18-newlegag/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.19</b></td>
			<td style="padding-left:36px"><b>Letter of Authorisation for a new Applicant in Egypt</b> <small>(m1-2-2-19-loauth)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-19-loauth/leaf | //m1-2-2-19-loauth/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.20</b></td>
			<td style="padding-left:36px"><b>PV Agreement between the MAH &amp; the Service Provider</b> <small>(m1-2-2-20-pvagre)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-20-pvagre/leaf | //m1-2-2-20-pvagre/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.2.21</b></td>
			<td style="padding-left:36px"><b>GMP Certificate</b> <small>(m1-2-2-21-gmpcert2)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-2-21-gmpcert2/leaf | //m1-2-2-21-gmpcert2/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3</b></td>
			<td style="padding-left:20px"><b>EDA Approvals</b> <small>(m1-2-3-edaapp)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.1</b></td>
			<td style="padding-left:36px"><b>Registration Request Approval</b> <small>(m1-2-3-1-regreq)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-1-regreq/leaf | //m1-2-3-1-regreq/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.2</b></td>
			<td style="padding-left:36px"><b>Inquiry Approval</b> <small>(m1-2-3-2-inqapp)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-2-inqapp/leaf | //m1-2-3-2-inqapp/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.3</b></td>
			<td style="padding-left:36px"><b>Name Approval</b> <small>(m1-2-3-3-nameapp)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-3-nameapp/leaf | //m1-2-3-3-nameapp/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.4</b></td>
			<td style="padding-left:36px"><b>Registration License</b> <small>(m1-2-3-4-reglic)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-4-reglic/leaf | //m1-2-3-4-reglic/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.5</b></td>
			<td style="padding-left:36px"><b>Preliminary Approval</b> <small>(m1-2-3-5-prelimapp)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-5-prelimapp/leaf | //m1-2-3-5-prelimapp/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.6</b></td>
			<td style="padding-left:36px"><b>Non-Reference Approval</b> <small>(m1-2-3-6-nonrefapp)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-6-nonrefapp/leaf | //m1-2-3-6-nonrefapp/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.7</b></td>
			<td style="padding-left:36px"><b>Exemption Approval</b> <small>(m1-2-3-7-exemptapp)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-7-exemptapp/leaf | //m1-2-3-7-exemptapp/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.8</b></td>
			<td style="padding-left:36px"><b>Pricing Certificate</b> <small>(m1-2-3-8-price)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-8-price/leaf | //m1-2-3-8-price/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.9</b></td>
			<td style="padding-left:36px"><b>Pharmacovigilance Approval</b> <small>(m1-2-3-9-pvapp)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-9-pvapp/leaf | //m1-2-3-9-pvapp/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.10</b></td>
			<td style="padding-left:36px"><b>Inspection Report</b> <small>(m1-2-3-10-insprep)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-10-insprep/leaf | //m1-2-3-10-insprep/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.11</b></td>
			<td style="padding-left:36px"><b>Importation Approval for each API</b> <small>(m1-2-3-11-importapp)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-11-importapp/leaf | //m1-2-3-11-importapp/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.12</b></td>
			<td style="padding-left:36px"><b>CADC Report</b> <small>(m1-2-3-12-cadcrep)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-12-cadcrep/leaf | //m1-2-3-12-cadcrep/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.13</b></td>
			<td style="padding-left:36px"><b>Stability Study Approval</b> <small>(m1-2-3-13-stabstud)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-13-stabstud/leaf | //m1-2-3-13-stabstud/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.14</b></td>
			<td style="padding-left:36px"><b>Stability Protocol Approval</b> <small>(m1-2-3-14-stabprot)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-14-stabprot/leaf | //m1-2-3-14-stabprot/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.15</b></td>
			<td style="padding-left:36px"><b>Module 3 Approval</b> <small>(m1-2-3-15-m3app)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-15-m3app/leaf | //m1-2-3-15-m3app/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.16</b></td>
			<td style="padding-left:36px"><b>Module 5 Approval</b> <small>(m1-2-3-16-m5app)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-16-m5app/leaf | //m1-2-3-16-m5app/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.17</b></td>
			<td style="padding-left:36px"><b>Pre-approved letters from EDA concerning the product</b> <small>(m1-2-3-17-preapplet)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-17-preapplet/leaf | //m1-2-3-17-preapplet/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.18</b></td>
			<td style="padding-left:36px"><b>Variation Approvals</b> <small>(m1-2-3-18-varapp)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-18-varapp/leaf | //m1-2-3-18-varapp/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.19</b></td>
			<td style="padding-left:36px"><b>Innovative Products Scientific Committee Approval</b> <small>(m1-2-3-19-ipsca)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-19-ipsca/leaf | //m1-2-3-19-ipsca/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.3.20</b></td>
			<td style="padding-left:36px"><b>Registration License for the Solvent</b> <small>(m1-2-3-20-reglicsolv)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-3-20-reglicsolv/leaf | //m1-2-3-20-reglicsolv/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4</b></td>
			<td style="padding-left:20px"><b>Declarations</b> <small>(m1-2-4-declar)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.1</b></td>
			<td style="padding-left:36px"><b>Declaration Letter stating the list of Registered &amp; Under-Registration Products owned by the Toll Company</b> <small>(m1-2-4-1-regprod)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-1-regprod/leaf | //m1-2-4-1-regprod/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.2</b></td>
			<td style="padding-left:36px"><b>Declaration Letter from the License Holder specifying the API Manufacturers</b> <small>(m1-2-4-2-apiman)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-2-apiman/leaf | //m1-2-4-2-apiman/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.3</b></td>
			<td style="padding-left:36px"><b>Declaration letter from the license holder specifying approved pack in Egypt</b> <small>(m1-2-4-3-liceholdpac)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-3-liceholdpac/leaf | //m1-2-4-3-liceholdpac/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.4</b></td>
			<td style="padding-left:36px"><b>Declaration Letter from the License Holder stating the Form of Bulk (Strips, Capsules, etc.)</b> <small>(m1-2-4-4-liceholdbulk)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-4-liceholdbulk/leaf | //m1-2-4-4-liceholdbulk/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.5</b></td>
			<td style="padding-left:36px"><b>Declaration Letter from the Manufacturer of the Active Substance to inform the Applicant in case of Modification of the manufacturing Process or Specifications</b> <small>(m1-2-4-5-apimanappl)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-5-apimanappl/leaf | //m1-2-4-5-apimanappl/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.6</b></td>
			<td style="padding-left:36px"><b>Declaration Letter from API Supplier</b> <small>(m1-2-4-6-apisupp)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-6-apisupp/leaf | //m1-2-4-6-apisupp/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.7</b></td>
			<td style="padding-left:36px"><b>Declaration Letter for Site Addition</b> <small>(m1-2-4-7-siteadd)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-7-siteadd/leaf | //m1-2-4-7-siteadd/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.8</b></td>
			<td style="padding-left:36px"><b>Declaration Letter Form LH stating all Variations &amp; Justification for the Change</b> <small>(m1-2-4-8-allvar)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-8-allvar/leaf | //m1-2-4-8-allvar/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.9</b></td>
			<td style="padding-left:36px"><b>Other declarations requested by Egyptian Drug Authority</b> <small>(m1-2-4-9-decother)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-9-decother/leaf | //m1-2-4-9-decother/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.10</b></td>
			<td style="padding-left:36px"><b>List of the Countries where the Product is registered &amp; marketed</b> <small>(m1-2-4-10-countries)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-10-countries/leaf | //m1-2-4-10-countries/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.11</b></td>
			<td style="padding-left:36px"><b>Ph. Eur. Certificate(s) of Suitability for TSE</b> <small>(m1-2-4-11-tse)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-11-tse/leaf | //m1-2-4-11-tse/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.12</b></td>
			<td style="padding-left:36px"><b>TSE/BSE Supplier Safety Declaration (if CEP not available)</b> <small>(m1-2-4-12-bsesafdec)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-12-bsesafdec/leaf | //m1-2-4-12-bsesafdec/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.13</b></td>
			<td style="padding-left:36px"><b>Raw Materials Storage Responsibility Declaration (for local Products)</b> <small>(m1-2-4-13-rawmat)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-13-rawmat/leaf | //m1-2-4-13-rawmat/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.14</b></td>
			<td style="padding-left:36px"><b>Excipient/s Supplier Name &amp; Origin</b> <small>(m1-2-4-14-exipsup)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-14-exipsup/leaf | //m1-2-4-14-exipsup/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.15</b></td>
			<td style="padding-left:36px"><b>Trade Name of the Albumin used as Stabilizer</b> <small>(m1-2-4-15-albtraden)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-15-albtraden/leaf | //m1-2-4-15-albtraden/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.16</b></td>
			<td style="padding-left:36px"><b>Albumin as Stabilizer Batch Release Certificate</b> <small>(m1-2-4-16-albstabil)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-16-albstabil/leaf | //m1-2-4-16-albstabil/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.17</b></td>
			<td style="padding-left:36px"><b>Plasma Derivative Supplier Safety and Efficacy Commitment</b> <small>(m1-2-4-17-plasdersub)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-17-plasdersub/leaf | //m1-2-4-17-plasdersub/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.18</b></td>
			<td style="padding-left:36px"><b>No Change in physical Address and Product related Processes Declaration</b> <small>(m1-2-4-18-nochaadd)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-18-nochaadd/leaf | //m1-2-4-18-nochaadd/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.19</b></td>
			<td style="padding-left:36px"><b>Pack Type Declaration</b> <small>(m1-2-4-19-pactype)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-19-pactype/leaf | //m1-2-4-19-pactype/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.20</b></td>
			<td style="padding-left:36px"><b>Insert Declaration Letter</b> <small>(m1-2-4-20-insdeclet)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-20-insdeclet/leaf | //m1-2-4-20-insdeclet/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.21</b></td>
			<td style="padding-left:36px"><b>Site Master File Declaration</b> <small>(m1-2-4-21-sitemfdec)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-21-sitemfdec/leaf | //m1-2-4-21-sitemfdec/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.4.22</b></td>
			<td style="padding-left:36px"><b>Storage Temperature at 25 °C Declaration</b> <small>(m1-2-4-22-storetemp)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-4-22-storetemp/leaf | //m1-2-4-22-storetemp/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.5</b></td>
			<td style="padding-left:20px"><b>Reference Product Document / Compendial</b> <small>(m1-2-5-refprod)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.5.1</b></td>
			<td style="padding-left:36px"><b>The Reference Product Documents</b> <small>(m1-2-5-1-refproddoc)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-5-1-refproddoc/leaf | //m1-2-5-1-refproddoc/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.5.2</b></td>
			<td style="padding-left:36px"><b>Scientific Reference (Trials &amp; Literature)</b> <small>(m1-2-5-2-sciref)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-5-2-sciref/leaf | //m1-2-5-2-sciref/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.5.3</b></td>
			<td style="padding-left:36px"><b>Reference for the trade name change</b> <small>(m1-2-5-3-reftradn)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-5-3-reftradn/leaf | //m1-2-5-3-reftradn/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.5.4</b></td>
			<td style="padding-left:36px"><b>The latest recent Pharmacopeia</b> <small>(m1-2-5-4-recph)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-5-4-recph/leaf | //m1-2-5-4-recph/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.6</b></td>
			<td style="padding-left:20px"><b>Imported Products Documents</b> <small>(m1-2-6-importdoc)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.6.1</b></td>
			<td style="padding-left:36px"><b>Certificate of Pharmaceutical Product (CPP)</b> <small>(m1-2-6-1-cpp)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-6-1-cpp/leaf | //m1-2-6-1-cpp/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.6.2</b></td>
			<td style="padding-left:36px"><b>List of Affiliates / Subsidiaries</b> <small>(m1-2-6-2-loaff)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-6-2-loaff/leaf | //m1-2-6-2-loaff/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.7</b></td>
			<td style="padding-left:20px"><b>Reliance Documents</b> <small>(m1-2-7-reliance)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.7.1</b></td>
			<td style="padding-left:36px"><b>Sameness Letter</b> <small>(m1-2-7-1-sameness)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-7-1-sameness/leaf | //m1-2-7-1-sameness/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.7.2</b></td>
			<td style="padding-left:36px"><b>Unredacted Assessment Report</b> <small>(m1-2-7-2-unredact)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-7-2-unredact/leaf | //m1-2-7-2-unredact/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.7.3</b></td>
			<td style="padding-left:36px"><b>RRA Variation Application with Annexes</b> <small>(m1-2-7-3-rravar)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-7-3-rravar/leaf | //m1-2-7-3-rravar/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.7.4</b></td>
			<td style="padding-left:36px"><b>Correspondences between the Applicant and the Reference Agency</b> <small>(m1-2-7-4-correspond)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-7-4-correspond/leaf | //m1-2-7-4-correspond/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.7.5</b></td>
			<td style="padding-left:36px"><b>List of Changes after first MA issued from EMA or FDA</b> <small>(m1-2-7-5-lofchange)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-7-5-lofchange/leaf | //m1-2-7-5-lofchange/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.7.6</b></td>
			<td style="padding-left:36px"><b>Rejection or Amendment Reporting Commitment</b> <small>(m1-2-7-6-reject)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-7-6-reject/leaf | //m1-2-7-6-reject/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.8</b></td>
			<td style="padding-left:20px"><b>Composition Documents</b> <small>(m1-2-8-composit)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.8.1</b></td>
			<td style="padding-left:36px"><b>Composition Certificate</b> <small>(m1-2-8-1-compositcert)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-8-1-compositcert/leaf | //m1-2-8-1-compositcert/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.8.2</b></td>
			<td style="padding-left:36px"><b>Specifications</b> <small>(m1-2-8-2-spec)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-8-2-spec/leaf | //m1-2-8-2-spec/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.8.3</b></td>
			<td style="padding-left:36px"><b>Any Composition Calculations</b> <small>(m1-2-8-3-compcalc)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-8-3-compcalc/leaf | //m1-2-8-3-compcalc/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.8.4</b></td>
			<td style="padding-left:36px"><b>Pellets / Premix Composition and Certificates</b> <small>(m1-2-8-4-pelletcomp)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-8-4-pelletcomp/leaf | //m1-2-8-4-pelletcomp/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.8.5</b></td>
			<td style="padding-left:36px"><b>Opadry / Coating Premix Composition</b> <small>(m1-2-8-5-opadry)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-8-5-opadry/leaf | //m1-2-8-5-opadry/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.8.6</b></td>
			<td style="padding-left:36px"><b>Capsule Shell Composition</b> <small>(m1-2-8-6-capshell)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-8-6-capshell/leaf | //m1-2-8-6-capshell/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.8.7</b></td>
			<td style="padding-left:36px"><b>Synonyms Evidence</b> <small>(m1-2-8-7-synonyms)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-8-7-synonyms/leaf | //m1-2-8-7-synonyms/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.9</b></td>
			<td style="padding-left:20px"><b>Certificate of Analysis</b> <small>(m1-2-9-coa)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-9-coa/leaf | //m1-2-9-coa/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.10</b></td>
			<td style="padding-left:20px"><b>Post Approval Changes Requirements</b> <small>(m1-2-10-postappch)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.10.1</b></td>
			<td style="padding-left:36px"><b>PAC Approval from the COO (Imported Products)</b> <small>(m1-2-10-1-pacapp)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-10-1-pacapp/leaf | //m1-2-10-1-pacapp/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.10.2</b></td>
			<td style="padding-left:36px"><b>Summary of Change for Variation</b> <small>(m1-2-10-2-sumcavar)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-10-2-sumcavar/leaf | //m1-2-10-2-sumcavar/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.10.3</b></td>
			<td style="padding-left:36px"><b>Justification of the proposed Post Approval Change</b> <small>(m1-2-10-3-justpoc)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-10-3-justpoc/leaf | //m1-2-10-3-justpoc/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.10.4</b></td>
			<td style="padding-left:36px"><b>Any additional Documents relevant to Variations</b> <small>(m1-2-10-4-anydoc)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-10-4-anydoc/leaf | //m1-2-10-4-anydoc/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.11</b></td>
			<td style="padding-left:20px"><b>Proof of Payment</b> <small>(m1-2-11-pop)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-11-pop/leaf | //m1-2-11-pop/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.12</b></td>
			<td style="padding-left:20px"><b>Analysis Requirements Documentation (for Biological Products only)</b> <small>(m1-2-12-analysreq)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.12.1</b></td>
			<td style="padding-left:36px"><b>Detailed Standard Operating Procedures (SOP)</b> <small>(m1-2-12-1-sop)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-12-1-sop/leaf | //m1-2-12-1-sop/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.12.2</b></td>
			<td style="padding-left:36px"><b>Summary Protocol for Vaccines and Plasma derived Medicinal Products</b> <small>(m1-2-12-2-sumvacc)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-12-2-sumvacc/leaf | //m1-2-12-2-sumvacc/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.13</b></td>
			<td style="padding-left:20px"><b>For Plasma derived Medicinal Products</b> <small>(m1-2-13-plasma)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.13.1</b></td>
			<td style="padding-left:36px"><b>Plasma Master File</b> <small>(m1-2-13-1-pmf)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-13-1-pmf/leaf | //m1-2-13-1-pmf/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.13.2</b></td>
			<td style="padding-left:36px"><b>Certificate of Plasma Batch Release from Health Authority</b> <small>(m1-2-13-2-plasbatch)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-13-2-plasbatch/leaf | //m1-2-13-2-plasbatch/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.13.3</b></td>
			<td style="padding-left:36px"><b>PMF Approval from Country of Origin</b> <small>(m1-2-13-3-pmfapp)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-13-3-pmfapp/leaf | //m1-2-13-3-pmfapp/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.14</b></td>
			<td style="padding-left:20px"><b>Scientific Advice Report</b> <small>(m1-2-14-scienadv)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-14-scienadv/leaf | //m1-2-14-scienadv/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.15</b></td>
			<td style="padding-left:20px"><b>Documents related PV</b> <small>(m1-2-15-relpv)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.15.1</b></td>
			<td style="padding-left:36px"><b>Latest valid PSMF Assessment Report / Confirmation E-mail of PSMF Document(s) Receival</b> <small>(m1-2-15-1-valpsmfas)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-15-1-valpsmfas/leaf | //m1-2-15-1-valpsmfas/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.15.2</b></td>
			<td style="padding-left:36px"><b>Updated Version of Summary of PSMF(s) / PSSF</b> <small>(m1-2-15-2-updpsmf)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-15-2-updpsmf/leaf | //m1-2-15-2-updpsmf/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.15.3</b></td>
			<td style="padding-left:36px"><b>The latest PSUR(s) (or the ACO in Case of Renewal)</b> <small>(m1-2-15-3-latpsur)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-15-3-latpsur/leaf | //m1-2-15-3-latpsur/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.15.4</b></td>
			<td style="padding-left:36px"><b>The most updated EU/Global/Core-Risk Management Plan (RMP)</b> <small>(m1-2-15-4-updrmp)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-15-4-updrmp/leaf | //m1-2-15-4-updrmp/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.15.5</b></td>
			<td style="padding-left:36px"><b>The Egyptian Display of EU-RMP / Global-RMP</b> <small>(m1-2-15-5-egrmp)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-15-5-egrmp/leaf | //m1-2-15-5-egrmp/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.16</b></td>
			<td style="padding-left:20px"><b>Documents related Inspection</b> <small>(m1-2-16-relinsp)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.16.1</b></td>
			<td style="padding-left:36px"><b>Site Master File for all Manufacturers</b> <small>(m1-2-16-1-smfall)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-16-1-smfall/leaf | //m1-2-16-1-smfall/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.16.2</b></td>
			<td style="padding-left:36px"><b>Latest Full Inspection Report(s) by SRA (past 3 Years)</b> <small>(m1-2-16-2-fullinsprep)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-16-2-fullinsprep/leaf | //m1-2-16-2-fullinsprep/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.16.3</b></td>
			<td style="padding-left:36px"><b>One completed Batch Manufacturing and Packaging Record</b> <small>(m1-2-16-3-batchrep)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-16-3-batchrep/leaf | //m1-2-16-3-batchrep/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.16.4</b></td>
			<td style="padding-left:36px"><b>List of any Recalls with Quality Defects (past 3 Years) (if found)</b> <small>(m1-2-16-4-recalls)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-16-4-recalls/leaf | //m1-2-16-4-recalls/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.16.5</b></td>
			<td style="padding-left:36px"><b>Any Warning Letter or equivalent regulatory Action (Production-line specific) (if found)</b> <small>(m1-2-16-5-warnlet)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-16-5-warnlet/leaf | //m1-2-16-5-warnlet/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.16.6</b></td>
			<td style="padding-left:36px"><b>Last Annual Product Quality Review</b> <small>(m1-2-16-6-annualrev)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-16-6-annualrev/leaf | //m1-2-16-6-annualrev/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.2.16.7</b></td>
			<td style="padding-left:36px"><b>Cold Chain Storage &amp; Transportation Procedures including Excursion allowed</b> <small>(m1-2-16-7-coldchain)</small>
				<ul type="square"><xsl:apply-templates select="//m1-2-16-7-coldchain/leaf | //m1-2-16-7-coldchain/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.3</b></td>
			<td style="padding-left:4px"><b>Product Information</b> <small>(m1-3-pi)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.3.1</b></td>
			<td style="padding-left:20px"><b>SmPC, Labelling and Package Leaflet</b> <small>(m1-3-1-spc-label-pl)</small>
				<xsl:apply-templates select="//m1-3-1-spc-label-pl"/>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.3.2</b></td>
			<td style="padding-left:20px"><b>Mock-up</b> <small>(m1-3-2-mockup)</small>
				<ul type="square"><xsl:apply-templates select="//m1-3-2-mockup/leaf | //m1-3-2-mockup/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.3.3</b></td>
			<td style="padding-left:20px"><b>Specimen</b> <small>(m1-3-3-specimen)</small>
				<ul type="square"><xsl:apply-templates select="//m1-3-3-specimen/leaf | //m1-3-3-specimen/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.3.4</b></td>
			<td style="padding-left:20px"><b>Consultation with Target Patient Groups</b> <small>(m1-3-4-consultation)</small>
				<ul type="square"><xsl:apply-templates select="//m1-3-4-consultation/leaf | //m1-3-4-consultation/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.3.5</b></td>
			<td style="padding-left:20px"><b>Product Information already approved in the Member States</b> <small>(m1-3-5-approved)</small>
				<ul type="square"><xsl:apply-templates select="//m1-3-5-approved/leaf | //m1-3-5-approved/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.3.6</b></td>
			<td style="padding-left:20px"><b>Braille</b> <small>(m1-3-6-braille)</small>
				<ul type="square"><xsl:apply-templates select="//m1-3-6-braille/leaf | //m1-3-6-braille/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.4</b></td>
			<td style="padding-left:4px"><b>Information about the Experts</b> <small>(m1-4-expert)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.4.1</b></td>
			<td style="padding-left:20px"><b>Quality</b> <small>(m1-4-1-quality)</small>
				<ul type="square"><xsl:apply-templates select="//m1-4-1-quality/leaf | //m1-4-1-quality/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.4.2</b></td>
			<td style="padding-left:20px"><b>Non-Clinical</b> <small>(m1-4-2-non-clinical)</small>
				<ul type="square"><xsl:apply-templates select="//m1-4-2-non-clinical/leaf | //m1-4-2-non-clinical/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.4.3</b></td>
			<td style="padding-left:20px"><b>Clinical</b> <small>(m1-4-3-clinical)</small>
				<ul type="square"><xsl:apply-templates select="//m1-4-3-clinical/leaf | //m1-4-3-clinical/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.5</b></td>
			<td style="padding-left:4px"><b>Specific Requirements for Different Types of Applications</b> <small>(m1-5-specific)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.5.1</b></td>
			<td style="padding-left:20px"><b>Information for Bibliographical Applications</b> <small>(m1-5-1-bibliographic)</small>
				<ul type="square"><xsl:apply-templates select="//m1-5-1-bibliographic/leaf | //m1-5-1-bibliographic/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.5.2</b></td>
			<td style="padding-left:20px"><b>Information for Generic, Hybrid' or Bio-similar Applications</b> <small>(m1-5-2-generic-hybrid-bio-similar)</small>
				<ul type="square"><xsl:apply-templates select="//m1-5-2-generic-hybrid-bio-similar/leaf | //m1-5-2-generic-hybrid-bio-similar/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.5.3</b></td>
			<td style="padding-left:20px"><b>(Extended) Data/Market Exclusivity</b> <small>(m1-5-3-data-market-exclusivity)</small>
				<ul type="square"><xsl:apply-templates select="//m1-5-3-data-market-exclusivity/leaf | //m1-5-3-data-market-exclusivity/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.5.4</b></td>
			<td style="padding-left:20px"><b>Exceptional Circumstances</b> <small>(m1-5-4-exceptional-circumstances)</small>
				<ul type="square"><xsl:apply-templates select="//m1-5-4-exceptional-circumstances/leaf | //m1-5-4-exceptional-circumstances/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.5.5</b></td>
			<td style="padding-left:20px"><b>Conditional Marketing Authorisation</b> <small>(m1-5-5-conditional-ma)</small>
				<ul type="square"><xsl:apply-templates select="//m1-5-5-conditional-ma/leaf | //m1-5-5-conditional-ma/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.6</b></td>
			<td style="padding-left:4px"><b>Environmental Risk Assessment</b> <small>(m1-6-environrisk)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.6.1</b></td>
			<td style="padding-left:20px"><b>Non-GMO</b> <small>(m1-6-1-non-gmo)</small>
				<ul type="square"><xsl:apply-templates select="//m1-6-1-non-gmo/leaf | //m1-6-1-non-gmo/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.6.2</b></td>
			<td style="padding-left:20px"><b>GMO</b> <small>(m1-6-2-gmo)</small>
				<ul type="square"><xsl:apply-templates select="//m1-6-2-gmo/leaf | //m1-6-2-gmo/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.7</b></td>
			<td style="padding-left:4px"><b>Information relating to Orphan Market Exclusivity</b> <small>(m1-7-orphan)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.7.1</b></td>
			<td style="padding-left:20px"><b>Similarity</b> <small>(m1-7-1-similarity)</small>
				<ul type="square"><xsl:apply-templates select="//m1-7-1-similarity/leaf | //m1-7-1-similarity/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.7.2</b></td>
			<td style="padding-left:20px"><b>Market Exclusivity</b> <small>(m1-7-2-market-exclusivity)</small>
				<ul type="square"><xsl:apply-templates select="//m1-7-2-market-exclusivity/leaf | //m1-7-2-market-exclusivity/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.8</b></td>
			<td style="padding-left:4px"><b>Information relating to Pharmacovigilance</b> <small>(m1-8-pharmacovigilance)</small>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.8.1</b></td>
			<td style="padding-left:20px"><b>Pharmacovigilance System</b> <small>(m1-8-1-pharmacovigilance-system)</small>
				<ul type="square"><xsl:apply-templates select="//m1-8-1-pharmacovigilance-system/leaf | //m1-8-1-pharmacovigilance-system/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.8.2</b></td>
			<td style="padding-left:20px"><b>Risk-management System</b> <small>(m1-8-2-risk-management-system)</small>
				<ul type="square"><xsl:apply-templates select="//m1-8-2-risk-management-system/leaf | //m1-8-2-risk-management-system/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.9</b></td>
			<td style="padding-left:4px"><b>Information relating to Clinical Trials</b> <small>(m1-9-clinical-trials)</small>
				<ul type="square"><xsl:apply-templates select="//m1-9-clinical-trials/leaf | //m1-9-clinical-trials/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b>1.10</b></td>
			<td style="padding-left:4px"><b>Information relating to Paediatrics</b> <small>(m1-10-paediatrics)</small>
				<ul type="square"><xsl:apply-templates select="//m1-10-paediatrics/leaf | //m1-10-paediatrics/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b></b></td>
			<td style="padding-left:4px"><b>Responses to Questions</b> <small>(m1-responses)</small>
				<ul type="square"><xsl:apply-templates select="//m1-responses/leaf | //m1-responses/node-extension"/></ul>
			</td>
		</tr>
		<tr>
			<td valign="top" width="9%"><b></b></td>
			<td style="padding-left:4px"><b>Additional Data</b> <small>(m1-additional-data)</small>
				<ul type="square"><xsl:apply-templates select="//m1-additional-data/leaf | //m1-additional-data/node-extension"/></ul>
			</td>
		</tr>
		</table>
		</center>
	</xsl:template>
</xsl:stylesheet>
