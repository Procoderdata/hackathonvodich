function CouncilChatPanel({ messages, input, onInputChange, onSend, loading }) {
  return (
    <section className="panel chat-panel">
      <h4>COUNCIL CHAT</h4>
      <div className="chat-feed">
        {messages.map((item) => (
          <div key={item.id} className={`chat-bubble ${item.role}`}>
            <div className="chat-role">{item.role === 'user' ? 'YOU' : 'COUNCIL'}</div>
            <div className="chat-text">{item.text}</div>
          </div>
        ))}
      </div>

      <form
        className="chat-form"
        onSubmit={(event) => {
          event.preventDefault();
          onSend();
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(event) => onInputChange(event.target.value)}
          placeholder="Ask the council: Why this target? Compare candidates?"
          className="chat-input"
        />
        <button type="submit" className="action-btn" disabled={loading || !input.trim()}>
          {loading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </section>
  );
}

export default CouncilChatPanel;
