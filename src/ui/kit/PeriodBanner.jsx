import { useId, useState } from 'preact/hooks';
import { S, fmt } from '../../lib/i18n.js';
import { localizeDigits } from '../../lib/digits.js';
import { formatDate } from '../../lib/dates.js';
import { cx } from '../../lib/format.js';
import { Icon } from './icons.jsx';
import { Pill } from './Pill.jsx';

const KIND = { open: 'good', closed_reserved: 'warn', locked: 'critical' };
const HINT = { open: S.period.hintOpen, closed_reserved: S.period.hintReserved, locked: S.period.hintLocked };

/**
 * Period state of the selected year, from state.fiscalYears:
 * green مفتوحة / amber مقفلة بتحفظ / red مقفلة نهائياً. Click to show the reservation text.
 */
export function PeriodBanner({ year, fiscalYears, className }) {
  const [open, setOpen] = useState(false);
  const auto = useId();
  const doc = fiscalYears ? fiscalYears[year] || fiscalYears[String(year)] : null;
  const state = doc?.state && KIND[doc.state] ? doc.state : 'open';
  const kind = KIND[state];
  const res = doc?.reservation || {};
  const label = fmt(S.period.label, { year: localizeDigits(String(year)), state: S.period[state] });
  const dateText = (v) => (typeof v === 'string' && /^\d{4}-\d{2}-\d{2}/.test(v) ? localizeDigits(formatDate(v.slice(0, 10))) : v || '');
  const panelId = `period-${auto}`;
  return (
    <div className={cx('period', `period--${kind}`, className)}>
      <button type="button" className="period__btn" aria-expanded={open ? 'true' : 'false'} aria-controls={panelId} onClick={() => setOpen(!open)}>
        <Icon name={state === 'open' ? 'good' : state === 'locked' ? 'lock' : 'warn'} />
        <span className="period__label">{label}</span>
        {!doc ? <Pill title={S.period.unregisteredHint}>{S.period.unregistered}</Pill> : null}
        <span className="period__more">
          <span className="period__more-text">{open ? S.period.hideDetail : S.period.showDetail}</span>
          <Icon name="chevron" />
        </span>
      </button>
      {open ? (
        <div className="period__detail" id={panelId}>
          <p>{HINT[state]}</p>
          <div>
            <h4>{S.period.reservation}</h4>
            <p>{res.text || S.period.noReservation}</p>
          </div>
          {res.sources ? (
            <div>
              <h4>{S.period.sources}</h4>
              <p>{res.sources}</p>
            </div>
          ) : null}
          {res.notRecorded ? (
            <div>
              <h4>{S.period.notRecorded}</h4>
              <p>{res.notRecorded}</p>
            </div>
          ) : null}
          {res.lastUpdate ? (
            <div>
              <h4>{S.period.lastUpdate}</h4>
              <p>{dateText(res.lastUpdate)}</p>
            </div>
          ) : null}
          {doc?.revision ? (
            <div>
              <h4>{S.period.revision}</h4>
              <p>{localizeDigits(String(doc.revision))}</p>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
