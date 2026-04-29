"""
Phase 2 — Django Models
Trip, RouteSegment, ELDLogSheet
"""
from django.db import models
import json


class Trip(models.Model):
    """Stores the top-level trip request and result metadata."""

    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('error', 'Error'),
        ('pdf_downloaded', 'PDF Downloaded'),
    ]

    # Input fields
    current_location = models.CharField(max_length=500)
    current_lat = models.FloatField()
    current_lng = models.FloatField()

    pickup_location = models.CharField(max_length=500)
    pickup_lat = models.FloatField()
    pickup_lng = models.FloatField()

    dropoff_location = models.CharField(max_length=500)
    dropoff_lat = models.FloatField()
    dropoff_lng = models.FloatField()

    current_cycle_used = models.FloatField(help_text="Hours already used in current 70-hr cycle")

    # Computed output fields
    total_distance_miles = models.FloatField(null=True, blank=True)
    total_drive_hours = models.FloatField(null=True, blank=True)
    total_days = models.IntegerField(null=True, blank=True)
    total_rest_stops = models.IntegerField(null=True, blank=True)
    total_fuel_stops = models.IntegerField(null=True, blank=True)

    # Route geometry (GeoJSON LineString coordinates stored as JSON)
    route_geometry = models.TextField(null=True, blank=True, help_text="JSON list of [lng, lat] pairs")

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    error_message = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_route_geometry(self):
        if self.route_geometry:
            return json.loads(self.route_geometry)
        return []

    def set_route_geometry(self, coords):
        self.route_geometry = json.dumps(coords)

    def __str__(self):
        return f"Trip #{self.pk}: {self.current_location} → {self.dropoff_location} [{self.status}]"

    class Meta:
        ordering = ['-created_at']


class RouteSegment(models.Model):
    """
    A single HOS segment within a trip.
    Each segment has a type, start/end time (offset in minutes from trip start),
    and distance in miles.
    """

    SEGMENT_TYPES = [
        ('DRIVING', 'Driving'),
        ('ON_DUTY', 'On Duty (not driving)'),
        ('BREAK', '30-Min Break'),
        ('SLEEPER', '10-Hr Sleeper Berth'),
        ('FUEL_STOP', 'Fuel Stop'),
    ]

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='segments')
    segment_type = models.CharField(max_length=20, choices=SEGMENT_TYPES)
    sequence = models.IntegerField(help_text="Order of this segment in the trip")

    start_time_offset = models.FloatField(help_text="Minutes from trip start when segment begins")
    end_time_offset = models.FloatField(help_text="Minutes from trip start when segment ends")
    duration_minutes = models.FloatField()

    distance_miles = models.FloatField(default=0.0, help_text="Miles covered in this segment (0 for non-driving)")

    # Odometer at start of segment
    odometer_start = models.FloatField(default=0.0)

    # Human-readable label for map/log display
    label = models.CharField(max_length=200, blank=True, default='')

    # Calendar day this segment starts on (0-indexed from trip start)
    day_index = models.IntegerField(default=0)

    def __str__(self):
        return f"[{self.sequence}] {self.segment_type} — {self.duration_minutes:.0f} min @ {self.distance_miles:.1f} mi"

    class Meta:
        ordering = ['sequence']


class ELDLogSheet(models.Model):
    """
    One per calendar day of the trip.
    Stores the 96-slot grid (each slot = 15 minutes) for all 4 duty statuses.
    """

    DUTY_STATUS = [
        ('OFF_DUTY', 'Off Duty'),
        ('SLEEPER', 'Sleeper Berth'),
        ('DRIVING', 'Driving'),
        ('ON_DUTY', 'On Duty (not driving)'),
    ]

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='log_sheets')
    day_index = models.IntegerField(help_text="0-indexed day number from trip start")
    date_label = models.CharField(max_length=50, help_text="Human-readable date e.g. 'Day 1'")

    # 96-slot grid per duty status. Each is a list of booleans (True = active).
    # Stored as JSON strings.
    off_duty_slots = models.TextField(default='[]')
    sleeper_slots = models.TextField(default='[]')
    driving_slots = models.TextField(default='[]')
    on_duty_slots = models.TextField(default='[]')

    # Daily totals (hours)
    total_off_duty_hours = models.FloatField(default=0.0)
    total_sleeper_hours = models.FloatField(default=0.0)
    total_driving_hours = models.FloatField(default=0.0)
    total_on_duty_hours = models.FloatField(default=0.0)

    # Remarks (fuel stops, pickup, dropoff etc.)
    remarks = models.TextField(blank=True, default='')

    def get_slots(self, status):
        mapping = {
            'OFF_DUTY': self.off_duty_slots,
            'SLEEPER': self.sleeper_slots,
            'DRIVING': self.driving_slots,
            'ON_DUTY': self.on_duty_slots,
        }
        raw = mapping.get(status, '[]')
        return json.loads(raw) if raw else [False] * 96

    def set_slots(self, status, slots):
        data = json.dumps(slots)
        if status == 'OFF_DUTY':
            self.off_duty_slots = data
        elif status == 'SLEEPER':
            self.sleeper_slots = data
        elif status == 'DRIVING':
            self.driving_slots = data
        elif status == 'ON_DUTY':
            self.on_duty_slots = data

    def __str__(self):
        return f"Log Sheet — Trip #{self.trip_id} — {self.date_label}"

    class Meta:
        ordering = ['day_index']
