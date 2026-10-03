import test from 'node:test';
import assert from 'node:assert/strict';
import { assemble } from '../../scripts/build.mjs';

// Contract of the published page (hard rules of the platform): see AGENTS.md.
test('built page honours the platform contract', async () => {
  const { html, js, css } = await assemble({ minify: true });
  assert.ok(html.startsWith('<title>نظام ستريفا المحاسبي</title>\n<style>'), 'title first, then style');
  assert.ok(!/<!doctype|<html|<head|<body/i.test(html), 'page content only: no document skeleton tags');
  assert.ok(html.includes('<div id="root" dir="rtl" lang="ar">'));
  assert.ok(Buffer.byteLength(html) < 12 * 1024 * 1024);
  // the only </script is the closing tag of the single inline script
  assert.equal((html.match(/<\/script/gi) || []).length, 1);
  assert.equal((html.match(/<script/gi) || []).length, 1);
  assert.ok(!/<!--/.test(js));
  // external resources: Google Fonts only
  const urls = [...html.matchAll(/(?:href|src)="(https?:[^"]+)"/g)].map((m) => new URL(m[1]).host);
  assert.deepEqual([...new Set(urls)].sort(), ['fonts.googleapis.com', 'fonts.gstatic.com']);
  // forbidden runtime features (code we wrote; third-party bundles are checked separately by the build lint)
  for (const re of [/\balert\(/, /\bwindow\.print\(/, /\bnew Function\(/, /\beval\(/, /serviceWorker/, /mailto:/]) {
    assert.ok(!re.test(js), `bundle must not contain ${re}`);
  }
  // theme tokens: defined on bare :root first, then the two dark blocks, body background from a token
  assert.match(css, /^:root\{[^}]*--bg:/);
  assert.match(css, /@media ?\(prefers-color-scheme: ?dark\)\{:root:not\(\[data-theme="?light"?\]\)\{/, 'media dark block guarded by :root:not([data-theme=light])');
  assert.match(css, /:root\[data-theme="?dark"?\]\{/);
  assert.ok((css.match(/color-scheme:dark/g) || []).length >= 2);
  assert.match(css, /body\{[^}]*background:var\(--bg\)/);
  assert.match(css, /\[hidden\]\{display:none!important\}/);
  assert.match(css, /prefers-reduced-motion:reduce/);
  assert.match(css, /safe-area-inset-top/);
  // every colour literal outside tokens: none in component rules (all colours come from tokens)
  const rules = css.replace(/^:root\{[^}]*\}/, '').replace(/@media ?\(prefers-color-scheme: ?dark\)\{:root:not\(\[data-theme="?light"?\]\)\{[^}]*\}\}/, '').replace(/:root\[data-theme="?dark"?\]\{[^}]*\}/, '');
  const literals = rules.match(/#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)/g) || [];
  assert.deepEqual(literals, [], 'component CSS must not use literal colours');
});
