# ELD Trip Planner & Log Sheet Generator
## Software Requirements Specification (SRS) v1.0
**Date:** April 2026
**Status:** Confidential — Internal Use Only

---

## 1. Project Overview & Tech Stack

The ELD Trip Planner & Log Sheet Generator is a web application designed to help truck drivers plan their trips while adhering to Hours of Service (HOS) regulations. It calculates routes, inserts mandatory rest and fuel stops, and generates ELD-compliant log sheets.

| Layer | Technology | Install Command / Notes |
| :--- | :--- | :--- |
| **Backend Framework** | Django 4.x | `pip install django` |
| **REST API** | Django REST Framework | `pip install djangorestframework` |
| **CORS** | django-cors-headers | `pip install django-cors-headers` |
| **PDF Generation** | ReportLab | `pip install reportlab` |
| **Env Vars** | python-dotenv | `pip install python-dotenv` |
| **Database** | SQLite 3 (Django ORM) | Built-in — no install. File: `db.sqlite3` |
| **Routing/Geocoding** | OpenRouteService API | Sign up at openrouteservice.org — FREE |
| **Frontend** | React 18 + Vite | `npm create vite@latest frontend -- --template react` |
| **Styling** | Tailwind CSS | `npm install tailwindcss postcss autoprefixer` |
| **Maps** | Leaflet + react-leaflet | `npm install leaflet react-leaflet` |
| **HTTP Client** | Axios | `npm install axios` |
| **Log Drawing** | react-konva OR Canvas API | `npm install react-konva konva` |
| **Map Tiles** | OpenStreetMap (via Leaflet) | FREE — no API key. Tile URL auto-used by Leaflet. |

---

## 2. External APIs Required

The following external APIs are required. All chosen APIs have a FREE tier sufficient for development and demo use.

