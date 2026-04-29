"""
Phase 6 — API Views
Endpoints:
  POST /api/trips/                  → Create trip + run HOS engine
  GET  /api/trips/:id/              → Retrieve trip
  GET  /api/trips/:id/logs/         → Get ELD log sheets
  GET  /api/trips/:id/logs/pdf/     → Download PDF
  GET  /api/geocode/?q=...          → Proxy ORS geocode
"""
import json
import math
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Trip, RouteSegment, ELDLogSheet
from .serializers import TripSerializer, ELDLogSheetSerializer, TripCreateSerializer
from .services import ors_client
from .services.hos_engine import compute_trip
from .services.pdf_gen import generate_trip_pdf


# ── Helper ────────────────────────────────────────────────────────────────────

def _save_trip_data(trip: Trip, result: dict):
    """Persist HOS engine result into Trip, RouteSegment, and ELDLogSheet records."""

    # Update Trip aggregate fields
    trip.total_distance_miles = result["total_distance_miles"]
    trip.total_drive_hours    = result["total_drive_hours"]
    trip.total_days           = result["total_days"]
    trip.total_rest_stops     = result["total_rest_stops"]
    trip.total_fuel_stops     = result["total_fuel_stops"]
    trip.set_route_geometry(result["route_geometry"])
    trip.status = "planned"
    trip.save()

    # Save RouteSegments
    seg_objs = []
    for seg in result["segments"]:
        seg_objs.append(RouteSegment(
            trip=trip,
            segment_type=seg["segment_type"],
            sequence=seg["sequence"],
            start_time_offset=seg["start_time_offset"],
            end_time_offset=seg["end_time_offset"],
            duration_minutes=seg["duration_minutes"],
            distance_miles=seg["distance_miles"],
            odometer_start=seg["odometer_start"],
            day_index=seg["day_index"],
            label=seg["label"],
        ))
    RouteSegment.objects.bulk_create(seg_objs)

    # Save ELDLogSheets
    grids = result["eld_grids"]
    log_objs = []
    for day_index, grid in sorted(grids.items()):
        # Calculate totals from slots
        def slots_to_hours(slots):
            return sum(1 for s in slots if s) * 0.25  # each slot = 15 min = 0.25 hr

        off_slots  = grid.get("OFF_DUTY", [False] * 96)
        slp_slots  = grid.get("SLEEPER",  [False] * 96)
        drv_slots  = grid.get("DRIVING",  [False] * 96)
        on_slots   = grid.get("ON_DUTY",  [False] * 96)
        remarks    = grid.get("remarks",  [])

        log_objs.append(ELDLogSheet(
            trip=trip,
            day_index=day_index,
            date_label=f"Day {day_index + 1}",
            off_duty_slots=json.dumps(off_slots),
            sleeper_slots=json.dumps(slp_slots),
            driving_slots=json.dumps(drv_slots),
            on_duty_slots=json.dumps(on_slots),
            total_off_duty_hours=slots_to_hours(off_slots),
            total_sleeper_hours=slots_to_hours(slp_slots),
            total_driving_hours=slots_to_hours(drv_slots),
            total_on_duty_hours=slots_to_hours(on_slots),
            remarks=json.dumps(remarks),
        ))
    ELDLogSheet.objects.bulk_create(log_objs)


# ── Views ─────────────────────────────────────────────────────────────────────

