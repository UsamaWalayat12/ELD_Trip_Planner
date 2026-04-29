"""
Phase 2 — Django Admin Registration
All models registered with rich list displays.
"""
from django.contrib import admin
from .models import Trip, RouteSegment, ELDLogSheet


class RouteSegmentInline(admin.TabularInline):
    model = RouteSegment
    extra = 0
    readonly_fields = ('sequence', 'segment_type', 'start_time_offset',
                       'end_time_offset', 'duration_minutes', 'distance_miles',
                       'odometer_start', 'day_index', 'label')


class ELDLogSheetInline(admin.TabularInline):
    model = ELDLogSheet
    extra = 0
    readonly_fields = ('day_index', 'date_label', 'total_driving_hours',
                       'total_on_duty_hours', 'total_sleeper_hours',
                       'total_off_duty_hours', 'remarks')


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('id', 'current_location', 'pickup_location', 'dropoff_location',
                    'current_cycle_used', 'total_distance_miles', 'total_drive_hours',
                    'total_days', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('current_location', 'pickup_location', 'dropoff_location')
    readonly_fields = ('created_at', 'updated_at', 'total_distance_miles',
                       'total_drive_hours', 'total_days', 'total_rest_stops',
                       'total_fuel_stops', 'route_geometry')
    inlines = [RouteSegmentInline, ELDLogSheetInline]


@admin.register(RouteSegment)
class RouteSegmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'trip', 'sequence', 'segment_type', 'duration_minutes',
                    'distance_miles', 'day_index', 'label')
    list_filter = ('segment_type', 'day_index')
    search_fields = ('trip__current_location', 'label')


@admin.register(ELDLogSheet)
class ELDLogSheetAdmin(admin.ModelAdmin):
    list_display = ('id', 'trip', 'day_index', 'date_label', 'total_driving_hours',
                    'total_on_duty_hours', 'total_sleeper_hours', 'total_off_duty_hours')
    list_filter = ('day_index',)
    search_fields = ('trip__current_location', 'date_label')
