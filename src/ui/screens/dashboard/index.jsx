import { S, fmt } from '../../../lib/i18n.js';
import { formatInt } from '../../../lib/format.js';
import { localizeDigits } from '../../../lib/digits.js';
import { EmptyState, Loading, PageHead, Pill, Banner, Button } from '../../kit/index.js';
import { useApp, useStoreState, useStoreStatus, navigate } from '../../hooks.js';

export const id = 'dashboard';
export const title = S.screens.dashboard;
export const nav = { group: 'home', order: 10 };

function Tile({ label, value, sub, href }) {
  const inner = (
    <>
      <span className="tile__label">{label}</span>
      <span className="tile__value">{value}</span>
      {sub ? <span className="tile__sub">{sub}</span> : null}
    </>
  );
  return href ? (
    <a className="tile tile--link" href={href}>{inner}</a>
  ) : (
    <div className="tile">{inner}</div>
  );
}

const YEAR_KIND = { open: 'good', closed_reserved: 'warn', locked: 'critical' };

export function summarize(state) {
  const entries = Object.values(state.entries);
  const docs = Object.values(state.documents);
  const items = Object.values(state.openItems);
  const assumptions = Object.values(state.assumptions);
  return {
    posted: entries.filter((e) => e.status === 'posted').length,
    drafts: entries.filter((e) => e.status === 'draft').length,
    voids: entries.filter((e) => e.status === 'void').length,
    accountsActive: Object.values(state.accounts).filter((a) => a.active !== false).length,
    parties: Object.values(state.parties).filter((p) => !p.mergedInto && p.active !== false).length,
    documents: docs.length,
    docsExpected: docs.filter((d) => d.status === 'expected').length,
    docsReceived: docs.filter((d) => d.status === 'received').length,
    openItems: items.filter((i) => i.status !== 'closed').length,
    openItemsTotal: items.length,
    assumptionsPending: assumptions.filter((a) => a.status === 'pending' || !a.status).length,
    assumptionsTotal: assumptions.length,
  };
}

export function component() {
  const state = useStoreState();
  const status = useStoreStatus();
  const { canEdit } = useApp();
  if (status.phase === 'loading' || status.phase === 'idle') return <Loading text={S.app.loading} />;
  const m = summarize(state);
  const empty = status.total === 0 || (!m.posted && !m.drafts && !m.accountsActive && !m.documents);
  const n = (v) => formatInt(v);
  const years = Object.values(state.fiscalYears).sort((a, b) => b.year - a.year);
  return (
    <div className="stack">
      <PageHead title={S.screens.dashboard} sub={S.dashboard.subtitle} />
      {empty ? (
        <EmptyState
          icon="database"
          title={S.dashboard.emptyTitle}
          text={S.dashboard.emptyText}
          action={canEdit ? <Button kind="primary" onClick={() => navigate('import')}>{S.screens.import}</Button> : null}
        />
      ) : (
        <>
          <div className="grid-tiles">
            <Tile label={S.dashboard.entries} value={n(m.posted)} href="#entries" />
            <Tile label={S.dashboard.drafts} value={n(m.drafts)} href="#entries" />
            <Tile label={S.dashboard.voids} value={n(m.voids)} href="#entries" />
            <Tile label={S.dashboard.accounts} value={n(m.accountsActive)} />
            <Tile label={S.dashboard.parties} value={n(m.parties)} href="#parties" />
            <Tile
              label={S.dashboard.documents}
              value={n(m.documents)}
              href="#documents"
              sub={`${fmt(S.dashboard.documentsExpected, { n: m.docsExpected })} · ${fmt(S.dashboard.documentsReceived, { n: m.docsReceived })}`}
            />
            <Tile label={S.dashboard.openItems} value={n(m.openItems)} href="#registers" sub={fmt(S.dashboard.openItemsSub, { total: m.openItemsTotal })} />
            <Tile label={S.dashboard.assumptions} value={n(m.assumptionsPending)} href="#registers" sub={fmt(S.dashboard.assumptionsSub, { total: m.assumptionsTotal })} />
          </div>
          <section aria-labelledby="dash-years">
            <h2 className="section-title" id="dash-years">{S.dashboard.years}</h2>
            {years.length ? (
              <div className="row">
                {years.map((y) => (
                  <Pill key={y.year} kind={YEAR_KIND[y.state] || 'neutral'} dot>
                    {localizeDigits(String(y.year))} — {S.period[y.state] || y.state}
                  </Pill>
                ))}
              </div>
            ) : (
              <p className="muted">{S.dashboard.yearsEmpty}</p>
            )}
          </section>
          <Banner kind="info">{S.dashboard.note}</Banner>
        </>
      )}
    </div>
  );
}
