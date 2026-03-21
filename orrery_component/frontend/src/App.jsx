import { useMemo, useState } from 'react';
import CommandCenterPage from './pages/CommandCenterPage.jsx';
import DataOpsPage from './pages/DataOpsPage.jsx';

const PAGES = {
  COMMAND: 'command',
  DATAOPS: 'dataops',
};

function App() {
  const [page, setPage] = useState(PAGES.COMMAND);

  const pageTitle = useMemo(() => {
    if (page === PAGES.DATAOPS) {
      return 'ATLAS Data Ops';
    }
    return 'ATLAS Command Center';
  }, [page]);

  return (
    <div className="app-shell">
      <header className="top-nav">
        <div className="brand">
          <h1>ATLAS ORRERY</h1>
          <span className="brand-sub">Real Data Mission Console</span>
        </div>
        <nav className="top-nav-buttons" aria-label="Main pages">
          <button
            className={`nav-btn ${page === PAGES.COMMAND ? 'active' : ''}`}
            onClick={() => setPage(PAGES.COMMAND)}
            type="button"
          >
            Command Center
          </button>
          <button
            className={`nav-btn ${page === PAGES.DATAOPS ? 'active' : ''}`}
            onClick={() => setPage(PAGES.DATAOPS)}
            type="button"
          >
            Data Ops
          </button>
        </nav>
      </header>

      <main className="page-root" aria-label={pageTitle}>
        {page === PAGES.COMMAND ? <CommandCenterPage /> : <DataOpsPage />}
      </main>
    </div>
  );
}

export default App;