class TripListCreateView(APIView):
    """POST /api/trips/ — Create trip and run HOS engine."""

    def post(self, request):
        serializer = TripCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Geocode all 3 addresses
        try:
            current  = ors_client.geocode(data["current_location"])
            pickup   = ors_client.geocode(data["pickup_location"])
            dropoff  = ors_client.geocode(data["dropoff_location"])
        except Exception as e:
            return Response(
                {"error": f"Geocoding failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create Trip record
        trip = Trip.objects.create(
            current_location  = current["display_name"],
            current_lat       = current["lat"],
            current_lng       = current["lng"],
            pickup_location   = pickup["display_name"],
            pickup_lat        = pickup["lat"],
            pickup_lng        = pickup["lng"],
            dropoff_location  = dropoff["display_name"],
            dropoff_lat       = dropoff["lat"],
            dropoff_lng       = dropoff["lng"],
            current_cycle_used = data["current_cycle_used"],
            status            = "planned",
        )

        # Run HOS engine
        try:
            result = compute_trip(current, pickup, dropoff, data["current_cycle_used"])
        except Exception as e:
            trip.status = "error"
            trip.error_message = str(e)
            trip.save()
            return Response(
                {"error": f"HOS computation failed: {str(e)}", "trip_id": trip.pk},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Persist all computed data
        try:
            _save_trip_data(trip, result)
        except Exception as e:
            trip.status = "error"
            trip.error_message = str(e)
            trip.save()
            return Response(
                {"error": f"Failed to save trip data: {str(e)}", "trip_id": trip.pk},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Reload and return full trip
        trip.refresh_from_db()
        out = TripSerializer(trip)
        return Response(out.data, status=status.HTTP_201_CREATED)


class TripDetailView(APIView):
    """GET /api/trips/:id/ — Retrieve a trip by ID."""

    def get(self, request, trip_id):
        try:
            trip = Trip.objects.prefetch_related('segments', 'log_sheets').get(pk=trip_id)
        except Trip.DoesNotExist:
            return Response({"error": "Trip not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(TripSerializer(trip).data)


class TripLogsView(APIView):
    """GET /api/trips/:id/logs/ — Return ELD log sheets as JSON."""

    def get(self, request, trip_id):
        try:
            trip = Trip.objects.get(pk=trip_id)
        except Trip.DoesNotExist:
            return Response({"error": "Trip not found."}, status=status.HTTP_404_NOT_FOUND)

        logs = trip.log_sheets.order_by('day_index')
        return Response(ELDLogSheetSerializer(logs, many=True).data)


class TripLogsPDFView(APIView):
    """GET /api/trips/:id/logs/pdf/ — Generate and return PDF."""

    def get(self, request, trip_id):
        try:
            trip = Trip.objects.get(pk=trip_id)
        except Trip.DoesNotExist:
            return Response({"error": "Trip not found."}, status=status.HTTP_404_NOT_FOUND)

        logs = trip.log_sheets.order_by('day_index')
        if not logs.exists():
            return Response(
                {"error": "No log sheets found for this trip."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            pdf_bytes = generate_trip_pdf(trip, logs)
        except Exception as e:
            return Response(
                {"error": f"PDF generation failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Update status
        trip.status = "pdf_downloaded"
        trip.save(update_fields=["status"])

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="eld_log_trip_{trip.pk}.pdf"'
        return response


class GeocodeProxyView(APIView):
    """GET /api/geocode/?q=... — Proxy ORS geocode search."""

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 3:
            return Response(
                {"error": "Query must be at least 3 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = ors_client.geocode(query)
            return Response(result)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class GeocodeSearchView(APIView):
    """
    GET /api/geocode/search/?q=... — Return multiple suggestions for autocomplete.
    Returns list of {lat, lng, display_name}.
    """

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 3:
            return Response([], status=status.HTTP_200_OK)

        import requests as req
        from django.conf import settings
        url = "https://api.openrouteservice.org/geocode/search"
        params = {
            "api_key": settings.ORS_API_KEY,
            "text": query,
            "size": 5,
        }
        try:
            resp = req.get(url, params=params, timeout=10)
            resp.raise_for_status()
            features = resp.json().get("features", [])
            results = []
            for f in features:
                coords = f["geometry"]["coordinates"]
                results.append({
                    "lat": coords[1],
                    "lng": coords[0],
                    "display_name": f["properties"].get("label", query),
                })
            return Response(results)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
