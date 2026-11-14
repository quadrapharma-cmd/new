// Packs the bridge as an extension for the Claude app on a computer (an MCP Bundle, .mcpb: a zip with manifest.json at its root,
// manifest version 0.3). The Claude app runs it with its own Node.js; the user picks the dossier folder when installing it.
//   node bridge/pack.mjs [out.mcpb]     (default dist/Dossier-Builder.mcpb; needs dist/knowledge.json — npm run build)
// Inside: manifest.json, and server/ with the bridge, the tool layer, the parts of core/ they use, the library's data and pdf.js
// (Apache-2.0, its licence beside it).
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { TOOLS } from '../agent/tools.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PKG = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf8'));
const PDFJS = path.join(ROOT, 'node_modules', 'pdfjs-dist');

const SERVER_FILES = ['bridge/mcp.mjs', 'agent/agent.js', 'agent/schema.js', 'agent/tools.js', 'agent/workspace.js',
                      'core/fold.js', 'core/search.js', 'core/knowledge.js', 'core/validate.js', 'core/pdftext.js'];

export function manifest() {
  return {
    manifest_version: '0.3',
    name: 'dossier-builder',
    display_name: 'Dossier Builder',
    version: PKG.version,
    description: 'Prepare a medicine registration dossier with Claude: read its files, search them and the authorities\' requirements, and record facts with the words that hold them.',
    long_description: 'Dossier Builder\'s tools over one dossier folder on this computer. Its files are read, never changed. The library holds the requirements of the Egyptian Drug Authority, ICH, the EU, the GCC and others, each with its source.',
    author: { name: 'Dossier Builder' },
    server: {
      type: 'node',
      entry_point: 'server/bridge/mcp.mjs',
      mcp_config: { command: 'node', args: ['${__dirname}/server/bridge/mcp.mjs', '--root', '${user_config.dossier_folder}'] },
    },
    user_config: {
      dossier_folder: { type: 'directory', title: 'Dossier folder', description: 'The folder that holds the dossier\'s files. They are read, never changed.', required: true },
    },
    tools: TOOLS.map(t => ({ name: t.name, description: t.description })),
    compatibility: { platforms: ['darwin', 'win32'], runtimes: { node: '>=18.0.0' } },
  };
}

export function pack(out = path.join(ROOT, 'dist', 'Dossier-Builder.mcpb')) {
  const knowledge = path.join(ROOT, 'dist', 'knowledge.json');
  if (!fs.existsSync(knowledge)) throw new Error('dist/knowledge.json is missing: run npm run build first');
  const stage = fs.mkdtempSync(path.join(os.tmpdir(), 'dbk-mcpb-'));
  try {
    const put = (from, to) => { fs.mkdirSync(path.dirname(path.join(stage, to)), { recursive: true }); fs.copyFileSync(from, path.join(stage, to)); };
    fs.writeFileSync(path.join(stage, 'manifest.json'), JSON.stringify(manifest(), null, 2));
    for (const f of SERVER_FILES) put(path.join(ROOT, f), `server/${f}`);
    put(knowledge, 'server/dist/knowledge.json');
    fs.writeFileSync(path.join(stage, 'server', 'package.json'), JSON.stringify({ name: 'dossier-builder-bridge', version: PKG.version, private: true, type: 'module' }, null, 2));
    for (const f of ['package.json', 'LICENSE', 'legacy/build/pdf.mjs', 'legacy/build/pdf.worker.mjs']) put(path.join(PDFJS, f), `server/node_modules/pdfjs-dist/${f}`);
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.rmSync(out, { force: true });
    execFileSync('zip', ['-r', '-X', '-q', path.resolve(out), 'manifest.json', 'server'], { cwd: stage });
  } finally { fs.rmSync(stage, { recursive: true, force: true }); }
  return out;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const out = pack(process.argv[2]);
  console.log(`${path.relative(process.cwd(), out)}: ${(fs.statSync(out).size / 1048576).toFixed(1)} MB`);
}
