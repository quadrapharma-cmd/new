"""The names the documents and folders of a CTD take (ICH M4 titles, written for file names: «/» as «-»), and the document level
of each module: the CTD number a document is filed under."""
import re

S_TITLES = {
    '3.2.S.1.1': 'Nomenclature', '3.2.S.1.2': 'Structure', '3.2.S.1.3': 'General properties',
    '3.2.S.2.1': 'Manufacturer(s)', '3.2.S.2.2': 'Description of manufacturing process and process controls',
    '3.2.S.2.3': 'Control of materials', '3.2.S.2.4': 'Controls of critical steps and intermediates',
    '3.2.S.2.5': 'Process validation and-or evaluation', '3.2.S.2.6': 'Manufacturing process development',
    '3.2.S.3.1': 'Elucidation of structure and other characteristics', '3.2.S.3.2': 'Impurities',
    '3.2.S.4.1': 'Specification', '3.2.S.4.2': 'Analytical procedures', '3.2.S.4.3': 'Validation of analytical procedures',
    '3.2.S.4.4': 'Batch analyses', '3.2.S.4.5': 'Justification of specification',
    '3.2.S.5': 'Reference standards or materials', '3.2.S.6': 'Container closure system',
    '3.2.S.7.1': 'Stability summary and conclusions', '3.2.S.7.2': 'Post-approval stability protocol and stability commitment',
    '3.2.S.7.3': 'Stability data',
}
S_GROUP = {'3.2.S.1': '3.2.S.1 General information', '3.2.S.2': '3.2.S.2 Manufacture', '3.2.S.3': '3.2.S.3 Characterisation',
           '3.2.S.4': '3.2.S.4 Control of drug substance', '3.2.S.5': '3.2.S.5 Reference standards or materials',
           '3.2.S.6': '3.2.S.6 Container closure system', '3.2.S.7': '3.2.S.7 Stability'}
P_TITLES = {
    '3.2.P.1': 'Description and composition of the drug product',
    '3.2.P.2.1': 'Components of the drug product', '3.2.P.2.2': 'Drug product', '3.2.P.2.3': 'Manufacturing process development',
    '3.2.P.2.4': 'Container closure system', '3.2.P.2.5': 'Microbiological attributes', '3.2.P.2.6': 'Compatibility',
    '3.2.P.3.1': 'Manufacturer(s)', '3.2.P.3.2': 'Batch formula', '3.2.P.3.3': 'Description of manufacturing process and process controls',
    '3.2.P.3.4': 'Controls of critical steps and intermediates', '3.2.P.3.5': 'Process validation and-or evaluation',
    '3.2.P.4.1': 'Specifications', '3.2.P.4.2': 'Analytical procedures', '3.2.P.4.3': 'Validation of analytical procedures',
    '3.2.P.4.4': 'Justification of specifications', '3.2.P.4.5': 'Excipients of human or animal origin', '3.2.P.4.6': 'Novel excipients',
    '3.2.P.5.1': 'Specification(s)', '3.2.P.5.2': 'Analytical procedures', '3.2.P.5.3': 'Validation of analytical procedures',
    '3.2.P.5.4': 'Batch analyses', '3.2.P.5.5': 'Characterisation of impurities', '3.2.P.5.6': 'Justification of specification(s)',
    '3.2.P.6': 'Reference standards or materials', '3.2.P.7': 'Container closure system',
    '3.2.P.8.1': 'Stability summary and conclusion', '3.2.P.8.2': 'Post-approval stability protocol and stability commitment',
    '3.2.P.8.3': 'Stability data',
}
P_GROUP = {'3.2.P.1': '3.2.P.1 Description and composition', '3.2.P.2': '3.2.P.2 Pharmaceutical development', '3.2.P.3': '3.2.P.3 Manufacture',
           '3.2.P.4': '3.2.P.4 Control of excipients', '3.2.P.5': '3.2.P.5 Control of drug product', '3.2.P.6': '3.2.P.6 Reference standards or materials',
           '3.2.P.7': '3.2.P.7 Container closure system', '3.2.P.8': '3.2.P.8 Stability'}
A_TITLES = {'3.2.A.1': 'Facilities and equipment', '3.2.A.2': 'Adventitious agents safety evaluation', '3.2.A.3': 'Novel excipients'}
M2_TITLES = {'2.1': 'CTD table of contents (Modules 2-5)', '2.2': 'CTD introduction', '2.4': 'Nonclinical overview',
             '2.5': 'Clinical overview', '2.6': 'Nonclinical written and tabulated summaries', '2.7': 'Clinical summary'}
