import { S } from '../../lib/i18n.js';
import { Button, PageHead, Pill } from '../kit/index.js';
import { navigate } from '../hooks.js';

/** Designed "under construction" state for screens that are built later by their own owner. */
export function StubScreen({ id }) {
  const plan = S.stub.plan[id] || [];
  return (
    <div className="stack">
      <PageHead title={S.screens[id]} />
      <section className="stub" aria-labelledby={`stub-${id}`}>
        <Pill kind="warn" dot className="stub__tag">{S.stub.tag}</Pill>
        <h2 id={`stub-${id}`}>{S.stub.title}</h2>
        <p className="stub__text">{S.stub.text}</p>
        {plan.length ? (
          <ul className="stub__list">
            {plan.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        ) : null}
        <div>
          <Button onClick={() => navigate('dashboard')}>{S.stub.back}</Button>
        </div>
      </section>
    </div>
  );
}
