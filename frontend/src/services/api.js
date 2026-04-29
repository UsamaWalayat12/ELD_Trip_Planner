import axios from 'axios'

const BASE = import.meta.env.VITE_API_BASE_URL || ''

const api = axios.create({
  baseURL: `${BASE}/api`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000,
})

/**
 * Search addresses via ORS geocode proxy (returns array of suggestions).
 * @param {string} query
 * @returns {Promise<Array<{lat, lng, display_name}>>}
 */
export async function searchAddresses(query) {
  const res = await api.get('/geocode/search/', { params: { q: query } })
  return res.data
}

/**
 * Create a new trip — runs the full HOS engine on the backend.
 * @param {{current_location, pickup_location, dropoff_location, current_cycle_used}} payload
 * @returns {Promise<object>} Full trip object with segments, log_sheets, geometry
 */
export async function createTrip(payload) {
  const res = await api.post('/trips/', payload)
  return res.data
}

/**
 * Fetch a trip by ID.
 * @param {number} tripId
 */
export async function getTrip(tripId) {
  const res = await api.get(`/trips/${tripId}/`)
  return res.data
}

/**
 * Fetch ELD log sheets for a trip.
 * @param {number} tripId
 */
export async function getTripLogs(tripId) {
  const res = await api.get(`/trips/${tripId}/logs/`)
  return res.data
}

/**
 * Trigger PDF download for a trip.
 * Opens the PDF in a new browser tab.
 * @param {number} tripId
 */
export function downloadTripPDF(tripId) {
  const url = `${BASE}/api/trips/${tripId}/logs/pdf/`
  window.open(url, '_blank')
}
