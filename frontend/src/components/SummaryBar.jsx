/**
 * SummaryBar — displays trip aggregate stats.
 */
export default function SummaryBar({ trip }) {
  const stats = [
    { label: 'Total Distance',  value: `${trip.total_distance_miles?.toFixed(1)} mi` },
    { label: 'Drive Time',      value: `${trip.total_drive_hours?.toFixed(1)} hrs` },
    { label: 'Trip Days',       value: `${trip.total_days} day${trip.total_days !== 1 ? 's' : ''}` },
    { label: 'Rest Stops',      value: trip.total_rest_stops ?? 0 },
    { label: 'Fuel Stops',      value: trip.total_fuel_stops ?? 0 },
    { label: 'Log Sheets',      value: trip.log_sheets?.length ?? 0 },
  ]

  return (
    <div className="summary-bar">
      {stats.map((s) => (
        <div key={s.label} className="summary-stat">
          <div className="summary-stat-value">{s.value}</div>
          <div className="summary-stat-label">{s.label}</div>
        </div>
      ))}
    </div>
  )
}
