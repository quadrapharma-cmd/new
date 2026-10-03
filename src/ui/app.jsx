import { useCallback, useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { S } from '../lib/i18n.js';
import { setDigitsMode, localizeDigits } from '../lib/digits.js';
import { initRuntime } from '../data/runtime.js';
import { createStore } from '../data/store.js';
import { createRepo, RepoError } from '../data/repo.js';
import { AppContext } from './context.js';
import { getPref, setPref } from './prefs.js';
import { navGroups, resolveRoute, hrefOf } from './routes.js';
import { useHashToken, navigate } from './hooks.js';
import { ErrorBoundary } from './ErrorBoundary.jsx';
import { runIntegrity, useIntegrity } from './integrity-state.js';
import { Banner, Button, ConfirmHost, EmptyState, IconButton, Loading, PeriodBanner, Pill, ToastHost, YearSelect, availableYears, toast } from './kit/index.js';

// ---------- theme ----------
function systemPrefersDark() {
  try {
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  } catch {
    return false;
  }
}
function useTheme() {
  const [explicit, setExplicit] = useState(() => {
    const t = getPref('theme');
    return t === 'dark' || t === 'light' ? t : null;
  });
  const [sysDark, setSysDark] = useState(systemPrefersDark());
  useEffect(() => {
    let mq;
    try {
      mq = window.matchMedia('(prefers-color-scheme: dark)');
    } catch {
      return undefined;
    }
    const on = () => setSysDark(mq.matches);
    mq.addEventListener ? mq.addEventListener('change', on) : mq.addListener(on);
    return () => (mq.removeEventListener ? mq.removeEventListener('change', on) : mq.removeListener(on));
  }, []);
  const effective = explicit || (sysDark ? 'dark' : 'light');
  const toggle = useCallback(() => {
    const next = effective === 'dark' ? 'light' : 'dark';
    setExplicit(next);
    setPref('theme', next);
    document.documentElement.setAttribute('data-theme', next);
  }, [effective]);
  return { effective, toggle };
}

// ---------- header, nav ----------
function Header({ companyName, theme, years, year, setYear, canEdit, dbOk, onMenu, navOpen, showMenu = true }) {
  return (
    <header className="app-header">
      <div className="app-header__inner">
        {showMenu ? <IconButton icon="menu" label={navOpen ? S.app.closeMenu : S.app.menu} className="nav-toggle" aria-expanded={navOpen ? 'true' : 'false'} aria-controls="app-nav" onClick={onMenu} /> : null}
        <a className="brand" href="#dashboard" aria-label={companyName}>
          <span className="brand__mark" aria-hidden="true">س</span>
          <span className="brand__text">
            <span className="brand__name">{companyName}</span>
            <span className="brand__sub">{S.app.title}</span>
          </span>
        </a>
        <div className="app-header__tools">
          {dbOk && !canEdit ? <Pill kind="warn" dot className="badge-readonly-header" title={S.app.readOnlyTitle}>{S.app.readOnlyBadge}</Pill> : null}
          {years ? (
            <div className="field-inline">
              <label htmlFor="year-select">{S.app.year}</label>
              <YearSelect id="year-select" value={year} years={years} onChange={setYear} />
            </div>
          ) : null}
          <IconButton
            icon={theme.effective === 'dark' ? 'sun' : 'moon'}
            label={theme.effective === 'dark' ? S.app.theme.toLight : S.app.theme.toDark}
            outline
            onClick={theme.toggle}
          />
        </div>
      </div>
    </header>
  );
}

function Nav({ activeScreen, open, onNavigate }) {
  const first = useRef(null);
  useEffect(() => {
    if (open) first.current?.focus();
  }, [open]);
  return (
    <>
      <nav className="nav" id="app-nav" aria-label={S.app.menu} data-open={open ? 'true' : 'false'}>
        {navGroups().map(({ group, items }, gi) => (
          <div className="nav__group" key={group}>
            <div className="nav__title" id={`nav-g-${group}`}>{S.nav.groups[group] || group}</div>
            <ul className="nav__list" aria-labelledby={`nav-g-${group}`}>
              {items.map((s, i) => (
                <li key={s.id}>
                  <a className="nav__link" href={hrefOf(s)} aria-current={activeScreen && activeScreen.id === s.id ? 'page' : undefined} ref={gi === 0 && i === 0 ? first : undefined} onClick={onNavigate}>
                    {s.title}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
      <button type="button" className="nav__scrim" aria-label={S.app.closeMenu} data-open={open ? 'true' : 'false'} tabIndex={-1} onClick={onNavigate} />
    </>
  );
}

// ---------- routed content ----------
function Routed({ token }) {
  const route = resolveRoute(token);
  if (!route) {
    return (
      <EmptyState icon="search" title={S.errors.notFoundTitle} text={S.errors.notFoundText} action={<Button kind="primary" onClick={() => navigate('dashboard')}>{S.errors.boundaryHome}</Button>} />
    );
  }
  const Screen = route.screen.component;
  return <Screen route={route} />;
}

function DbUnavailable() {
  return (
    <EmptyState
      icon="database"
      title={S.errors.dbUnavailableTitle}
      text={S.errors.dbUnavailableText}
      action={<Button onClick={() => location.reload()}>{S.common.reload}</Button>}
    >
      <p className="field__hint">{S.errors.dbUnavailableHint}</p>
    </EmptyState>
  );
}

function initialYear(years, fiscalYears) {
  const open = Object.values(fiscalYears || {})
    .filter((y) => y.state === 'open')
    .map((y) => Number(y.year))
    .sort((a, b) => b - a)[0];
  if (open && years.includes(open)) return open;
  const cur = new Date().getFullYear();
  return years.includes(cur) ? cur : years[0];
}

// ---------- connected shell ----------
function Connected({ boot }) {
  const { runtime, store, repo } = boot;
  const [state, setState] = useState(store.getState());
  const [status, setStatus] = useState(store.getStatus());
  useEffect(() => {
    const a = store.subscribe((s) => setState(s));
    const b = store.onStatus((s) => setStatus(s));
    // snapshots may have arrived between the first render and this effect: resync once
    setState(store.getState());
    setStatus(store.getStatus());
    return () => {
      a();
      b();
    };
  }, [store]);

  setDigitsMode(state.config.settings.digits); // before children render

  const years = useMemo(() => availableYears(state), [state.fiscalYears, state.entries]);
  // the viewer's explicit choice (or last session's) wins once it is a known year; otherwise the latest open year
  const [chosen, setChosen] = useState(() => Number(getPref('year')) || null);
  const yearOk = chosen && years.includes(chosen) ? chosen : initialYear(years, state.fiscalYears);
  const setYear = useCallback((y) => {
    setChosen(y);
    setPref('year', y);
  }, []);

  const dbOk = !!runtime.db;
  const canEdit = dbOk && runtime.user.canEdit();
  const theme = useTheme();
  const token = useHashToken();
  const route = resolveRoute(token);
  const [navOpen, setNavOpen] = useState(false);
  const main = useRef(null);
  const integrity = useIntegrity();

  // integrity check on load (once the first complete snapshot set arrived)
  const checked = useRef(false);
  useEffect(() => {
    if (status.phase === 'ready' && !checked.current) {
      checked.current = true;
      runIntegrity(store.getState());
    }
  }, [status.phase, store]);

  // new screen: close the drawer, scroll to top, move focus to the content
  const firstRoute = useRef(true);
  useEffect(() => {
    setNavOpen(false);
    if (firstRoute.current) {
      firstRoute.current = false;
      return;
    }
    window.scrollTo(0, 0);
    main.current?.focus({ preventScroll: true });
  }, [token]);
  useEffect(() => {
    if (!navOpen) return undefined;
    const on = (e) => e.key === 'Escape' && setNavOpen(false);
    document.addEventListener('keydown', on);
    return () => document.removeEventListener('keydown', on);
  }, [navOpen]);

  const ctx = useMemo(
    () => ({ runtime, store, repo, year: yearOk, setYear, years, canEdit, dbOk, digits: state.config.settings.digits }),
    [runtime, store, repo, yearOk, setYear, years, canEdit, dbOk, state.config.settings.digits],
  );

  const companyName = state.config.company.name || S.app.defaultCompany;
  const errNames = Object.keys(status.errors);

  return (
    <AppContext.Provider value={ctx}>
      <div className="app">
        <a className="sr-only" href="#main-content" onClick={(e) => { e.preventDefault(); main.current?.focus(); }}>{S.app.skipToContent}</a>
        <Header companyName={companyName} theme={theme} years={dbOk ? years : null} year={yearOk} setYear={setYear} canEdit={canEdit} dbOk={dbOk} navOpen={navOpen} showMenu={dbOk} onMenu={() => setNavOpen(!navOpen)} />
        <div className="app-body">
          {dbOk ? <Nav activeScreen={route && route.screen} open={navOpen} onNavigate={() => setNavOpen(false)} /> : null}
          <main className="content" id="main-content" tabIndex={-1} ref={main}>
            <div className="content__stack">
              {!dbOk ? (
                <DbUnavailable />
              ) : (
                <>
                  <PeriodBanner year={yearOk} fiscalYears={state.fiscalYears} />
                  {!canEdit ? <Banner kind="info" title={S.app.readOnlyTitle}>{S.app.readOnlyText}</Banner> : null}
                  {status.phase === 'revoked' ? <Banner kind="critical">{S.errors.revoked}</Banner> : null}
                  {integrity.status === 'done' && integrity.result && integrity.result.errors > 0 ? (
                    <Banner kind="critical" title={S.system.integrity} actions={<Button size="sm" onClick={() => navigate('system')}>{S.screens.system}</Button>}>
                      {S.system.integrityIssues.replace('{n}', localizeDigits(String(integrity.result.issues.length)))}
                    </Banner>
                  ) : null}
                  {errNames.length && status.phase !== 'revoked' ? (
                    <Banner kind="warn">{S.errors.loadFailed.replace('{names}', errNames.map((n) => S.collections[n] || n).join('، '))}</Banner>
                  ) : null}
                  <ErrorBoundary key={token}>
                    <Routed token={token} />
                  </ErrorBoundary>
                </>
              )}
            </div>
          </main>
        </div>
      </div>
      <ToastHost />
      <ConfirmHost />
    </AppContext.Provider>
  );
}

// ---------- root ----------
export function App() {
  const [boot, setBoot] = useState(null);
  const theme = useTheme();

  useEffect(() => {
    let store;
    let live = true;
    (async () => {
      const runtime = await initRuntime();
      store = createStore(runtime);
      const repo = createRepo({ runtime, store });
      store.start();
      if (live) setBoot({ runtime, store, repo });
    })();
    const onRejection = (e) => {
      const r = e.reason;
      console.error('Unhandled rejection', r);
      toast.error(r instanceof RepoError ? r.message : S.repo.unknown);
    };
    window.addEventListener('unhandledrejection', onRejection);
    return () => {
      live = false;
      store && store.stop();
      window.removeEventListener('unhandledrejection', onRejection);
    };
  }, []);

  return (
    <ErrorBoundary>
      {boot ? (
        <Connected boot={boot} />
      ) : (
        <div className="app">
          <Header companyName={S.app.defaultCompany} theme={theme} years={null} year={new Date().getFullYear()} setYear={() => {}} canEdit dbOk={false} navOpen={false} showMenu={false} onMenu={() => {}} />
          <main className="content"><Loading text={S.app.loading} /></main>
        </div>
      )}
    </ErrorBoundary>
  );
}
