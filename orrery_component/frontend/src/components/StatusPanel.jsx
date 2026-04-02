function StatusPanel({ priorityCount, discoveryCount }) {
  return (
    <section className="panel status-panel">
      <h3>ATLAS COMMAND CENTER</h3>
      <p>&gt; STATUS: <span className="success">OPERATIONAL</span></p>
      <p>&gt; DIRECTOR: <span className="info">CLASSIFIED</span></p>
      <p>&gt; SATELLITES: <span className="info">3 ACTIVE</span></p>
      <p>&gt; PRIORITY ZONES: <span className="warning">{priorityCount} DETECTED</span></p>
      <p>&gt; DISCOVERIES: <span className="confirmed">{discoveryCount}</span></p>
    </section>
  );
}

export default StatusPanel;
