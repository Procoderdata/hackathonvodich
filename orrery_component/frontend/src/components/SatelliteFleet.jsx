function SatelliteFleet({ selectedSatellite, onSelectSatellite }) {
  const satellites = ['NEOSSat-1', 'NEOSSat-2', 'NEOSSat-3'];

  return (
    <section className="panel fleet-panel">
      <h4>SATELLITE FLEET</h4>
      {satellites.map((name, index) => (
        <button
          key={name}
          type="button"
          className={`satellite-card ${selectedSatellite === index ? 'active' : ''}`}
          onClick={() => onSelectSatellite(index)}
        >
          <strong>{name}</strong> - Status: <span className="info">IDLE</span>
        </button>
      ))}
    </section>
  );
}

export default SatelliteFleet;
