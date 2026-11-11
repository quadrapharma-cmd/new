"""The active substances of a form are the run of «name amount unit» lines under their label — not the cells printed after them
(appearance, shelf life, pack, price), not the composition table's headings, not OCR fragments. Layouts as real registration
notifications, pricing letters and leaflets print them; the product and its substances here are made up."""
from dossier_engine import extract as X, intake_eda as E

FORM = '''Egyptian Drug Authority
Trade Name: Dermacure
Dosage Form: Topical Powder
Active Ingredient(s) & Strength(s): Each 1g contains:
MICONAZOLE NITRATE 20.000 mg (2 Percent)
Hydrocortisone Acetate 10.000 mg (1 Percent) ZINC OXIDE 150.000 mg
ALLANTOIN; 5.000 mg
PANTHENOL Img
White homogenous powder
36 Months
Store at a temperature not exceeding 30C in dry place
White opaque plastic (HDPE) jar containing 10 g or 20 g powder covered with plastic (HDPE) cap with insert leaflet
34 L.E./1 Box/ 1 Bottle/10 Gm
QUADR
Ingredient
Active Ingredients
Miconazole Nitrate (Equivalent to 2 Percent)
Hydrocortisone Acetate (Equivalent to 1 Percent)
Allantoin
Specification
Quantity
20 mg
BP2018
gistra
Inactive Ingredients
maize starch
BP2018
815 mg
Chief Executive Officer/ Dr. Example Person
Registration No.: 12345/2022
License Holder: Example Pharma, EGYPT
'''
WANT = [('Miconazole Nitrate', '20.000 mg'), ('Hydrocortisone Acetate', '10.000 mg'), ('Zinc Oxide', '150.000 mg'), ('Allantoin', '5.000 mg'), ('Panthenol', '1 mg')]


def pairs(apis):
    return [(a['name'].title(), a.get('strength')) for a in apis]


def test_only_the_dosed_run_under_the_label_is_read():
    assert pairs(E.read(FORM)['apis']) == WANT
    rules = X.read_texts([{'filename': 'registration notification.pdf', 'text': FORM}])['rules']
    assert pairs(rules['apis']) == WANT                                    # nothing from the cells and the table printed after them
    assert rules['product']['name'] == 'Dermacure'


def test_pricing_letter_row_with_trailing_labels_and_a_pack_line():
    text = '''Pricing Administration
Dermacure Topical Powder Trade Name
Each Ig Powder Contains:
Miconazole Nitrate 20mg 2 Percent) +Hydrocortisone Acetate 10mg Generic Name
(1Percent) +Zinc Oxide 150mg + Allantoin 5mg + Panthenol Img
Carton box containing Plastic Bottle of 10 g Dusting Powder & an inner leaflet Unit
27,00 LE Unit Price Number of Units
'''
    apis = E.read(text)['apis']
    assert [a['name'].title() for a in apis] == ['Miconazole Nitrate', 'Hydrocortisone Acetate', 'Zinc Oxide', 'Allantoin', 'Panthenol']
    assert apis[-1]['strength'] == '1 mg'                                  # «Img» is OCR for «1mg»; the pack line is not a substance


def test_leaflet_sentence_with_equivalents_and_no_headings():
    text = '''SUMMARY OF PRODUCT CHARACTERISTICS
1. NAME OF THE MEDICINAL PRODUCT
DERMACURE topical powder
2. QUALITATIVE AND QUANTITATIVE COMPOSITION
Each 1 g of powder contains Miconazole nitrate 20 mg (equivalent to 2 Percent), Hydrocortisone acetate 10 mg (equivalent to 1 Percent), Zinc oxide 150 mg
For full list of excipients, see section 6.1
3. PHARMACEUTICAL FORM
Powder for cutaneous use
White, homogeneous powder
4. CLINICAL PARTICULARS
4.1 Therapeutic indications
Nappy rash
4.6 Pregnancy and lactation
No information is available regarding the excretion of the active ingredients in human milk.
'''
    rules = X.read_texts([{'filename': 'smpc.docx', 'text': text}])['rules']
    assert [a['name'] for a in rules['apis']] == ['Miconazole nitrate', 'Hydrocortisone acetate', 'Zinc oxide']


def test_a_label_is_a_field_not_a_word_in_a_sentence():
    assert X.read_texts([{'filename': 'note.pdf', 'text': 'Safety note\nNo information is available regarding the excretion of the active ingredients in human milk.'}])['rules']['apis'] == []
    one = X.read_texts([{'filename': 'cpp.pdf', 'text': 'Certificate of a Pharmaceutical Product\nTrade name: Dermacure\nActive ingredient: Bisoprolol fumarate\n'}])['rules']['apis']
    assert [a['name'] for a in one] == ['Bisoprolol fumarate']


def test_labels_printed_as_a_column_are_not_values():
    text = 'Trade Name:\n\nDosage Form:\n\nActive Ingredient(s) & Strength(s):\n\nDermacure\n\nTopical Powder\n\nEach 1g contains:\n\nMICONAZOLE NITRATE 20.000 mg\n'
    p = X.read_texts([{'filename': 'form.pdf', 'text': text}])['rules']['product']
    assert p.get('name') != 'Dosage Form' and 'Active Ingredient' not in (p.get('dosage_form') or '')


def test_a_name_alone_counts_only_when_no_amount_is_printed():
    apis, _ = E.actives(['Bisoprolol fumarate', 'Tablets', 'Blister'])
    assert [a['name'] for a in apis] == ['Bisoprolol fumarate']
    apis, _ = E.actives(['Each tablet contains:', 'Bisoprolol fumarate 10 mg', 'Yellow round tablet', 'Lactose'])
    assert [(a['name'], a['strength']) for a in apis] == [('Bisoprolol fumarate', '10 mg')]
