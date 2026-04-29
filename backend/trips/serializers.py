"""
Phase 6 — DRF Serializers
"""
import json
from rest_framework import serializers
from .models import Trip, RouteSegment, ELDLogSheet


class RouteSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RouteSegment
        fields = [
            'id', 'sequence', 'segment_type', 'start_time_offset',
            'end_time_offset', 'duration_minutes', 'distance_miles',
            'odometer_start', 'day_index', 'label',
        ]


class ELDLogSheetSerializer(serializers.ModelSerializer):
    off_duty_slots  = serializers.SerializerMethodField()
    sleeper_slots   = serializers.SerializerMethodField()
    driving_slots   = serializers.SerializerMethodField()
    on_duty_slots   = serializers.SerializerMethodField()
    remarks         = serializers.SerializerMethodField()

    def _parse(self, value):
        try:
            return json.loads(value) if value else []
        except Exception:
            return []

    def get_off_duty_slots(self, obj):  return self._parse(obj.off_duty_slots)
    def get_sleeper_slots(self, obj):   return self._parse(obj.sleeper_slots)
    def get_driving_slots(self, obj):   return self._parse(obj.driving_slots)
    def get_on_duty_slots(self, obj):   return self._parse(obj.on_duty_slots)
    def get_remarks(self, obj):
        try:
            return json.loads(obj.remarks) if obj.remarks and obj.remarks.startswith("[") else obj.remarks
        except Exception:
            return obj.remarks

    class Meta:
        model = ELDLogSheet
        fields = [
            'id', 'day_index', 'date_label',
            'off_duty_slots', 'sleeper_slots', 'driving_slots', 'on_duty_slots',
            'total_off_duty_hours', 'total_sleeper_hours',
            'total_driving_hours', 'total_on_duty_hours',
            'remarks',
        ]


class TripSerializer(serializers.ModelSerializer):
    segments   = RouteSegmentSerializer(many=True, read_only=True)
    log_sheets = ELDLogSheetSerializer(many=True, read_only=True)
    route_geometry = serializers.SerializerMethodField()

    def get_route_geometry(self, obj):
        return obj.get_route_geometry()

    class Meta:
        model = Trip
        fields = [
            'id', 'status', 'error_message',
            'current_location', 'current_lat', 'current_lng',
            'pickup_location', 'pickup_lat', 'pickup_lng',
            'dropoff_location', 'dropoff_lat', 'dropoff_lng',
            'current_cycle_used',
            'total_distance_miles', 'total_drive_hours',
            'total_days', 'total_rest_stops', 'total_fuel_stops',
            'route_geometry',
            'segments', 'log_sheets',
            'created_at',
        ]


class TripCreateSerializer(serializers.Serializer):
    """Input-only serializer for POST /api/trips/"""
    current_location  = serializers.CharField(max_length=500)
    pickup_location   = serializers.CharField(max_length=500)
    dropoff_location  = serializers.CharField(max_length=500)
    current_cycle_used = serializers.FloatField(min_value=0.0, max_value=69.99)

    def validate(self, data):
        if data['current_location'].strip() == data['pickup_location'].strip():
            raise serializers.ValidationError("Current Location and Pickup cannot be the same.")
        if data['pickup_location'].strip() == data['dropoff_location'].strip():
            raise serializers.ValidationError("Pickup and Dropoff cannot be the same.")
        return data
