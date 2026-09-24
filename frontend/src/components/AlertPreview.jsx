export default function AlertPreview({ alerts }) {
  const latest = alerts?.[0];

  return (
    <section className="panel">
      <h2>Alert preview</h2>
      <p className="panel__hint">What the farmer would receive off-platform, simulated for this demo.</p>
      {!latest ? (
        <p className="panel__empty">No alert generated yet for this field.</p>
      ) : (
        <div className="alert-bubble">
          <span className="alert-bubble__channel">{latest.channel}</span>
          <p>{latest.message}</p>
          <time>{formatTime(latest.created_at)}</time>
        </div>
      )}
    </section>
  );
}

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleString(undefined, {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}
