const SPEED_BUTTONS = [
  { label: 'REV x8', value: -8 },
  { label: 'REV x1', value: -1 },
  { label: 'PAUSE', value: 0 },
  { label: 'PLAY', value: 1 },
  { label: 'FWD x8', value: 8 },
];

function TimeControlBar({ simDateText, simSpeedText, timeScale, onSpeedSelect, onResetTime }) {
  return (
    <section className="panel time-panel">
      <div className="time-meta">
        Date: <span className="info">{simDateText}</span> | Speed: <span className="success">{simSpeedText}</span>
      </div>
      <div className="button-row">
        {SPEED_BUTTONS.map((button) => (
          <button
            key={button.value}
            type="button"
            className={`action-btn ${timeScale === button.value ? 'active' : ''}`}
            onClick={() => onSpeedSelect(button.value)}
          >
            {button.label}
          </button>
        ))}
        <button type="button" className="action-btn" onClick={onResetTime}>NOW</button>
      </div>
    </section>
  );
}

export default TimeControlBar;
