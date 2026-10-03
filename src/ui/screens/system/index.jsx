import { useMemo } from 'preact/hooks';
import { S, fmt } from '../../../lib/i18n.js';
import { formatBytes, formatInt, formatTimestamp, jsonBytes, cx } from '../../../lib/format.js';
import { COLLECTIONS, DOC_BYTES_CAP, DOC_CAP, SUBSCRIPTION_CAP } from '../../../data/schema.js';
import { Banner, Button, DataTable, Loading, PageHead, Pill } from '../../kit/index.js';
import { useApp, useStoreState, useStoreStatus } from '../../hooks.js';
import { runIntegrity, useIntegrity } from '../../integrity-state.js';
import { engineFn } from '../../engine.js';

export const id = 'system';
export const title = S.screens.system;
export const nav = { group: 'system', order: 20 };

const PHASE_KIND = { ready: 'good', loading: 'accent', idle: 'neutral', error: 'warn', revoked: 'critical', unavailable: 'critical' };

/** Approximate stored size per collection and the biggest single document. */
export function measure(state) {
  const sizes = {};
  let biggest = { path: '', bytes: 0 };
  const add = (name, path, v) => {
    const b = jsonBytes(v);
    sizes[name] = (sizes[name] || 0) + b;
    if (b > biggest.bytes) biggest = { path, bytes: b };
  };
  add('meta', 'meta/config', state.config);
  add('meta', 'meta/counters', state.counters);
  add('meta', 'meta/groups', { groups: state.groups });
  for (const c of COLLECTIONS) {
    if (!c.key) continue;
    for (const [docId, doc] of Object.entries(state[c.key] || {})) add(c.name, `${c.name}/${docId}`, doc);
  }
  return { sizes, biggest };
}

function Row({ label, children }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </>
  );
}
function Panel({ title: t, id: pid, actions, children, flush }) {
  return (
    <section className="panel" aria-labelledby={pid}>
      <div className="panel__head">
        <h2 className="panel__title" id={pid}>{t}</h2>
        {actions}
      </div>
      <div className={cx('panel__body', flush && 'panel__body--flush')}>{children}</div>
    </section>
  );
}

