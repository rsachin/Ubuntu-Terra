import RiskBadge from './RiskBadge';

export default function FieldList({ fields, selectedFieldId, riskByFieldId, onSelect }) {
  return (
    <ul className="field-list">
      {fields.map((field) => {
        const risk = riskByFieldId?.[field.id];
        const selected = field.id === selectedFieldId;
        return (
          <li key={field.id}>
            <button
              className={`field-list__item${selected ? ' is-selected' : ''}`}
              onClick={() => onSelect(field.id)}
              aria-current={selected}
            >
              <span className="field-list__name">{field.name}</span>
              {risk && <RiskBadge score={risk} compact />}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
