// Safe access to the engine barrel (src/engine/index.js, owned by the engine owner).
// The barrel may be an empty placeholder while the engine is being built: nothing here may break the build or the page.
import * as engineNS from '../engine/index.js';

export const engine = engineNS;

/** Returns the exported engine function, or null when it does not exist (yet). */
export function engineFn(name) {
  const f = engineNS[name];
  return typeof f === 'function' ? f : null;
}

const SEV = (s) => {
  const v = String(s || '').toLowerCase();
  if (/err|crit|fail|high/.test(v)) return 'error';
  if (/info|note/.test(v)) return 'info';
  return 'warning';
};
const asIssue = (x, forced) => {
  const o = typeof x === 'string' ? { message: x } : x || {};
  return {
    severity: forced || SEV(o.severity || o.level || o.type),
    code: o.code || o.rule || o.check || '',
    message: o.message || o.msg || o.text || o.summary || JSON.stringify(o),
    ref: o.ref || o.where || o.entryNo || o.entry || o.id || o.acct || '',
  };
};

/** Normalise whatever checkIntegrity returns into { issues:[{severity,code,message,ref}], errors, warnings }. */
export function normalizeIntegrity(raw) {
  let issues = [];
  if (Array.isArray(raw)) issues = raw.map((x) => asIssue(x));
  else if (raw && Array.isArray(raw.issues)) issues = raw.issues.map((x) => asIssue(x));
  else if (raw && (Array.isArray(raw.errors) || Array.isArray(raw.warnings))) {
    issues = [...(raw.errors || []).map((x) => asIssue(x, 'error')), ...(raw.warnings || []).map((x) => asIssue(x, 'warning'))];
  } else if (raw && Array.isArray(raw.checks)) {
    issues = raw.checks.filter((c) => c && c.ok === false).map((c) => asIssue({ ...c, message: c.message || c.name }, 'error'));
  }
  return {
    issues,
    errors: issues.filter((i) => i.severity === 'error').length,
    warnings: issues.filter((i) => i.severity === 'warning').length,
  };
}
