const LABEL = {
  Low: 'Low risk',
  Medium: 'Medium risk',
  High: 'High risk',
};

export default function RiskBadge({ score, compact = false }) {
  if (!score) return null;
  return (
    <span className={`risk-badge risk-badge--${score.toLowerCase()}${compact ? ' is-compact' : ''}`}>
      {compact ? score : LABEL[score] ?? score}
    </span>
  );
}
