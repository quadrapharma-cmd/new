#!/usr/bin/env node
// The bridge: the program's tools (agent/tools.js) as an MCP server, for the Claude app on the user's computer (a Desktop
// Extension) and for Claude Code. It speaks MCP over standard input and output — one JSON-RPC message per line — and works on one
// dossier folder on this computer, which the user chooses: its files are read, never changed.
//   node bridge/mcp.mjs --root <dossier folder> [--knowledge <knowledge.json>]
// Nothing but MCP messages is written to standard output (pdf.js and our own notes go to standard error).
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import { fileURLToPath } from 'node:url';
import { createWorkspace } from '../agent/workspace.js';
import { callTool, mcpTools } from '../agent/agent.js';
import { tool } from '../agent/tools.js';
import { createKnowledge } from '../core/knowledge.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const VERSIONS = ['2025-11-25', '2025-06-18', '2025-03-26', '2024-11-05'];
const MAX_FILES = 5000, MAX_BYTES = 512 * 1024 * 1024;
const note = (...a) => process.stderr.write(a.join(' ') + '\n');
console.log = console.info = console.warn = console.debug = note;          // nothing may reach standard output but MCP

const arg = name => { const i = process.argv.indexOf(name); return i > 0 ? process.argv[i + 1] : null; };

// The dossier folder's files, every level down, hidden files and folders left out.
function readFolder(root) {
  const out = [], skipped = [];
  const walk = dir => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      if (e.name.startsWith('.')) continue;
      const p = path.join(dir, e.name);
      if (e.isDirectory()) { walk(p); continue; }
      if (!e.isFile()) continue;
      const rel = path.relative(root, p).split(path.sep).join('/');
      const size = fs.statSync(p).size;
      if (out.length >= MAX_FILES || size > MAX_BYTES) { skipped.push(rel); continue; }
      out.push({ name: e.name, path: rel, bytes: new Uint8Array(fs.readFileSync(p)) });
    }
  };
  walk(root);
  if (skipped.length) note(`bridge: ${skipped.length} file(s) left out (over ${MAX_FILES} files or ${MAX_BYTES / 1048576} MB)`);
  return out;
}

async function knowledge() {
  const file = arg('--knowledge') || path.join(HERE, '..', 'dist', 'knowledge.json');
  if (fs.existsSync(file)) return createKnowledge(JSON.parse(fs.readFileSync(file, 'utf8')));
  try { const { loadKnowledge } = await import('../tools/load.mjs'); return createKnowledge(loadKnowledge()); }
  catch (e) { note(`bridge: the library could not be loaded (${e.message}); its tools will say so`); return null; }
}

let ctx = null;
async function context() {
  if (ctx) return ctx;
  const root = arg('--root');
  if (!root || !fs.existsSync(root) || !fs.statSync(root).isDirectory()) throw new Error(`the dossier folder «${root || ''}» does not exist`);
  const [ws, pdfjs, k] = await Promise.all([createWorkspace({ files: readFolder(path.resolve(root)) }),
                                            import('pdfjs-dist/legacy/build/pdf.mjs'), knowledge()]);
  ctx = { ws, pdfjs, knowledge: k, by: 'claude (bridge)' };
  note(`bridge: ${ws.files.length} file(s) in ${root}`);
  return ctx;
}

const send = msg => process.stdout.write(JSON.stringify(msg) + '\n');
const reply = (id, result) => send({ jsonrpc: '2.0', id, result });
const error = (id, code, message) => send({ jsonrpc: '2.0', id, error: { code, message } });

async function handle(msg) {
  const { id, method, params = {} } = msg;
  const isRequest = id !== undefined && id !== null;
  switch (method) {
    case 'initialize': {
      const asked = params.protocolVersion;
      return reply(id, { protocolVersion: VERSIONS.includes(asked) ? asked : VERSIONS[1],
        capabilities: { tools: { listChanged: false } },
        serverInfo: { name: 'dossier-builder', title: 'Dossier Builder', version: JSON.parse(fs.readFileSync(path.join(HERE, '..', 'package.json'), 'utf8')).version },
        instructions: 'The tools of Dossier Builder over one dossier folder: list its files, read PDF pages, search inside the files and the library of requirements, and record facts with the words that hold them.' });
    }
    case 'ping': return isRequest && reply(id, {});
    case 'tools/list': return reply(id, { tools: mcpTools() });
    case 'tools/call': {
      if (!tool(params.name)) return error(id, -32602, `Unknown tool: ${params.name}`);
      let c;
      try { c = await context(); } catch (e) { return reply(id, { content: [{ type: 'text', text: e.message }], isError: true }); }
      const r = await callTool(params.name, params.arguments ?? {}, c);
      return reply(id, r.ok ? { content: [{ type: 'text', text: JSON.stringify(r.result, null, 1) }], structuredContent: r.result, isError: false }
                            : { content: [{ type: 'text', text: r.error }], isError: true });
    }
    default:
      if (method?.startsWith('notifications/') || !isRequest) return;          // notifications need no answer
      return error(id, -32601, `Method not found: ${method}`);
  }
}

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
let queue = Promise.resolve();
rl.on('line', line => {
  if (!line.trim()) return;
  let msg;
  try { msg = JSON.parse(line); } catch { return error(null, -32700, 'Parse error'); }
  queue = queue.then(() => handle(msg)).catch(e => { note('bridge:', e?.stack || e); if (msg?.id != null) error(msg.id, -32603, String(e?.message || e)); });
});
rl.on('close', () => queue.then(() => process.exit(0)));
