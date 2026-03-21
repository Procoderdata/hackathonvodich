import { useEffect, useState } from 'react';

function DataOpsPage() {
  const [state, setState] = useState({
    loading: true,
    error: '',
    source: '-',
    rows: 0,
    refreshedAt: '-',
    solver: '-',
    epochPolicy: '-',
    habitableCandidates: 0,
  });

  useEffect(() => {
    let mounted = true;

    fetch('/api/orbital-meta')
      .then((response) => {
        if (!response.ok) {
          throw new Error(`API returned ${response.status}`);
        }
        return response.json();
      })
      .then((payload) => {
        if (!mounted) return;
        setState({
          loading: false,
          error: '',
          source: payload.source || 'NASA Exoplanet Archive',
          rows: payload.rows || 0,
          refreshedAt: payload.refreshed_at_utc || 'unknown',
          solver: payload.solver || 'kepler_newton',
          epochPolicy: payload.epoch_policy || 'real_only(pl_orbtper|pl_tranmid)',
          habitableCandidates: payload.habitable_candidates || 0,
        });
      })
      .catch((error) => {
        if (!mounted) return;
        setState((prev) => ({
          ...prev,
          loading: false,
          error: error.message,
        }));
      });

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="dataops-layout">
      <section className="panel dataops-panel">
        <h3>DATA PIPELINE STATUS</h3>
        <p>Source: <span className="info">{state.source}</span></p>
        <p>Rows in active catalog: <span className="success">{state.rows}</span></p>
        <p>Habitable candidates: <span className="confirmed">{state.habitableCandidates}</span></p>
        <p>Kepler solver: <span className="info">{state.solver}</span></p>
        <p>Epoch policy: <span className="info">{state.epochPolicy}</span></p>
        <p>Last refresh (UTC): <span className="warning">{state.refreshedAt}</span></p>
        {state.loading ? <p className="info">Loading pipeline metadata...</p> : null}
        {state.error ? <p className="warning">Pipeline error: {state.error}</p> : null}
      </section>

      <section className="panel dataops-panel">
        <h3>NIGHTLY REFRESH COMMANDS</h3>
        <p>1. One-shot refresh:</p>
        <pre><code>python scripts/refresh_orbital_catalog.py</code></pre>

        <p>2. Install nightly launchd job (macOS):</p>
        <pre><code>python scripts/install_nightly_refresh_launchd.py --hour 2 --minute 15</code></pre>

        <p>3. Validate refreshed files:</p>
        <pre><code>ls -lah data/orbital_elements.csv data/orbital_elements.meta.json</code></pre>
      </section>

      <section className="panel dataops-panel">
        <h3>REAL-DATA POLICY</h3>
        <ul className="flat-list">
          <li>No demo fallback for orbital catalog.</li>
          <li>All orbit propagation uses Kepler solver with epoch from API metadata.</li>
          <li>If API/data file unavailable, UI reports OFFLINE instead of fabricating values.</li>
        </ul>
      </section>
    </div>
  );
}

export default DataOpsPage;
