import { useState } from 'react'
import TripForm from './components/TripForm'
import MapView from './components/MapView'
import SummaryBar from './components/SummaryBar'
import ELDLogSheet from './components/ELDLogSheet'
import { createTrip, downloadTripPDF } from './services/api'

export default function App() {
  const [trip, setTrip] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handlePlanTrip = async (payload) => {
    setLoading(true)
    setError(null)
    setTrip(null)
    try {
      const data = await createTrip(payload)
      setTrip(data)
    } catch (err) {
      console.error(err)
      setError(err.response?.data?.error || 'Failed to plan trip. Please check addresses and try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadPDF = () => {
    if (trip && trip.id) {
      downloadTripPDF(trip.id)
    }
  }

  return (
    <div className="app-shell">
      {/* Navbar */}
      <nav className="navbar">
        <div className="navbar-brand">
          <span>🚛</span> ELD Trip Planner
        </div>
        <div className="navbar-badge">BETA v1.0</div>
      </nav>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {!trip && (
          <header className="hero">
            <h1>Plan HOS-Compliant Routes</h1>
            <p>Calculate driving time, insert mandatory rest stops, and generate ELD log sheets automatically.</p>
          </header>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left Column: Form */}
          <div className="lg:col-span-1">
            <div className="glass-card sticky top-24">
              <h2 className="section-title">Trip Details</h2>
              
              {error && (
                <div className="alert-error mb-5">
                  {error}
                </div>
              )}

              <TripForm onSubmit={handlePlanTrip} loading={loading} />
            </div>
          </div>

          {/* Right Column: Map & Results */}
          <div className="lg:col-span-2">
            
            {loading && !trip && (
              <div className="glass-card loading-overlay" style={{ minHeight: '480px' }}>
                <div className="loading-spinner-lg" />
                <p className="text-slate-400 font-medium tracking-wide">Computing HOS-compliant route...</p>
              </div>
            )}

            {!loading && !trip && (
              <div className="glass-card flex items-center justify-center text-slate-500" style={{ minHeight: '480px', borderStyle: 'dashed', borderWidth: '2px' }}>
                Enter trip details to view map and log sheets
              </div>
            )}

            {trip && (
              <div className="space-y-6">
                <SummaryBar trip={trip} />
                
                <div className="glass-card p-4">
                  <h2 className="section-title px-2">Interactive Route Map</h2>
                  <MapView trip={trip} />
                </div>

                <div className="glass-card">
                  <div className="flex items-center justify-between mb-6">
                    <h2 className="section-title mb-0">Generated Log Sheets</h2>
                    <button onClick={handleDownloadPDF} className="btn-pdf">
                      <span>📄</span> Download PDF
                    </button>
                  </div>
                  
                  {trip.log_sheets && trip.log_sheets.length > 0 ? (
                    trip.log_sheets.map((log) => (
                      <ELDLogSheet key={log.id} log={log} />
                    ))
                  ) : (
                    <div className="text-center py-8 text-slate-500">No log sheets generated.</div>
                  )}
                </div>
              </div>
            )}
            
          </div>
        </div>
      </main>
    </div>
  )
}
