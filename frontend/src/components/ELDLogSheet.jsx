import React from 'react'

const ROW_LABELS = [
  { label: 'OFF DUTY', key: 'off_duty_slots', color: '#cbd5e1' }, // Gray
  { label: 'SLEEPER', key: 'sleeper_slots', color: '#a855f7' }, // Purple
  { label: 'DRIVING', key: 'driving_slots', color: '#3b82f6' }, // Blue
  { label: 'ON DUTY', key: 'on_duty_slots', color: '#22c55e' }, // Green
]

/* Helper to parse JSON slots */
function getSlots(log, key) {
  try {
    const slots = typeof log[key] === 'string' ? JSON.parse(log[key]) : log[key]
    return Array.isArray(slots) ? slots : Array(96).fill(false)
  } catch {
    return Array(96).fill(false)
  }
}

export default function ELDLogSheet({ log }) {
  if (!log) return null

  // Process remarks
  let remarks = []
  try {
    remarks = typeof log.remarks === 'string' ? JSON.parse(log.remarks) : log.remarks
    if (!Array.isArray(remarks)) remarks = [remarks]
  } catch {
    remarks = [log.remarks]
  }

  return (
    <div className="eld-sheet mb-6">
      <div className="eld-sheet-header">
        <div className="eld-sheet-title">{log.date_label}</div>
        <div className="text-sm text-slate-400">Day {log.day_index + 1}</div>
      </div>

      <div className="eld-grid-wrapper">
        <div style={{ minWidth: '800px', paddingBottom: '1rem' }}>

          {/* Time Header */}
          <div className="flex" style={{ marginLeft: '80px', marginBottom: '4px' }}>
            {Array.from({ length: 25 }).map((_, i) => (
              <div key={i} className="text-xs text-slate-500" style={{ width: i === 24 ? '0' : '3.125%' }}>
                <div style={{ transform: 'translateX(-50%)' }}>
                  {i % 3 === 0 ? `${i.toString().padStart(2, '0')}:00` : '|'}
                </div>
              </div>
            ))}
          </div>

          {/* Grid Rows */}
          {ROW_LABELS.map((row, rowIdx) => {
            const slots = getSlots(log, row.key)
            return (
              <div key={row.key} className="flex items-stretch" style={{ height: '32px', borderBottom: rowIdx === 3 ? 'none' : '1px solid rgba(148,163,184,0.1)' }}>
                {/* Row Label */}
                <div className="flex-shrink-0 flex justify-end items-center pr-3" style={{ width: '80px' }}>
                  <span className="text-xs font-bold text-slate-300">{row.label}</span>
                </div>

                {/* 96 Slots (24 hours * 4 quarters) */}
                <div className="flex-grow flex relative bg-slate-800/50" style={{ borderLeft: '1px solid rgba(148,163,184,0.2)', borderRight: '1px solid rgba(148,163,184,0.2)' }}>

                  {/* Vertical Hour Dividers */}
                  <div className="absolute inset-0 flex pointer-events-none">
                    {Array.from({ length: 24 }).map((_, i) => (
                      <div key={i} style={{ width: '4.1666%', borderRight: '1px solid rgba(148,163,184,0.1)' }} />
                    ))}
                  </div>

                  {/* Slot Blocks */}
                  {slots.slice(0, 96).map((isActive, i) => (
                    <div
                      key={i}
                      style={{
                        width: '1.0416%', // 100% / 96 slots
                        backgroundColor: isActive ? row.color : 'transparent',
                        height: isActive ? '16px' : '100%',
                        marginTop: isActive ? '8px' : '0'
                      }}
                    />
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Remarks */}
      {remarks && remarks.length > 0 && remarks[0] && (
        <div className="px-5 py-3 text-sm text-slate-300 border-t border-indigo-500/10">
          <span className="font-semibold text-slate-400 mr-2">Remarks:</span>
          {remarks.join(' | ')}
        </div>
      )}

      {/* Daily Totals */}
      <div className="eld-totals">
        <div className="text-xs font-bold uppercase text-slate-500 tracking-wider mt-1 mr-2">Totals:</div>
        <div className="eld-total-item">
          <div className="eld-dot" style={{ backgroundColor: ROW_LABELS[0].color }} />
          <span>Off Duty: {log.total_off_duty_hours?.toFixed(2)}h</span>
        </div>
        <div className="eld-total-item">
          <div className="eld-dot" style={{ backgroundColor: ROW_LABELS[1].color }} />
          <span>Sleeper: {log.total_sleeper_hours?.toFixed(2)}h</span>
        </div>
        <div className="eld-total-item">
          <div className="eld-dot" style={{ backgroundColor: ROW_LABELS[2].color }} />
          <span>Driving: {log.total_driving_hours?.toFixed(2)}h</span>
        </div>
        <div className="eld-total-item">
          <div className="eld-dot" style={{ backgroundColor: ROW_LABELS[3].color }} />
          <span>On Duty: {log.total_on_duty_hours?.toFixed(2)}h</span>
        </div>
      </div>
    </div>
  )
}


