const SERIES = [
  { key: 'ndvi', label: 'Vegetation (NDVI)', color: '#5C7A3D', format: (v) => v.toFixed(2) },
  { key: 'rainfall_mm', label: 'Rainfall', color: '#1B6E6E', format: (v) => `${v.toFixed(0)}mm` },
  { key: 'temp_c', label: 'Temperature', color: '#B4741F', format: (v) => `${v.toFixed(0)}°C` },
];

const WIDTH = 320;
const HEIGHT = 64;
const PAD = 6;

export default function TrendChart({ readings }) {
  const hasAnyData = readings?.some((r) => r.ndvi != null || r.rainfall_mm != null || r.temp_c != null);

  return (
    <section className="panel">
      <h2>Recent trend</h2>
      {!hasAnyData ? (
        <p className="panel__empty">
          No readings cached for this field yet. Readings appear here once live weather and satellite data
          have been pulled for the first time.
        </p>
      ) : (
        <div className="trend-chart">
          {SERIES.map((series) => (
            <Sparkline key={series.key} series={series} readings={readings} />
          ))}
        </div>
      )}
    </section>
  );
}

function Sparkline({ series, readings }) {
  const points = readings
    .map((r, i) => ({ i, v: r[series.key] }))
    .filter((p) => p.v != null);

  if (points.length === 0) {
    return (
      <div className="sparkline">
        <div className="sparkline__label">{series.label}</div>
        <p className="sparkline__empty">No data yet</p>
      </div>
    );
  }

  const values = points.map((p) => p.v);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const n = readings.length;

  const x = (i) => PAD + (i / Math.max(n - 1, 1)) * (WIDTH - PAD * 2);
  const y = (v) => HEIGHT - PAD - ((v - min) / range) * (HEIGHT - PAD * 2);

  const path = points.map((p, idx) => `${idx === 0 ? 'M' : 'L'}${x(p.i)},${y(p.v)}`).join(' ');
  const latest = points[points.length - 1];

  return (
    <div className="sparkline">
      <div className="sparkline__label">
        {series.label}
        <span className="sparkline__latest" style={{ color: series.color }}>
          {series.format(latest.v)}
        </span>
      </div>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="sparkline__svg" aria-hidden="true">
        <path d={path} fill="none" stroke={series.color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        {points.map((p) => (
          <circle key={p.i} cx={x(p.i)} cy={y(p.v)} r="2.5" fill={series.color} />
        ))}
      </svg>
    </div>
  );
}
