function PizInfoPanel({ selectedPiz, pizCatalog = [], onSelectPiz }) {
  return (
    <section className="panel piz-panel">
      <h4>PIZ ANALYSIS</h4>
      {!selectedPiz ? (
        <p className="muted">Select any highlighted PIZ sphere in the orrery or choose from the list below.</p>
      ) : (
        <>
          <p>ID: <span className="info">{selectedPiz.id}</span></p>
          <p>TARGETS: <span>{selectedPiz.targets}</span></p>
          <p>PRIORITY: <span className="warning">{selectedPiz.priority}</span></p>
          <p>CONFIDENCE: <span className="success">{selectedPiz.confidence}%</span></p>
        </>
      )}

      {pizCatalog.length > 0 ? (
        <div className="filter-block">
          <div className="filter-title">FAST PIZ PICKER</div>
          <div className="button-row">
            {pizCatalog.slice(0, 6).map((piz) => (
              <button
                key={piz.id}
                type="button"
                className={`action-btn ${selectedPiz?.id === piz.id ? 'active' : ''}`}
                onClick={() => onSelectPiz?.(piz.id)}
              >
                {piz.id}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

export default PizInfoPanel;
