"""
Phase 5 — ReportLab PDF Generator
Generates ELD-compliant log sheet PDFs — one page per calendar day.
"""
import io
import math
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Table, TableStyle


# ── Color palette ─────────────────────────────────────────────────────────────
COLOR_DRIVING   = colors.HexColor("#2563EB")   # Blue
COLOR_ON_DUTY   = colors.HexColor("#16A34A")   # Green
COLOR_SLEEPER   = colors.HexColor("#7C3AED")   # Purple
COLOR_OFF_DUTY  = colors.HexColor("#D1D5DB")   # Light grey
COLOR_GRID_LINE = colors.HexColor("#9CA3AF")   # Grey
COLOR_HEADER_BG = colors.HexColor("#1E293B")   # Dark slate
COLOR_HEADER_FG = colors.white

# ELD grid layout constants
GRID_LEFT   = 1.2 * inch
GRID_RIGHT  = 10.0 * inch
GRID_WIDTH  = GRID_RIGHT - GRID_LEFT
SLOT_WIDTH  = GRID_WIDTH / 96            # 96 × 15-min = 24 hrs
ROW_HEIGHT  = 0.35 * inch
LABEL_COL_W = 1.1 * inch

DUTY_ROWS = [
    ("OFF DUTY",  "OFF_DUTY",  COLOR_OFF_DUTY),
    ("SLEEPER",   "SLEEPER",   COLOR_SLEEPER),
    ("DRIVING",   "DRIVING",   COLOR_DRIVING),
    ("ON DUTY",   "ON_DUTY",   COLOR_ON_DUTY),
]


def _draw_header(c, trip, day_index, date_label, page_width, page_height):
    """Draw the top header band."""
    header_h = 0.9 * inch
    c.setFillColor(COLOR_HEADER_BG)
    c.rect(0, page_height - header_h, page_width, header_h, fill=1, stroke=0)

    c.setFillColor(COLOR_HEADER_FG)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(0.3 * inch, page_height - 0.35 * inch,
                 "ELD LOG SHEET — DRIVER DAILY LOG")

    c.setFont("Helvetica", 9)
    info_y = page_height - 0.60 * inch
    c.drawString(0.3 * inch, info_y,
                 f"From: {trip.current_location}   |   Pickup: {trip.pickup_location}   |   Dropoff: {trip.dropoff_location}")
    c.drawString(0.3 * inch, info_y - 0.18 * inch,
                 f"Cycle Hours Used: {trip.current_cycle_used} hrs   |   Trip ID: #{trip.pk}   |   {date_label}")

    # Page number top-right
    c.setFont("Helvetica", 8)
    c.drawRightString(page_width - 0.3 * inch, page_height - 0.35 * inch,
                      f"Day {day_index + 1}")


def _draw_time_axis(c, grid_top_y):
    """Draw the 24-hour time axis above the grid."""
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.black)
    for hour in range(25):
        x = GRID_LEFT + hour * (SLOT_WIDTH * 4)
        label = f"{hour % 24:02d}:00" if hour % 3 == 0 else ""
        if label:
            c.drawCentredString(x, grid_top_y + 4, label)
        # Tick mark
        c.setStrokeColor(COLOR_GRID_LINE)
        c.setLineWidth(0.5)
        c.line(x, grid_top_y, x, grid_top_y + 3)


def _draw_grid_row(c, row_label, slot_color, slots, row_y):
    """Draw one duty-status row of the ELD grid."""
    # Row label
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.black)
    c.drawRightString(GRID_LEFT - 5, row_y + ROW_HEIGHT * 0.3, row_label)

    # Row background
    c.setFillColor(colors.white)
    c.setStrokeColor(COLOR_GRID_LINE)
    c.setLineWidth(0.5)
    c.rect(GRID_LEFT, row_y, GRID_WIDTH, ROW_HEIGHT, fill=1, stroke=1)

    # Filled slots
    c.setFillColor(slot_color)
    c.setStrokeColor(slot_color)
    in_block = False
    block_start = 0

    for i, active in enumerate(slots + [False]):   # sentinel
        if active and not in_block:
            block_start = i
            in_block = True
        elif not active and in_block:
            x = GRID_LEFT + block_start * SLOT_WIDTH
            w = (i - block_start) * SLOT_WIDTH
            c.rect(x, row_y + 1, w, ROW_HEIGHT - 2, fill=1, stroke=0)
            in_block = False

    # Vertical hour lines over the row
    c.setStrokeColor(COLOR_GRID_LINE)
    c.setLineWidth(0.3)
    for hour in range(25):
        x = GRID_LEFT + hour * SLOT_WIDTH * 4
        c.line(x, row_y, x, row_y + ROW_HEIGHT)


