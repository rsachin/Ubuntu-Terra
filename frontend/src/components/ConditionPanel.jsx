import RiskBadge from './RiskBadge';

export default function ConditionPanel({ risk }) {
  if (!risk) {
    return (
      <section className="panel">
        <h2>Condition</h2>
        <p className="panel__empty">Risk data isn't available for this field right now.</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="panel__header">
        <h2>Condition</h2>
        <RiskBadge score={risk.score} />
      </div>
      <ul className="panel__reasons">
        {risk.reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
      <p className="panel__check">
        <strong>Recommended check:</strong> {risk.recommended_check}
      </p>
    </section>
  );
}
