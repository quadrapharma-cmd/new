// Shared esbuild options for the single-file bundle (used by scripts/build.mjs and dev/serve.mjs).
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = dirname(fileURLToPath(import.meta.url));
export const ENTRY = resolve(ROOT, 'src/ui/main.jsx');

/**
 * Modules owned by other engineers. While they do not exist yet the build must still pass,
 * so a tiny stub from dev/stubs/ is used instead. As soon as the real file is created it wins
 * automatically (the check runs on every build). The build prints which stubs were used.
 */
export const OPTIONAL_MODULES = {
  'src/lib/money.js': 'dev/stubs/money.js',
  'src/lib/dates.js': 'dev/stubs/dates.js',
};

export const usedStubs = new Set();

function fallbackPlugin() {
  return {
    name: 'strifa-optional-modules',
    setup(build) {
      build.onResolve({ filter: /(^|\/)(money|dates)\.js$/ }, (args) => {
        if (!args.path.startsWith('.')) return null;
        const abs = resolve(args.resolveDir, args.path);
        for (const [real, stub] of Object.entries(OPTIONAL_MODULES)) {
          if (abs === resolve(ROOT, real) && !existsSync(abs)) {
            usedStubs.add(real);
            return { path: resolve(ROOT, stub) };
          }
        }
        return null;
      });
    },
  };
}

export function bundleOptions({ minify = true, sourcemap = false, entry = ENTRY } = {}) {
  return {
    entryPoints: [entry],
    bundle: true,
    write: false,
    format: 'iife',
    platform: 'browser',
    target: ['es2020'],
    jsx: 'automatic',
    jsxImportSource: 'preact',
    loader: { '.js': 'js', '.jsx': 'jsx' },
    mainFields: ['browser', 'module', 'main'],
    define: { 'process.env.NODE_ENV': '"production"', global: 'globalThis' },
    legalComments: 'none',
    charset: 'utf8',
    minify,
    sourcemap,
    logLevel: 'warning',
    plugins: [fallbackPlugin()],
  };
}
