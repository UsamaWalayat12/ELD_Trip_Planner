import { useState, useRef, useCallback, useEffect } from 'react'
import { searchAddresses } from '../services/api'

/* ── Debounce hook ─────────────────────────────────────────────────────── */
function useDebounce(fn, delay = 400) {
  const timer = useRef(null)
  return useCallback((...args) => {
    clearTimeout(timer.current)
    timer.current = setTimeout(() => fn(...args), delay)
  }, [fn, delay])
}

/* ── Single autocomplete field ─────────────────────────────────────────── */
function LocationField({ id, label, value, onChange, onSelect, error, placeholder }) {
  const [suggestions, setSuggestions] = useState([])
  const [loading, setLoading]         = useState(false)
  const [open, setOpen]               = useState(false)
  const wrapperRef = useRef(null)

  const fetchSuggestions = async (q) => {
    if (q.length < 3) { setSuggestions([]); setOpen(false); return }
    setLoading(true)
    try {
      const results = await searchAddresses(q)
      setSuggestions(results)
      setOpen(results.length > 0)
    } catch {
      setSuggestions([])
    } finally {
      setLoading(false)
    }
  }

  const debouncedFetch = useDebounce(fetchSuggestions, 400)

  const handleChange = (e) => {
    onChange(e.target.value)
    debouncedFetch(e.target.value)
  }

  const handleSelect = (item) => {
    onSelect(item)
    setSuggestions([])
    setOpen(false)
  }

  /* Close dropdown on outside click */
  useEffect(() => {
    const handler = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div className="mb-5" ref={wrapperRef}>
      <label htmlFor={id} className="form-label">{label}</label>
      <div className="autocomplete-wrapper">
        <input
          id={id}
          type="text"
          className="form-input"
          value={value}
          onChange={handleChange}
          placeholder={placeholder}
          autoComplete="off"
        />
        {loading && (
          <span style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)' }}>
            <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
          </span>
        )}
        {open && suggestions.length > 0 && (
          <div className="autocomplete-dropdown">
            {suggestions.map((s, i) => (
              <div
                key={i}
                className="autocomplete-item"
                onMouseDown={() => handleSelect(s)}
              >
                <span style={{ marginRight: '0.5rem', opacity: 0.5 }}>📍</span>
                {s.display_name}
              </div>
            ))}
          </div>
        )}
      </div>
      {error && <p className="form-error">{error}</p>}
    </div>
  )
}

/* ── Main TripForm Component ────────────────────────────────────────────── */
export default function TripForm({ onSubmit, loading }) {
  const [fields, setFields] = useState({
    current_location:   '',
    pickup_location:    '',
    dropoff_location:   '',
    current_cycle_used: '',
  })
  const [coords, setCoords] = useState({
    current: null,
    pickup:  null,
    dropoff: null,
  })
  const [errors, setErrors] = useState({})

  const setText = (key) => (val) =>
    setFields(prev => ({ ...prev, [key]: val }))

  const setCoord = (key) => (item) => {
    setFields(prev => ({ ...prev, [key + '_location']: item.display_name }))
    setCoords(prev => ({ ...prev, [key]: item }))
  }

  /* ── Validation ──────────────────────────────────────────────────────── */
  const validate = () => {
    const errs = {}
    if (fields.current_location.trim().length < 3)
      errs.current_location = 'Enter at least 3 characters.'
    if (fields.pickup_location.trim().length < 3)
      errs.pickup_location = 'Enter at least 3 characters.'
    if (fields.dropoff_location.trim().length < 3)
      errs.dropoff_location = 'Enter at least 3 characters.'
    if (fields.current_location.trim() === fields.pickup_location.trim() && fields.pickup_location.trim())
      errs.pickup_location = 'Cannot be the same as Current Location.'
    if (fields.pickup_location.trim() === fields.dropoff_location.trim() && fields.dropoff_location.trim())
      errs.dropoff_location = 'Cannot be the same as Pickup Location.'
    const cycle = parseFloat(fields.current_cycle_used)
    if (isNaN(cycle) || cycle < 0)
      errs.current_cycle_used = 'Enter a value between 0 and 69.99.'
    if (cycle >= 70)
      errs.current_cycle_used = 'Cycle exhausted — cannot exceed 70 hours.'
    return errs
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length > 0) { setErrors(errs); return }
    setErrors({})
    onSubmit({
      current_location:   fields.current_location.trim(),
      pickup_location:    fields.pickup_location.trim(),
      dropoff_location:   fields.dropoff_location.trim(),
      current_cycle_used: parseFloat(fields.current_cycle_used),
    })
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <LocationField
        id="current-location"
        label="🚛 Current Location"
        value={fields.current_location}
        onChange={setText('current_location')}
        onSelect={setCoord('current')}
        error={errors.current_location}
        placeholder="e.g. Chicago, IL"
      />
      <LocationField
        id="pickup-location"
        label="📦 Pickup Location"
        value={fields.pickup_location}
        onChange={setText('pickup_location')}
        onSelect={setCoord('pickup')}
        error={errors.pickup_location}
        placeholder="e.g. Indianapolis, IN"
      />
      <LocationField
        id="dropoff-location"
        label="🏁 Dropoff Location"
        value={fields.dropoff_location}
        onChange={setText('dropoff_location')}
        onSelect={setCoord('dropoff')}
        error={errors.dropoff_location}
        placeholder="e.g. Columbus, OH"
      />

      {/* Cycle Hours */}
      <div className="mb-6">
        <label htmlFor="cycle-hours" className="form-label">⏱ Current Cycle Used (hrs)</label>
        <input
          id="cycle-hours"
          type="number"
          step="0.1"
          min="0"
          max="69.99"
          className="form-input"
          value={fields.current_cycle_used}
          onChange={(e) => setFields(p => ({ ...p, current_cycle_used: e.target.value }))}
          placeholder="0.0 – 69.99"
        />
        {errors.current_cycle_used && (
          <p className="form-error">{errors.current_cycle_used}</p>
        )}
        <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.35rem' }}>
          Hours already used in your current 70-hr / 8-day cycle.
        </p>
      </div>

      <button
        id="plan-trip-btn"
        type="submit"
        className="btn-primary"
        disabled={loading}
      >
        {loading ? (
          <><span className="spinner" /> Computing Route…</>
        ) : (
          <><span>🗺️</span> Plan Trip & Generate Log Sheets</>
        )}
      </button>
    </form>
  )
}