M4_TITLES = {'4.1': 'Table of contents of Module 4', '4.2.1': 'Pharmacology', '4.2.2': 'Pharmacokinetics',
             '4.2.3.1': 'Single-dose toxicity', '4.2.3.2': 'Repeat-dose toxicity', '4.2.3.3': 'Genotoxicity', '4.2.3.4': 'Carcinogenicity',
             '4.2.3.5': 'Reproductive and developmental toxicity', '4.2.3.6': 'Local tolerance', '4.2.3.7': 'Other toxicity studies',
             '4.3': 'Literature references'}
M5_TITLES = {'5.1': 'Table of contents of Module 5', '5.2': 'Tabular listing of all clinical studies',
             '5.3.1': 'Reports of biopharmaceutic studies', '5.3.2': 'Reports of studies pertinent to pharmacokinetics using human biomaterials',
             '5.3.3': 'Reports of human pharmacokinetic (PK) studies', '5.3.4': 'Reports of human pharmacodynamic (PD) studies',
             '5.3.5.1': 'Study reports of controlled clinical studies', '5.3.5.2': 'Study reports of uncontrolled clinical studies',
             '5.3.5.3': 'Analyses of data from more than one study', '5.3.5.4': 'Other study reports',
             '5.3.6': 'Reports of post-marketing experience', '5.3.7': 'Case report forms and individual patient listings',
             '5.4': 'Literature references'}
M1EU_TITLES = {'1.0': 'Cover letter', '1.1': 'Comprehensive table of contents', '1.2': 'Application form',
               '1.3.1': 'SPC, labelling and package leaflet', '1.3.2': 'Mock-ups', '1.3.3': 'Specimen',
               '1.3.4': 'Consultation with target patient groups', '1.3.5': 'Product information already approved in member states',
               '1.3.6': 'Braille', '1.4.1': 'Information about the experts - quality', '1.4.2': 'Information about the experts - non-clinical',
               '1.4.3': 'Information about the experts - clinical', '1.5': 'Specific requirements for different types of applications',
               '1.6': 'Environmental risk assessment', '1.7': 'Orphan market exclusivity', '1.8': 'Pharmacovigilance',
               '1.9': 'Information relating to clinical trials', '1.10': 'Additional data'}
TOC = {'1': ('1.0', 'Module 1 table of contents'), '2': ('2.1', M2_TITLES['2.1']), '3': ('3.1', 'Table of contents of Module 3'),
       '4': ('4.1', M4_TITLES['4.1']), '5': ('5.1', M5_TITLES['5.1'])}
NUMBER_WORDS = {2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six', 7: 'seven', 8: 'eight', 9: 'nine'}


def parts(key):
    return key.split('.')


def doc_key(key):
    """The CTD number a document under heading `key` is filed under, or None when `key` names a group of documents."""
    if not key:
        return None
    k = key.split('.')
    m = k[0]
    if m == '3':
        if key in ('3.1', '3.3', '3.2.R') or key.startswith('3.2.R.'):
            return '3.2.R' if key.startswith('3.2.R') else key
        for table in (S_TITLES, P_TITLES, A_TITLES):
            for n in range(len(k), 2, -1):
                if '.'.join(k[:n]) in table:
                    return '.'.join(k[:n])
        return None
    if m == '2':
        if len(k) >= 3 and k[1] == '3' and k[2] in ('S', 'P', 'A', 'R'):
            return '.'.join(k[:3])
        if key == '2.3':
            return '2.3'
        return '.'.join(k[:2]) if len(k) >= 2 and k[1] in '1245678' else None
    if m == '4':
        if key == '4.1' or key.startswith('4.1.') or key == '4.3' or key.startswith('4.3.'):
            return key[:3]
        if len(k) >= 3 and k[1] == '2' and k[2] in ('1', '2'):
            return '.'.join(k[:3])
        if len(k) >= 4 and k[1] == '2' and k[2] == '3':
            return '.'.join(k[:4])
        return None
    if m == '5':
        if key[:3] in ('5.1', '5.2', '5.4'):
            return key[:3]
        if len(k) >= 3 and k[1] == '3':
            if k[2] == '5':
                return '.'.join(k[:4]) if len(k) >= 4 else None
            return '.'.join(k[:3])
        return None
    if m == '1':
        if len(k) >= 3 and k[1] in ('3', '4'):
            return '.'.join(k[:3])
        if len(k) >= 2 and k[1] not in ('3', '4'):
            return '.'.join(k[:2])
        return None
    return None


ORDER_LETTER = {'S': 1, 'P': 2, 'A': 3, 'R': 4}


def order(key):
    """A sortable form of a CTD number: 3.2.S.4.1 → (3, 2, 1, 4, 1)."""
    out = []
    for x in key.split('.'):
        out.append(int(x) if x.isdigit() else ORDER_LETTER.get(x, 9))
    return tuple(out)


def is_under(key, group):
    return key == group or key.startswith(group + '.')


def norm_words(s):
    return [w for w in re.findall(r'[a-z]+', s.lower()) if w not in ('the', 'of', 'and', 'or', 's', 'a', 'an')]
