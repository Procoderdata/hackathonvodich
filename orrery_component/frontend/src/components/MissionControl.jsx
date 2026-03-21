function MissionControl({ visible, onScan }) {
  if (!visible) return null;

  return (
    <section className="panel mission-panel">
      <h4>TACTICAL DEPLOYMENT</h4>
      <p>SELECT SCAN PATTERN:</p>
      <div className="button-row">
        <button type="button" className="action-btn" onClick={() => onScan('grid')}>GRID SCAN (FAST)</button>
        <button type="button" className="action-btn" onClick={() => onScan('spiral')}>SPIRAL SCAN (DEEP)</button>
        <button type="button" className="action-btn" onClick={() => onScan('targeted')}>TARGETED TRACK</button>
      </div>
    </section>
  );
}

export default MissionControl;