export function component() {
  const { runtime } = useApp();
  const state = useStoreState();
  const status = useStoreStatus();
  const integrity = useIntegrity();
  const m = useMemo(() => measure(state), [state]);
  const hasChecker = !!engineFn('checkIntegrity');
  const ready = status.phase === 'ready';

  const pct = Math.min(100, (status.total / DOC_CAP) * 100);
  const capKind = pct >= 90 ? 'critical' : pct >= 70 ? 'warn' : '';
  const names = COLLECTIONS.map((c) => c.name);
  const loadedCount = names.filter((n) => status.loaded[n]).length;
  const errorNames = Object.keys(status.errors);

  const lastImport = Object.values(state.importRuns || {}).sort((a, b) => String(b.at).localeCompare(String(a.at)))[0] || null;
  const baseline = state.config.baseline;

  const rows = COLLECTIONS.map((c) => ({
    key: c.name,
    label: S.collections[c.name],
    count: status.counts[c.name] ?? 0,
    bytes: m.sizes[c.name] || 0,
  }));

  const cols = [
    { key: 'label', header: S.system.collection, render: (r) => (<>{r.label} <span className="muted mono">{r.key}</span></>) },
    { key: 'count', header: S.system.count, align: 'num', render: (r) => formatInt(r.count), total: () => formatInt(status.total) },
    { key: 'share', header: S.system.share, align: 'num', render: (r) => `${((r.count / DOC_CAP) * 100).toFixed(1)}%`, total: () => `${pct.toFixed(1)}%` },
    { key: 'bytes', header: S.system.bytes, align: 'num', render: (r) => formatBytes(r.bytes), total: () => formatBytes(rows.reduce((a, r) => a + r.bytes, 0)) },
  ];

  const nearLimit = m.biggest.bytes > DOC_BYTES_CAP * 0.7;

  return (
    <div className="stack">
      <PageHead title={S.screens.system} sub={S.system.subtitle} />

      {!ready && status.phase === 'loading' ? <Loading text={S.app.loading} /> : null}
      {status.phase === 'revoked' ? <Banner kind="critical">{S.errors.revoked}</Banner> : null}
      {errorNames.length ? <Banner kind="warn" title={S.system.phases.error}>{fmt(S.errors.loadFailed, { names: errorNames.map((n) => S.collections[n] || n).join('، ') })}</Banner> : null}

      <div className="grid-2">
        <Panel title={S.system.db} id="sys-db">
          <dl className="kv">
            <Row label={S.system.status}>
              <Pill kind={PHASE_KIND[status.phase] || 'neutral'} dot>{S.system.phases[status.phase] || status.phase}</Pill>
            </Row>
            <Row label={S.system.subscriptions}><span className="ltr">{`${status.subscriptions} / ${SUBSCRIPTION_CAP}`}</span></Row>
            <Row label={S.system.collectionsLoaded}><span className="ltr">{`${loadedCount} / ${names.length}`}</span></Row>
            <Row label={S.system.schema}><span className="ltr">{state.config.schemaVersion}</span></Row>
          </dl>
          <p className="field__hint" style={{ marginTop: 8 }}>{S.system.subscriptionsNote}</p>
        </Panel>

        <Panel title={S.system.user} id="sys-user">
          <dl className="kv">
            <Row label={S.system.userName}>{runtime.user.name || S.common.unknown}</Row>
            <Row label={S.system.userLevel}>
              <Pill kind={runtime.user.level === 'viewer' ? 'warn' : runtime.user.level === 'unknown' ? 'neutral' : 'accent'}>{S.roles[runtime.user.level]}</Pill>
            </Row>
            <Row label={S.system.userCanWrite}>{runtime.user.canEdit() ? S.common.yes : S.common.no}</Row>
          </dl>
        </Panel>
      </div>

      <Panel title={S.system.docsTitle} id="sys-docs" flush>
        <div className="panel__body">
          <div className="stack-sm">
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <strong>
                {S.system.docsTotal}: <span className="ltr">{`${formatInt(status.total)} / ${formatInt(DOC_CAP)}`}</span>
              </strong>
              <span className="muted">{S.system.capLabel} <span className="ltr">{formatInt(DOC_CAP)}</span></span>
            </div>
            <div className={cx('meter', capKind && `meter--${capKind}`)} role="progressbar" aria-valuemin={0} aria-valuemax={DOC_CAP} aria-valuenow={status.total} aria-label={S.system.docsTotal}>
              <div className="meter__bar" style={{ width: `${pct}%` }} />
            </div>
            {pct >= 90 ? <Banner kind="critical">{S.system.capCritical}</Banner> : pct >= 70 ? <Banner kind="warn">{S.system.capWarn}</Banner> : null}
            <p className="field__hint">
              {S.system.biggest}: <span className="mono">{m.biggest.path || '-'}</span> <span className="ltr">{formatBytes(m.biggest.bytes)}</span>. {S.system.biggestNote}
            </p>
            {nearLimit ? <Banner kind="warn">{fmt(S.system.docNearLimit, { path: m.biggest.path, size: formatBytes(m.biggest.bytes) })}</Banner> : null}
          </div>
        </div>
        <DataTable columns={cols} rows={rows} totals dense sticky={false} ariaLabel={S.system.docsTitle} className="table-wrap--panel" />
      </Panel>

      <Panel
        title={S.system.integrity}
        id="sys-integrity"
        actions={hasChecker ? <Button size="sm" busy={integrity.status === 'running'} disabled={!ready} onClick={() => runIntegrity(state)}>{S.system.integrityRun}</Button> : null}
      >
        <div className="stack-sm">
          {!hasChecker || integrity.status === 'missing' ? (
            <Banner kind="info">{S.system.integrityMissing}</Banner>
          ) : integrity.status === 'error' ? (
            <Banner kind="critical">{fmt(S.system.integrityFailed, { msg: integrity.message })}</Banner>
          ) : integrity.status === 'done' && integrity.result ? (
            integrity.result.issues.length === 0 ? (
              <Banner kind="good">{S.system.integrityOk}</Banner>
            ) : (
              <>
                <Banner kind={integrity.result.errors ? 'critical' : 'warn'}>{fmt(S.system.integrityIssues, { n: integrity.result.issues.length })}</Banner>
                <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                  {integrity.result.issues.slice(0, 100).map((it, i) => (
                    <li key={i} className="issue">
                      <Pill kind={it.severity === 'error' ? 'critical' : it.severity === 'info' ? 'neutral' : 'warn'}>{S.severity[it.severity]}</Pill>
                      <span className="issue__body">
                        {it.message} {it.ref ? <span className="muted mono">{String(it.ref)}</span> : null}
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            )
          ) : (
            <p className="muted">{ready ? S.common.loading : S.system.integrityWaiting}</p>
          )}
          <p className="field__hint">{S.system.integrityNote}</p>
        </div>
      </Panel>

      <div className="grid-2">
        <Panel title={S.system.lastImport} id="sys-import">
          {lastImport || baseline ? (
            <dl className="kv">
              <Row label={S.system.importedAt}><span className="ltr">{formatTimestamp(lastImport?.at || baseline?.importedAt)}</span></Row>
              {baseline?.file ? <Row label={S.system.importFile}><span className="mono">{baseline.file}</span></Row> : null}
              {(lastImport?.fileSha256 || baseline?.sha256) ? <Row label="SHA-256"><span className="mono">{String(lastImport?.fileSha256 || baseline?.sha256).slice(0, 16)}…</span></Row> : null}
            </dl>
          ) : (
            <p className="muted">{S.system.lastImportNone}</p>
          )}
        </Panel>

        <Panel title={S.system.capabilities} id="sys-caps">
          <dl className="kv">
            {['db', 'user', 'downloads', 'assets'].map((c) => (
              <Row key={c} label={S.system[`cap_${c}`]}>
                <Pill kind={runtime.caps[c] ? 'good' : 'neutral'} dot>{runtime.caps[c] ? S.system.available : S.system.notAvailable}</Pill>
              </Row>
            ))}
          </dl>
        </Panel>
      </div>

      <Banner kind="info">{S.system.auditNote}</Banner>
    </div>
  );
}
