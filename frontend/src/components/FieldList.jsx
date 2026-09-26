import RiskBadge from "./RiskBadge";

export default function FieldList({
  fields,
  selectedFieldId,
  riskByFieldId,
  onSelect,
  ownerId,
  filterMyFields,
  onToggleFilter,
}) {
  const myFieldsCount = fields ? fields.filter((f) => f.owner_id === ownerId).length : 0;
  const displayedFields = fields
    ? filterMyFields
      ? fields.filter((f) => f.owner_id === ownerId)
      : fields
    : [];

  return (
    <div className="field-list-wrapper">
      <div className="field-list-header">
        <h3 className="field-list-title">Fields ({displayedFields.length})</h3>
        <div className="field-list-filters">
          <button
            className={`field-filter-btn${!filterMyFields ? " is-active" : ""}`}
            onClick={() => onToggleFilter(false)}
          >
            All Fields
          </button>
          <button
            className={`field-filter-btn${filterMyFields ? " is-active" : ""}`}
            onClick={() => onToggleFilter(true)}
          >
            My Fields ({myFieldsCount})
          </button>
        </div>
      </div>

      {displayedFields.length === 0 ? (
        <div className="field-list-empty">
          No fields match this view. Click <strong>✏️ Draw My Field</strong> on the map to add your farm boundary.
        </div>
      ) : (
        <ul className="field-list">
          {displayedFields.map((field) => {
            const risk = riskByFieldId?.[field.id];
            const selected = field.id === selectedFieldId;
            const isMine = field.owner_id === ownerId;

            return (
              <li key={field.id}>
                <button
                  className={`field-list__item${selected ? " is-selected" : ""}`}
                  onClick={() => onSelect(field.id)}
                  aria-current={selected}
                >
                  <div className="field-list__item-info">
                    <span className="field-list__name">{field.name}</span>
                    {isMine && <span className="field-list__owner-badge">My Field</span>}
                  </div>
                  {risk && <RiskBadge score={risk} compact />}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
