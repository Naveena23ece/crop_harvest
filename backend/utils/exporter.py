"""
GrainGuard AI - Historical Data & Report Exporter
Provides:
- Filtered CSV exports (Sensors, Predictions, Alerts)
- Executive PDF Summary Reports generated via ReportLab
- Clear metadata: storage unit, telemetry mode, timestamps, and statistics
"""

import io
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

def generate_csv_export(records: List[Dict[str, Any]], fieldnames: List[str]) -> str:
    """Generate RFC-4180 compliant CSV string from list of dicts."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    for row in records:
        writer.writerow(row)
    return output.getvalue()

def generate_pdf_report(
    unit_info: Dict[str, Any],
    stats: Dict[str, Any],
    recent_alerts: List[Dict[str, Any]],
    recent_readings: List[Dict[str, Any]],
    generated_by: str = "Administrator"
) -> bytes:
    """
    Generate professional multi-section GrainGuard Post-Harvest Risk Report as PDF bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1b4332"),
        fontName="Helvetica-Bold"
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4b5563")
    )
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#2d6a4f"),
        fontName="Helvetica-Bold",
        spaceBefore=10,
        spaceAfter=6
    )
    cell_style = ParagraphStyle(
        'Cell',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1f2937")
    )
    header_cell_style = ParagraphStyle(
        'HCell',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.white,
        fontName="Helvetica-Bold"
    )

    elements = []

    # Title & Header
    elements.append(Paragraph("GrainGuard AI — Post-Harvest Storage Risk Audit Report", title_style))
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    elements.append(Paragraph(
        f"<b>Generated:</b> {now_str} | <b>Operator:</b> {generated_by} | "
        f"<b>Source:</b> Local Prototype Mode (Simulated Telemetry Replay)",
        subtitle_style
    ))
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2d6a4f"), spaceAfter=12))

    # Unit Summary Table
    elements.append(Paragraph("1. Target Storage Unit Overview", heading_style))
    unit_data = [
        [
            Paragraph("<b>Unit Name:</b>", cell_style),
            Paragraph(str(unit_info.get("name", "All Units")), cell_style),
            Paragraph("<b>Crop Stored:</b>", cell_style),
            Paragraph(str(unit_info.get("crop_type", "Wheat / Grain")), cell_style)
        ],
        [
            Paragraph("<b>Capacity:</b>", cell_style),
            Paragraph(f"{unit_info.get('capacity_tons', 500)} Tons", cell_style),
            Paragraph("<b>Current Risk Status:</b>", cell_style),
            Paragraph(f"<b>{stats.get('current_risk', 'Low Risk')}</b>", cell_style)
        ]
    ]
    u_table = Table(unit_data, colWidths=[90, 180, 90, 180])
    u_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f3f4f6")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d1d5db")),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(u_table)
    elements.append(Spacer(1, 10))

    # Summary Statistics Cards Table
    elements.append(Paragraph("2. Telemetry & Risk Statistics (Filtered Period)", heading_style))
    stats_data = [
        [
            Paragraph("<b>Total Telemetry Points</b>", cell_style),
            Paragraph("<b>Average Temp (°C)</b>", cell_style),
            Paragraph("<b>Average Humidity (%)</b>", cell_style),
            Paragraph("<b>Critical Alerts Logged</b>", cell_style)
        ],
        [
            Paragraph(str(stats.get("total_readings", 0)), cell_style),
            Paragraph(f"{stats.get('avg_temp', 0):.1f}°C", cell_style),
            Paragraph(f"{stats.get('avg_humidity', 0):.1f}%", cell_style),
            Paragraph(str(stats.get("high_risk_alerts", 0)), cell_style)
        ]
    ]
    s_table = Table(stats_data, colWidths=[135, 135, 135, 135])
    s_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e5e7eb")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#9ca3af")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(s_table)
    elements.append(Spacer(1, 12))

    # Recent Alerts Section
    elements.append(Paragraph("3. Storage Alerts & Incidents", heading_style))
    if recent_alerts:
        alert_rows = [[
            Paragraph("Timestamp", header_cell_style),
            Paragraph("Level", header_cell_style),
            Paragraph("Message", header_cell_style),
            Paragraph("Status", header_cell_style)
        ]]
        for a in recent_alerts[:10]:
            alert_rows.append([
                Paragraph(str(a.get("timestamp", ""))[:19], cell_style),
                Paragraph(str(a.get("level", "")), cell_style),
                Paragraph(str(a.get("message", ""))[:60], cell_style),
                Paragraph(str(a.get("status", "Active")), cell_style)
            ])
        a_table = Table(alert_rows, colWidths=[110, 70, 280, 80])
        a_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2d6a4f")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d1d5db")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f9fafb")]),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(a_table)
    else:
        elements.append(Paragraph("<i>No alerts recorded for this selection.</i>", subtitle_style))
    elements.append(Spacer(1, 12))

    # Recent Sensor Readings Table
    elements.append(Paragraph("4. Recent Sensor Telemetry Samples", heading_style))
    if recent_readings:
        read_rows = [[
            Paragraph("Timestamp", header_cell_style),
            Paragraph("Temp (°C)", header_cell_style),
            Paragraph("Hum (%)", header_cell_style),
            Paragraph("Gas (ppm)", header_cell_style),
            Paragraph("Moist (%)", header_cell_style),
            Paragraph("Vent", header_cell_style)
        ]]
        for r in recent_readings[:12]:
            read_rows.append([
                Paragraph(str(r.get("timestamp", ""))[:19], cell_style),
                Paragraph(f"{r.get('temperature', 0):.1f}", cell_style),
                Paragraph(f"{r.get('humidity', 0):.1f}", cell_style),
                Paragraph(f"{r.get('gas_concentration', 0):.0f}", cell_style),
                Paragraph(f"{r.get('grain_moisture', 0):.1f}", cell_style),
                Paragraph("ON" if r.get("ventilation") else "OFF", cell_style)
            ])
        r_table = Table(read_rows, colWidths=[130, 80, 80, 80, 80, 90])
        r_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1b4332")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d1d5db")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f9fafb")]),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(r_table)
    else:
        elements.append(Paragraph("<i>No sensor telemetry recorded for this selection.</i>", subtitle_style))

    # Disclaimer Footer
    elements.append(Spacer(1, 16))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#9ca3af"), spaceAfter=8))
    elements.append(Paragraph(
        "<b>Notice:</b> This document was generated automatically by GrainGuard AI. "
        "In this prototype evaluation phase, data points are delivered via simulated telemetry replay. "
        "Physical ESP32 hardware and sensor probes will be connected in the subsequent hardware integration phase.",
        subtitle_style
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
