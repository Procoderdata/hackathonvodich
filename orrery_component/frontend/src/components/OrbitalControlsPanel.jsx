function OrbitalControlsPanel({
  ui,
  filters,
  onFilterChange,
  onTrackEnable,
  onTrackDisable,
}) {
  const dataStatusClass = ui.dataStatus === 'LIVE' ? 'success' : 'warning';

  return (
    <section className="panel orbital-panel">
      <h4>
        ORRERY ANALYTICS <span className={`pill ${dataStatusClass}`}>{ui.dataStatus}</span>
      </h4>
      <p>Source: <span className="info">{ui.dataSource}</span></p>
      <p>
        Visible Objects: <span className="success">{ui.catalogVisible} / {ui.catalogTotal}</span>
      </p>
      <p>
        Solver: <span className="info">{ui.solverName}</span>
      </p>
      <p>
        Tracking: <span className={ui.trackingTarget === 'OFF' ? 'warning' : 'success'}>{ui.trackingTarget}</span>
      </p>
      <div className="button-row">
        <button type="button" className="action-btn" onClick={onTrackEnable}>Track (T)</button>
        <button type="button" className="action-btn danger" onClick={onTrackDisable}>Unlock (U)</button>
      </div>

      <div className="filter-block">
        <div className="filter-title">CATEGORY FILTERS</div>
        <label className="inline-check">
          <input
            type="checkbox"
            checked={filters.showConfirmed}
            onChange={(event) => onFilterChange({ showConfirmed: event.target.checked })}
          />
          Confirmed Planets
        </label>
        <label className="inline-check">
          <input
            type="checkbox"
            checked={filters.showHabitable}
            onChange={(event) => onFilterChange({ showHabitable: event.target.checked })}
          />
          Habitable Candidates
        </label>
      </div>

      <div className="filter-block">
        <div className="filter-title">RADIUS (EARTH RADII)</div>
        <div className="range-row">
          <span>{filters.radiusMin.toFixed(1)}</span>
          <input
            type="range"
            min="0.3"
            max="20"
            step="0.1"
            value={filters.radiusMin}
            onChange={(event) => onFilterChange({ radiusMin: Number(event.target.value) })}
          />
        </div>
        <div className="range-row">
          <span>{filters.radiusMax.toFixed(1)}</span>
          <input
            type="range"
            min="0.3"
            max="20"
            step="0.1"
            value={filters.radiusMax}
            onChange={(event) => onFilterChange({ radiusMax: Number(event.target.value) })}
          />
        </div>
      </div>

      <div className="filter-block">
        <div className="filter-title">ORBIT PERIOD (DAYS)</div>
        <div className="range-row">
          <span>{Math.round(filters.periodMin)}</span>
          <input
            type="range"
            min="1"
            max="1200"
            step="5"
            value={filters.periodMin}
            onChange={(event) => onFilterChange({ periodMin: Number(event.target.value) })}
          />
        </div>
        <div className="range-row">
          <span>{Math.round(filters.periodMax)}</span>
          <input
            type="range"
            min="1"
            max="1200"
            step="5"
            value={filters.periodMax}
            onChange={(event) => onFilterChange({ periodMax: Number(event.target.value) })}
          />
        </div>
      </div>

      <div className="shortcut-note">
        Keys: <span className="info">T</span> Track, <span className="info">U</span> Unlock, <span className="info">Q/E</span> Speed -/+.
      </div>
    </section>
  );
}

export default OrbitalControlsPanel;
