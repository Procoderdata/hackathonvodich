function DiscoveryCollection({ discoveries, onOpenPlanet }) {
  return (
    <section className="panel discovery-panel">
      <h4>DISCOVERY COLLECTION</h4>
      <div className="discovery-list">
        {discoveries.length === 0 ? <p className="muted">No confirmed discoveries yet.</p> : null}
        {discoveries.map((item) => (
          <button
            key={item.id}
            type="button"
            className="discovery-item"
            onClick={() => onOpenPlanet(item)}
          >
            {item.id} - {item.habitable ? 'Habitable' : 'Non-Habitable'}
          </button>
        ))}
      </div>
    </section>
  );
}

export default DiscoveryCollection;
