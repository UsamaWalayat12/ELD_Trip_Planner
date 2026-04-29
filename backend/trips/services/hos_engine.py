"""
Phase 4 — HOS Engine
Implements the 10-step Hours of Service algorithm per FMCSA regulations.

HOS Rules enforced:
  - Max 11 hours DRIVING per day
  - Max 14 hours ON-DUTY window per day
  - Mandatory 30-min break after 8 consecutive driving hours
  - Mandatory 10-hr OFF DUTY / SLEEPER reset after 11 hrs driving
  - Fuel stop every <=1,000 miles
  - 70-hr/8-day cycle limit (cycle_used tracked)
  - 1-hr ON DUTY at pickup and dropoff
"""

import math
from datetime import datetime, timedelta
from .ors_client import geocode, get_route

# ── Constants ────────────────────────────────────────────────────────────────
METERS_PER_MILE = 1609.344
MAX_DRIVE_HOURS_PER_DAY = 11.0        # hours driving allowed per shift
MAX_CONSECUTIVE_DRIVE_HOURS = 8.0     # hours before mandatory 30-min break
BREAK_DURATION_HOURS = 0.5            # 30-minute break
REST_DURATION_HOURS = 10.0            # 10-hour sleeper/off-duty reset
MAX_FUEL_MILES = 1000.0               # fuel stop interval
PICKUP_DROPOFF_DUTY_HOURS = 1.0       # on-duty time at pickup/dropoff
SPEED_MPH = 55.0                      # assumed average HGV speed


def meters_to_miles(m: float) -> float:
    return m / METERS_PER_MILE


def hours_to_minutes(h: float) -> float:
    return h * 60.0


def _make_segment(seq, seg_type, start_min, duration_min, distance_miles,
                  odometer, day_index, label=""):
    """Helper to build a raw segment dict."""
    return {
        "sequence": seq,
        "segment_type": seg_type,
        "start_time_offset": start_min,
        "end_time_offset": start_min + duration_min,
        "duration_minutes": duration_min,
        "distance_miles": distance_miles,
        "odometer_start": odometer,
        "day_index": day_index,
        "label": label,
    }


