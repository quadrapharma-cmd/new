import { Component } from 'preact';
import { S } from '../lib/i18n.js';
import { Button } from './kit/Button.jsx';
import { Icon } from './kit/icons.jsx';

/** Friendly Arabic fallback instead of a blank page when a screen throws while rendering. */
export class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error) {
    console.error('UI error', error);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    const detail = String(error?.stack || error?.message || error);
    return (
      <div className="err-box" role="alert">
        <Icon name="critical" className="icon empty__icon" />
        <h1>{S.errors.boundaryTitle}</h1>
        <p>{S.errors.boundaryText}</p>
        <div className="row">
          <Button kind="primary" onClick={() => this.setState({ error: null })}>{S.common.retry}</Button>
          <Button
            onClick={() => {
              this.setState({ error: null });
              location.hash = 'dashboard';
            }}
          >
            {S.errors.boundaryHome}
          </Button>
        </div>
        <details>
          <summary>{S.errors.boundaryDetails}</summary>
          <pre className="mono" style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', direction: 'ltr', textAlign: 'left' }}>{detail}</pre>
        </details>
      </div>
    );
  }
}