def _draw_totals(c, log_sheet, grid_bottom_y):
    """Draw daily totals below the grid."""
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.black)

    totals = [
        ("Off Duty", log_sheet.total_off_duty_hours, COLOR_OFF_DUTY),
        ("Sleeper",  log_sheet.total_sleeper_hours,  COLOR_SLEEPER),
        ("Driving",  log_sheet.total_driving_hours,  COLOR_DRIVING),
        ("On Duty",  log_sheet.total_on_duty_hours,  COLOR_ON_DUTY),
    ]
    x = GRID_LEFT
    y = grid_bottom_y - 0.25 * inch
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, "Daily Totals:")
    x += 1.0 * inch
    c.setFont("Helvetica", 9)
    for label, hrs, col in totals:
        c.setFillColor(col)
        c.rect(x, y, 0.12 * inch, 0.12 * inch, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.drawString(x + 0.16 * inch, y, f"{label}: {hrs:.2f} hrs")
        x += 1.8 * inch


def _draw_remarks(c, remarks_text, y):
    """Draw remarks section."""
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.black)
    c.drawString(GRID_LEFT, y, "Remarks / Events:")
    c.setFont("Helvetica", 8)
    c.drawString(GRID_LEFT + 1.1 * inch, y, remarks_text[:180])


def generate_trip_pdf(trip, log_sheets) -> bytes:
    """
    Generate a multi-page ELD PDF for the given trip.

    Args:
        trip: Trip model instance
        log_sheets: queryset of ELDLogSheet ordered by day_index

    Returns:
        bytes: PDF binary content
    """
    import json
    buffer = io.BytesIO()
    page_width, page_height = landscape(letter)
    c = rl_canvas.Canvas(buffer, pagesize=landscape(letter))
    c.setTitle(f"ELD Log Sheet — Trip #{trip.pk}")
    c.setAuthor("ELD Trip Planner")
    c.setSubject("ELD Driver Daily Log")

    for log in log_sheets:
        # Parse slots
        slot_data = {
            "OFF_DUTY": json.loads(log.off_duty_slots or "[]") or [False] * 96,
            "SLEEPER":  json.loads(log.sleeper_slots  or "[]") or [False] * 96,
            "DRIVING":  json.loads(log.driving_slots  or "[]") or [False] * 96,
            "ON_DUTY":  json.loads(log.on_duty_slots  or "[]") or [False] * 96,
        }
        # Pad to 96 if shorter
        for k in slot_data:
            while len(slot_data[k]) < 96:
                slot_data[k].append(False)

        # ── Header ──────────────────────────────────────────────────────
        _draw_header(c, trip, log.day_index, log.date_label, page_width, page_height)

        # ── Time axis ───────────────────────────────────────────────────
        grid_top_y = page_height - 1.5 * inch
        _draw_time_axis(c, grid_top_y)

        # ── Grid rows ───────────────────────────────────────────────────
        current_y = grid_top_y - ROW_HEIGHT
        for row_label, status_key, row_color in DUTY_ROWS:
            slots = slot_data[status_key]
            _draw_grid_row(c, row_label, row_color, slots, current_y)
            current_y -= ROW_HEIGHT

        # ── Totals ──────────────────────────────────────────────────────
        _draw_totals(c, log, current_y)

        # ── Remarks ─────────────────────────────────────────────────────
        remarks = json.loads(log.remarks or "[]") if log.remarks.startswith("[") else log.remarks
        if isinstance(remarks, list):
            remarks_text = " | ".join(remarks)
        else:
            remarks_text = str(remarks)
        _draw_remarks(c, remarks_text, current_y - 0.5 * inch)

        # ── Footer ──────────────────────────────────────────────────────
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.grey)
        c.drawCentredString(page_width / 2, 0.25 * inch,
                            "ELD Trip Planner & Log Sheet Generator | Generated automatically | For demonstration purposes")

        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer.read()
