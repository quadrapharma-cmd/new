// The payer's name as Paymob and Fawry want it (B-25): first and last name WITHOUT a title. A Drugbox name often starts with one
// ("Dr. Mona El-Sayed", "د. منى السيد", "Eng. Omar Khaled", "أ.د. هالة") and may end with a degree ("(Pharm.D.)", "PhD"): Paymob's
// billing_data.first_name used to be "Dr." / "د.". Titles at the start and degrees at the end are left out; a name made only of
// them is kept as it is (never an empty name).
const TITLES = new Set(['dr', 'doctor', 'prof', 'professor', 'eng', 'engr', 'engineer', 'pharm', 'pharmacist', 'chem', 'mr', 'mrs', 'ms', 'miss', 'mx', 'sir', 'dame',
  'rev', 'capt', 'col', 'gen', 'hon', 'assoc', 'asst', 'sheikh', 'sh',
  'د', 'دكتور', 'دكتورة', 'الدكتور', 'الدكتورة', 'أد', 'اد', 'أ', 'ا', 'م', 'مهندس', 'مهندسة', 'المهندس', 'المهندسة', 'ص', 'صيدلي', 'صيدلانية', 'الصيدلي',
  'الصيدلانية', 'أستاذ', 'أستاذة', 'الأستاذ', 'الأستاذة', 'السيد', 'السيدة', 'الشيخ', 'ش']);
const DEGREES = new Set(['phd', 'pharmd', 'md', 'msc', 'bsc', 'mba', 'bpharm', 'mpharm', 'rph']);
const bare = (w) => w.toLowerCase().replace(/[.’',()]/g, '');
export function billingName(name) {
  const all = String(name || '').replace(/\([^)]*\)/g, ' ').split(/\s+/).filter(Boolean);
  let w = all.slice();
  while (w.length > 1 && TITLES.has(bare(w[0]))) w.shift();
  while (w.length > 1 && DEGREES.has(bare(w[w.length - 1]))) w.pop();
  if (!w.length || (w.length === 1 && TITLES.has(bare(w[0])))) w = all.length ? all : ['Drugbox', 'Member'];
  return { first: w[0], last: w.slice(1).join(' ') || 'NA', full: w.join(' ') };
}
