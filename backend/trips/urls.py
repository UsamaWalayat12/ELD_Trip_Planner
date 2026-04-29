"""
Phase 6 — URL Routes for trips app
"""
from django.urls import path
from .views import (
    TripListCreateView,
    TripDetailView,
    TripLogsView,
    TripLogsPDFView,
    GeocodeProxyView,
    GeocodeSearchView,
)

urlpatterns = [
    # Trip endpoints
    path('trips/',                      TripListCreateView.as_view(), name='trip-create'),
    path('trips/<int:trip_id>/',        TripDetailView.as_view(),     name='trip-detail'),
    path('trips/<int:trip_id>/logs/',   TripLogsView.as_view(),       name='trip-logs'),
    path('trips/<int:trip_id>/logs/pdf/', TripLogsPDFView.as_view(), name='trip-logs-pdf'),

    # Geocode endpoints
    path('geocode/',         GeocodeProxyView.as_view(),  name='geocode'),
    path('geocode/search/',  GeocodeSearchView.as_view(), name='geocode-search'),
]
