// The arithmetic the preparation checks show the user, never hide: a substance named in one hydrate or salt form in one document
// and another form in the next («citric acid monohydrate 11 g» in the licence, «citric acid anhydrous 10.06 g» in the
// specification) is the same amount when the two masses stand in the ratio of the forms' molecular weights. The molecular weights
// come from the formulas below and the IUPAC standard atomic weights (abridged, 2021); the finding prints the formulas and the sum.
const ATOMS = { H: 1.008, C: 12.011, N: 14.007, O: 15.999, Na: 22.990, Mg: 24.305, P: 30.974, S: 32.06, Cl: 35.45, K: 39.098, Ca: 40.078,
                Fe: 55.845, Zn: 65.38, Br: 79.904, I: 126.90 };
const WATER = 2 * ATOMS.H + ATOMS.O;

// Anhydrous formulas of substances the checks meet (more are added as dossiers need them).
export const FORMULAS = {
  'citric acid': 'C6H8O7', 'ascorbic acid': 'C6H8O6', 'sodium picosulfate': 'C18H13NNa2O8S2', 'magnesium oxide': 'MgO',
  'light magnesium oxide': 'MgO', 'paracetamol': 'C8H9NO2', 'sodium citrate': 'C6H5Na3O7', 'lactose': 'C12H22O11',
  'glucose': 'C6H12O6', 'dextrose': 'C6H12O6', 'calcium carbonate': 'CaCO3', 'ferrous sulfate': 'FeSO4', 'zinc sulfate': 'ZnSO4',
};
// Other names of the same substance, as documents write them (the first is the name the checks use).
export const SYNONYMS = [['ascorbic acid', 'vitamin c'], ['paracetamol', 'acetaminophen'], ['dextrose', 'glucose'],
                         ['sodium picosulfate', 'sodium picosulphate'], ['ferrous sulfate', 'ferrous sulphate'], ['zinc sulfate', 'zinc sulphate']];
export const namesOf = name => SYNONYMS.find(g => g.includes(name)) || [name];
const HYDRATES = { anhydrous: 0, hemihydrate: 0.5, monohydrate: 1, sesquihydrate: 1.5, dihydrate: 2, trihydrate: 3, tetrahydrate: 4,
                   pentahydrate: 5, hexahydrate: 6, heptahydrate: 7 };

export function molarMass(formula) {
  let m = 0;
  for (const [, el, n] of formula.matchAll(/([A-Z][a-z]?)(\d*)/g)) {
    if (!ATOMS[el]) throw new Error(`no atomic weight for ${el}`);
    m += ATOMS[el] * (n ? Number(n) : 1);
  }
  return m;
}

// «Citric Acid Monohydrate» → {base: 'citric acid', water: 1, form: 'monohydrate'}; a name without a form is the plain substance.
export function formOf(name) {
  const n = String(name).toLowerCase().replace(/\s+/g, ' ').trim();
  for (const [form, water] of Object.entries(HYDRATES)) {
    const at = n.search(new RegExp(`\\b${form}\\b`));
    if (at >= 0) return { base: (n.slice(0, at) + n.slice(at + form.length)).replace(/\s+/g, ' ').trim(), water, form };
  }
  return { base: n, water: null, form: null };
}

// The mass of `from` (a form and an amount) expressed as the other form: null when the substance's formula is not known.
export function convert(fromName, amount, toName) {
  const a = formOf(fromName), b = formOf(toName);
  if (a.base !== b.base || !FORMULAS[a.base]) return null;
  const base = molarMass(FORMULAS[a.base]);
  const ma = base + (a.water || 0) * WATER, mb = base + (b.water || 0) * WATER;
  return { amount: amount * mb / ma, ratio: `${mb.toFixed(2)} ÷ ${ma.toFixed(2)}`, formula: FORMULAS[a.base], from: a, to: b,
           mFrom: ma, mTo: mb };
}
