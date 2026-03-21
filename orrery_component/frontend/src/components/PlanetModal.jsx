function PlanetModal({ open, details, onClose }) {
  if (!open || !details) return null;

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Planet details">
      <section className="modal-panel">
        <header className="modal-header">
          <h3>EXOPLANET DISCOVERY CONFIRMED</h3>
          <button type="button" className="action-btn danger" onClick={onClose}>CLOSE</button>
        </header>

        <div className="modal-grid">
          <div className="data-card">
            <h4>PLANETARY ANALYSIS</h4>
            <p>Designation: <span className="info">{details.id}</span></p>
            <p>Host Star: <span>{details.star || 'Unknown'}</span></p>
            <p>Mass: <span>{details.mass}</span></p>
            <p>Radius: <span>{details.radius}</span></p>
            <p>Period: <span>{details.period}</span></p>
            <p>Equilibrium Temp: <span>{details.temp}</span></p>
          </div>

          <div className="data-card">
            <h4>ORBITAL PROFILE</h4>
            <p>Semi-major Axis: <span>{details.semi_major || 'Unknown'}</span></p>
            <p>Eccentricity: <span>{details.eccentricity || 'Unknown'}</span></p>
            <p>Inclination: <span>{details.inclination || 'Unknown'}</span></p>
            <p>Insolation: <span>{details.insolation || 'Unknown'}</span></p>
            <p>Distance: <span>{details.distance || 'Unknown'}</span></p>
            <p>Facility: <span>{details.discovery_facility || 'Unknown'}</span></p>
          </div>

          <div className="data-card">
            <h4>HABITABILITY ASSESSMENT</h4>
            <p>Classification: <span className={details.habitable ? 'success' : 'warning'}>{details.habitable ? 'Candidate' : 'Non-habitable'}</span></p>
            <p>Overall Index: <span>{details.habitable ? '0.82' : '0.31'}</span></p>
            <p>Status: <span className="confirmed">Ready for follow-up proposal</span></p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default PlanetModal;