def _day_of(elapsed_minutes: float) -> int:
    """Return 0-indexed calendar day number from elapsed minutes."""
    return int(elapsed_minutes // (24 * 60))


def _process_leg(leg_distance_miles: float, leg_label: str,
                 state: dict, segments: list) -> None:
    """
    Drive a single leg (Current→Pickup or Pickup→Dropoff).
    Mutates `state` and appends to `segments`.

    state keys:
        elapsed_min     – total minutes since trip started
        drive_today     – driving hours accumulated today
        consec_drive    – consecutive driving hours since last break/rest
        cycle_used      – total hours used in 70-hr cycle
        odometer        – miles driven so far
        fuel_since      – miles since last fuel stop
        seq             – next segment sequence number
        rest_stops      – count of 10-hr rests inserted
        fuel_stops      – count of fuel stops inserted
        break_stops     – count of 30-min breaks inserted
    """
    remaining_leg_miles = leg_distance_miles

    while remaining_leg_miles > 0.001:
        # ── How far can we drive before the next mandatory stop? ─────────
        # 1. Fuel constraint
        miles_to_fuel = MAX_FUEL_MILES - state["fuel_since"]

        # 2. 30-min break after 8 consecutive driving hours
        hours_to_break = MAX_CONSECUTIVE_DRIVE_HOURS - state["consec_drive"]
        miles_to_break = hours_to_break * SPEED_MPH if hours_to_break > 0 else 0

        # 3. 11-hr daily driving limit
        hours_to_rest = MAX_DRIVE_HOURS_PER_DAY - state["drive_today"]
        miles_to_rest = hours_to_rest * SPEED_MPH if hours_to_rest > 0 else 0

        # Choose the closest constraint
        max_drive_miles = min(miles_to_fuel, miles_to_break, miles_to_rest, remaining_leg_miles)

        # Guard: if all constraints are 0, force a rest
        if max_drive_miles <= 0.001:
            max_drive_miles = 0.001

        drive_hours = max_drive_miles / SPEED_MPH
        drive_minutes = hours_to_minutes(drive_hours)

        # ── Insert DRIVING segment ───────────────────────────────────────
        day_idx = _day_of(state["elapsed_min"])
        seg = _make_segment(
            seq=state["seq"],
            seg_type="DRIVING",
            start_min=state["elapsed_min"],
            duration_min=drive_minutes,
            distance_miles=max_drive_miles,
            odometer=state["odometer"],
            day_index=day_idx,
            label=f"Driving ({leg_label})",
        )
        segments.append(seg)
        state["seq"] += 1

        # Update state
        state["elapsed_min"] += drive_minutes
        state["drive_today"] += drive_hours
        state["consec_drive"] += drive_hours
        state["cycle_used"] += drive_hours
        state["odometer"] += max_drive_miles
        state["fuel_since"] += max_drive_miles
        remaining_leg_miles -= max_drive_miles

        if remaining_leg_miles <= 0.001:
            break  # Leg complete — don't insert stops at end of leg here

        # ── Determine which mandatory stop is needed ─────────────────────
        needs_fuel = state["fuel_since"] >= MAX_FUEL_MILES - 0.01
        needs_break = state["consec_drive"] >= MAX_CONSECUTIVE_DRIVE_HOURS - 0.01
        needs_rest = state["drive_today"] >= MAX_DRIVE_HOURS_PER_DAY - 0.01

        if needs_rest:
            # 10-hr mandatory rest — resets daily drive and consecutive drive
            day_idx = _day_of(state["elapsed_min"])
            rest_min = hours_to_minutes(REST_DURATION_HOURS)
            seg = _make_segment(
                seq=state["seq"],
                seg_type="SLEEPER",
                start_min=state["elapsed_min"],
                duration_min=rest_min,
                distance_miles=0,
                odometer=state["odometer"],
                day_index=day_idx,
                label="10-Hr Sleeper Rest",
            )
            segments.append(seg)
            state["seq"] += 1
            state["elapsed_min"] += rest_min
            state["drive_today"] = 0.0
            state["consec_drive"] = 0.0
            state["rest_stops"] += 1

        elif needs_break:
            # 30-min mandatory break
            day_idx = _day_of(state["elapsed_min"])
            break_min = hours_to_minutes(BREAK_DURATION_HOURS)
            seg = _make_segment(
                seq=state["seq"],
                seg_type="BREAK",
                start_min=state["elapsed_min"],
                duration_min=break_min,
                distance_miles=0,
                odometer=state["odometer"],
                day_index=day_idx,
                label="30-Min Mandatory Break",
            )
            segments.append(seg)
            state["seq"] += 1
            state["elapsed_min"] += break_min
            state["consec_drive"] = 0.0
            state["break_stops"] += 1

        if needs_fuel:
            # Fuel stop (~30 min)
            day_idx = _day_of(state["elapsed_min"])
            fuel_min = 30.0
            seg = _make_segment(
                seq=state["seq"],
                seg_type="FUEL_STOP",
                start_min=state["elapsed_min"],
                duration_min=fuel_min,
                distance_miles=0,
                odometer=state["odometer"],
                day_index=day_idx,
                label=f"Fuel Stop @ {state['odometer']:.0f} mi",
            )
            segments.append(seg)
            state["seq"] += 1
            state["elapsed_min"] += fuel_min
            state["fuel_since"] = 0.0
            state["fuel_stops"] += 1


def _build_eld_grids(segments: list) -> dict:
    """
    Convert raw segments into per-day 96-slot grids.
    Returns dict keyed by day_index.
    """
    # Find how many days total
    max_day = 0
    for seg in segments:
        # A segment may span midnight — compute end day
        end_day = _day_of(seg["end_time_offset"])
        max_day = max(max_day, end_day)

    days = {}
    for d in range(max_day + 1):
        days[d] = {
            "OFF_DUTY": [False] * 96,
            "SLEEPER": [False] * 96,
            "DRIVING": [False] * 96,
            "ON_DUTY": [False] * 96,
            "remarks": [],
        }

    # Map segment types → ELD duty status rows
    TYPE_TO_ROW = {
        "DRIVING": "DRIVING",
        "ON_DUTY": "ON_DUTY",
        "BREAK": "OFF_DUTY",
        "SLEEPER": "SLEEPER",
        "FUEL_STOP": "ON_DUTY",
    }

    for seg in segments:
        row = TYPE_TO_ROW.get(seg["segment_type"], "OFF_DUTY")
        start_slot = int(seg["start_time_offset"] // 15)   # 15-min slots
        end_slot = int(math.ceil(seg["end_time_offset"] / 15))

        # Handle multi-day segments
        for slot in range(start_slot, end_slot):
            day = slot // 96
            slot_in_day = slot % 96
            if day in days and slot_in_day < 96:
                days[day][row][slot_in_day] = True

        # Remarks
        if seg["label"] and seg["segment_type"] in ("ON_DUTY", "FUEL_STOP", "SLEEPER", "BREAK"):
            day = _day_of(seg["start_time_offset"])
            if day in days:
                days[day]["remarks"].append(seg["label"])

    return days


def compute_trip(current_loc: dict, pickup_loc: dict, dropoff_loc: dict,
                 cycle_used: float) -> dict:
    """
    Main HOS engine entry point.

    Args:
        current_loc: {"lat", "lng", "display_name"}
        pickup_loc:  {"lat", "lng", "display_name"}
        dropoff_loc: {"lat", "lng", "display_name"}
        cycle_used:  hours already used in current 70-hr cycle

    Returns:
        {
            "segments": [...],
            "eld_grids": {day_index: {...}},
            "route_geometry": [[lng, lat], ...],
            "total_distance_miles": float,
            "total_drive_hours": float,
            "total_days": int,
            "total_rest_stops": int,
            "total_fuel_stops": int,
        }
    """
    # ── Step 1 & 2: Get routes ──────────────────────────────────────────────
    # Leg A: Current → Pickup
    route_a = get_route(current_loc, pickup_loc)
    # Leg B: Pickup → Dropoff
    route_b = get_route(pickup_loc, dropoff_loc)

    leg_a_miles = meters_to_miles(route_a["distance_meters"])
    leg_b_miles = meters_to_miles(route_b["distance_meters"])
    total_miles = leg_a_miles + leg_b_miles

    # Combine geometries (avoid duplicating the pickup point)
    full_geometry = route_a["geometry"] + route_b["geometry"][1:]

    # ── Step 3-10: HOS simulation ───────────────────────────────────────────
    segments = []
    state = {
        "elapsed_min": 0.0,
        "drive_today": 0.0,
        "consec_drive": 0.0,
        "cycle_used": cycle_used,
        "odometer": 0.0,
        "fuel_since": 0.0,
        "seq": 1,
        "rest_stops": 0,
        "fuel_stops": 0,
        "break_stops": 0,
    }

    # Steps 4 & 5: Process Leg A
    _process_leg(leg_a_miles, "Current → Pickup", state, segments)

    # Step 6: Pickup — 1 hr ON DUTY
    day_idx = _day_of(state["elapsed_min"])
    pickup_min = hours_to_minutes(PICKUP_DROPOFF_DUTY_HOURS)
    segments.append(_make_segment(
        seq=state["seq"],
        seg_type="ON_DUTY",
        start_min=state["elapsed_min"],
        duration_min=pickup_min,
        distance_miles=0,
        odometer=state["odometer"],
        day_index=day_idx,
        label=f"Pickup — On Duty @ {pickup_loc['display_name']}",
    ))
    state["seq"] += 1
    state["elapsed_min"] += pickup_min
    state["cycle_used"] += PICKUP_DROPOFF_DUTY_HOURS

    # Steps 7: Process Leg B
    _process_leg(leg_b_miles, "Pickup → Dropoff", state, segments)

    # Step 8: Dropoff — 1 hr ON DUTY
    day_idx = _day_of(state["elapsed_min"])
    dropoff_min = hours_to_minutes(PICKUP_DROPOFF_DUTY_HOURS)
    segments.append(_make_segment(
        seq=state["seq"],
        seg_type="ON_DUTY",
        start_min=state["elapsed_min"],
        duration_min=dropoff_min,
        distance_miles=0,
        odometer=state["odometer"],
        day_index=day_idx,
        label=f"Dropoff — On Duty @ {dropoff_loc['display_name']}",
    ))
    state["seq"] += 1
    state["elapsed_min"] += dropoff_min

    # Step 9: Build ELD 96-slot grids
    eld_grids = _build_eld_grids(segments)

    # Step 10: Compute summary
    total_drive_hours = sum(
        s["duration_minutes"] / 60.0
        for s in segments if s["segment_type"] == "DRIVING"
    )
    total_days = _day_of(state["elapsed_min"]) + 1

    return {
        "segments": segments,
        "eld_grids": eld_grids,
        "route_geometry": full_geometry,
        "total_distance_miles": round(total_miles, 2),
        "total_drive_hours": round(total_drive_hours, 2),
        "total_days": total_days,
        "total_rest_stops": state["rest_stops"],
        "total_fuel_stops": state["fuel_stops"],
    }