### 2.1 OpenRouteService API (Primary — Routing + Geocoding)
> 🗺️ **OpenRouteService (ORS)**
> - **Website:** [openrouteservice.org](https://openrouteservice.org)
> - **Free Tier:** 2,000 requests/day
> - **Used For:** Geocoding (Address → Lat/Lng), Directions (HGV routing), Distance/Duration calculation.

### 2.2 OpenStreetMap Tiles (Map Display)
> 🗺️ **OpenStreetMap (OSM)**
> - **API Key:** NOT REQUIRED
> - **Used For:** Rendering the interactive map background.

### 2.3 API Endpoint Summary
| API | Endpoint Used | Purpose | Cost |
| :--- | :--- | :--- | :--- |
| OpenRouteService | `/geocode/search` | Address → Lat/Lng | FREE (2k/day) |
| OpenRouteService | `/geocode/reverse` | Lat/Lng → Address | FREE (2k/day) |
| OpenRouteService | `/v2/directions/driving-hgv` | Route calculation | FREE (2k/day) |
| OpenStreetMap Tiles | `tile.openstreetmap.org` | Map background | FREE — no key |

---

## 3. Database — SQLite via Django ORM

- **Database:** SQLite 3 — Built into Python/Django.
- **File Location:** `./backend/db.sqlite3`
- **Access:** Django ORM (`models.py`) — NO raw SQL.
- **Admin Panel:** Django built-in admin at `/admin`.

---

## 4. Frontend Requirements

### 4.1 Screen 1 — Input Form
| # | Field | Type | Required | Validation |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Current Location | Autocomplete | Yes | Min 3 chars. Must resolve via ORS. |
| 2 | Pickup Location | Autocomplete | Yes | Min 3 chars. Cannot equal Current Location. |
| 3 | Dropoff Location | Autocomplete | Yes | Min 3 chars. Cannot equal Pickup Location. |
| 4 | Current Cycle Used | Number (0.0–70.0) | Yes | Error if ≥ 70: "Cycle exhausted." |

### 4.2 Screen 2 — Interactive Map
| Map Element | Specification |
| :--- | :--- |
| **Route Polyline** | Full driving route drawn as a blue line using ORS data. |
| **Start Marker** | Green pin at Current Location. |
| **Pickup Marker** | Orange pin at Pickup Location. |
| **Dropoff Marker** | Red pin at Dropoff Location. |
| **Fuel Stop Markers** | Yellow gas-pump icons every ≤1,000 miles. |
| **Rest Stop Markers** | Purple bed icons for 10-hr or 30-min breaks. |
| **Route Summary Bar** | Total Distance, Drive Time, Days, and Rest Stops. |

---

## 5. HOS Engine Algorithm (Step-by-Step)

| Step | Logic |
| :--- | :--- |
| 1 | Geocode all 3 addresses using ORS `/geocode/search`. |
| 2 | Call ORS `/v2/directions/driving-hgv` for the full route. |
| 3 | Split route into Leg A (Current → Pickup) and Leg B (Pickup → Dropoff). |
| 4 | Initialize simulation state (cycle hours, elapsed time, etc.). |
| 5 | Process Leg A: Insert fuel stops (1k miles), 30-min breaks (8 hrs), and 10-hr rests (11 hrs). |
| 6 | At pickup: Insert 1-hr ON DUTY segment. |
| 7 | Process Leg B: Same logic as Step 5. |
| 8 | At dropoff: Insert 1-hr ON DUTY segment. Trip complete. |
| 9 | Convert segments to calendar day buckets (96-slot grid). |
| 10 | Serialize to JSON and save to SQLite. |

---

## 6. Django REST API Endpoints

| Method | Endpoint | Name | Description |
| :--- | :--- | :--- | :--- |
| **POST** | `/api/trips/` | Create Trip | Accept inputs, run HOS engine, save, and return data. |
| **GET** | `/api/trips/:id/` | Get Trip | Retrieve trip by ID. |
| **GET** | `/api/trips/:id/logs/` | Get Log Sheets | Return ELDLogSheet records as JSON. |
| **GET** | `/api/trips/:id/logs/pdf/` | Download PDF | Generate and return PDF via ReportLab. |
| **GET** | `/api/geocode/?q=...` | Geocode | Proxy ORS geocode/search. |

---

## 7. Backend Requirements (BE)

| Req ID | Requirement Description | Priority |
| :--- | :--- | :--- |
| BE-1 | Django 4.x project with REST Framework. | High |
| BE-2 | HOS Engine logic implemented in `services/hos_engine.py`. | High |
| BE-3 | Models for Trip, RouteSegment, and ELDLogSheet. | High |
| BE-4 | Integration with OpenRouteService for routing and geocoding. | High |
| BE-5 | PDF generation using ReportLab for log sheets. | High |
| BE-13 | CORS configured for React dev and production domains. | High |
| BE-14 | Django admin panel enabled for record management. | Medium |

---

## 8. Frontend Requirements (FE)

| Req ID | Requirement Description | Priority |
| :--- | :--- | :--- |
| FE-1 | React 18 SPA built with Vite. | High |
| FE-2 | TripForm with real-time validation and loading states. | High |
| FE-3 | Debounced autocomplete for location fields. | High |
| FE-5 | Leaflet.js map rendering route and markers. | High |
| FE-9 | ELDLogSheet component drawing 24-hour grids. | High |
| FE-12 | PDF download trigger for log sheets. | High |
| FE-13 | Tailwind CSS for responsive styling. | High |

---

## 9. Deployment Guide

| Component | Platform | Free Tier | Config |
| :--- | :--- | :--- | :--- |
| **Django Backend** | Railway.app / Render | ✅ Free | Set `ORS_API_KEY`, `DJANGO_SECRET_KEY`. |
| **SQLite Database** | Same as Backend | ✅ Free | Persists on Railway volumes. |
| **React Frontend** | Vercel.com | ✅ Free | Set `VITE_API_BASE_URL`. |
| **ORS API** | openrouteservice.org | ✅ Free | 2,000 req/day. |

### 9.1 Environment Variables
| Service | Variable Name | Example Value |
| :--- | :--- | :--- |
| Backend | `ORS_API_KEY` | `ey123abc...` |
| Backend | `DJANGO_SECRET_KEY` | `django-insecure-xyz...` |
| Backend | `ALLOWED_HOSTS` | `localhost,your-app.railway.app` |
| Frontend | `VITE_API_BASE_URL` | `https://your-api.railway.app` |

---

## 10. Trip Status State Machine

| From Status | To Status | Triggered By | Effect |
| :--- | :--- | :--- | :--- |
| — | `planned` | `POST /api/trips/` | Trip created and HOS computed. |
| `planned` | `error` | API failure | Backend returns 400/500. |
| `planned` | `pdf_downloaded` | `GET .../logs/pdf/` | PDF generated and returned. |

---

**— END OF DOCUMENT —**
*ELD Trip Planner & Log Sheet Generator | SRS v1.0 | April 2026 | Confidential*
