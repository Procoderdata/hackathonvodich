function MissionControl({ visible, onScan }) {
  const disabled = !visible;

  return (
    <section className="panel mission-panel">
      <h4>TACTICAL DEPLOYMENT</h4>
      <p className="mission-note">
        {disabled
          ? 'Select a PIZ target to unlock scan patterns.'
          : 'Mission target locked. Choose scan pattern.'}
      </p>
      <div className="button-row">
        <button type="button" className="action-btn" disabled={disabled} onClick={() => onScan('grid')}>GRID SCAN</button>
        <button type="button" className="action-btn" disabled={disabled} onClick={() => onScan('spiral')}>SPIRAL SCAN</button>
        <button type="button" className="action-btn" disabled={disabled} onClick={() => onScan('targeted')}>TARGETED TRACK</button>
      </div>
    </section>
  );
}

export default MissionControl;
