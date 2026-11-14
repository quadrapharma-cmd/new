// The part of JSON Schema the tools' inputs use, checked before a tool runs: whatever Claude sends, a tool only ever sees input
// of the shape it declares. check(schema, value) → a list of plain-English problems (empty when the input is good).
const TYPES = {
  string: v => typeof v === 'string',
  integer: v => Number.isInteger(v),
  number: v => typeof v === 'number' && Number.isFinite(v),
  boolean: v => typeof v === 'boolean',
  array: v => Array.isArray(v),
  object: v => v !== null && typeof v === 'object' && !Array.isArray(v),
};

export function check(schema, value, at = 'input') {
  const out = [];
  if (!schema) return out;
  if (schema.type && !TYPES[schema.type]?.(value)) return [`${at} must be ${schema.type === 'integer' ? 'a whole number' : `a ${schema.type}`}`];
  if (schema.enum && !schema.enum.includes(value)) out.push(`${at} must be one of: ${schema.enum.join(', ')}`);
  if (typeof value === 'string') {
    if (schema.minLength != null && value.length < schema.minLength) out.push(`${at} is too short (at least ${schema.minLength} characters)`);
    if (schema.maxLength != null && value.length > schema.maxLength) out.push(`${at} is too long (at most ${schema.maxLength} characters)`);
  }
  if (typeof value === 'number') {
    if (schema.minimum != null && value < schema.minimum) out.push(`${at} must be at least ${schema.minimum}`);
    if (schema.maximum != null && value > schema.maximum) out.push(`${at} must be at most ${schema.maximum}`);
  }
  if (Array.isArray(value)) {
    if (schema.maxItems != null && value.length > schema.maxItems) out.push(`${at} has more than ${schema.maxItems} items`);
    if (schema.items) value.forEach((v, i) => out.push(...check(schema.items, v, `${at}[${i}]`)));
  }
  if (TYPES.object(value) && schema.type === 'object') {
    for (const k of schema.required || []) if (value[k] === undefined) out.push(`${at}.${k} is missing`);
    for (const [k, v] of Object.entries(value)) {
      if (schema.properties?.[k]) out.push(...check(schema.properties[k], v, `${at}.${k}`));
      else if (schema.additionalProperties === false) out.push(`${at}.${k} is not an input of this tool`);
    }
  }
  return out;
}
