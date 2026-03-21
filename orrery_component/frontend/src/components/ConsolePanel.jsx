function ConsolePanel({ lines }) {
  return (
    <section className="panel console-panel">
      <h4>SYSTEM CONSOLE</h4>
      <div className="console-lines">
        {lines.map((line) => (
          <div key={line.id} className={`console-line ${line.type}`}>
            &gt; {line.message}
          </div>
        ))}
      </div>
    </section>
  );
}

export default ConsolePanel;
