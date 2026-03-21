function PizInfoPanel({ selectedPiz }) {
  if (!selectedPiz) return null;

  return (
    <section className="panel piz-panel">
      <h4>PIZ ANALYSIS</h4>
      <p>ID: <span className="info">{selectedPiz.id}</span></p>
      <p>TARGETS: <span>{selectedPiz.targets}</span></p>
      <p>PRIORITY: <span className="warning">{selectedPiz.priority}</span></p>
      <p>CONFIDENCE: <span className="success">{selectedPiz.confidence}%</span></p>
    </section>
  );
}

export default PizInfoPanel;
