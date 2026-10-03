import { createContext } from 'preact';

/**
 * App-wide context value: { runtime, store, repo, year, setYear, years, canEdit, readOnly, digits }
 * (screens read it with useApp() from hooks.js).
 */
export const AppContext = createContext(null);
