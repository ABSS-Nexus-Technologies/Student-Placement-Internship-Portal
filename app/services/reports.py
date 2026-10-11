import io
from datetime import datetime, date
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import pandas as pd
import numpy as np


def compute_kpis(student_records):
    """
    Computes key performance indicators from a list of student records.
    Each record: {'student_id', 'name', 'roll_no', 'branch', 'cgpa', 'is_placed', 'package', ...}
    """
    total_registered = len(student_records)
    if total_registered == 0:
        return {
            'total_registered': 0,
            'total_placed': 0,
            'placement_percentage': 0.0,
            'highest_package': 0.0,
            'average_package': 0.0,
            'median_package': 0.0,
        }

    placed_students = [s for s in student_records if s.get('is_placed', False)]
    total_placed = len(placed_students)
    placement_percentage = round((total_placed / total_registered) * 100.0, 2)

    packages = [float(s.get('package') or 0.0) for s in placed_students if s.get('package') and float(s.get('package')) > 0]

    if packages:
        highest_package = round(float(np.max(packages)), 2)
        average_package = round(float(np.mean(packages)), 2)
        median_package = round(float(np.median(packages)), 2)
    else:
        highest_package = 0.0
        average_package = 0.0
        median_package = 0.0

    return {
        'total_registered': total_registered,
        'total_placed': total_placed,
        'placement_percentage': placement_percentage,
        'highest_package': highest_package,
        'average_package': average_package,
        'median_package': median_package,
    }


def style_worksheet(ws, header_fill_color="1E3A8A"):
    """
    Applies professional styling:
    - Dark navy/indigo header with bold white text
    - Subtle borders
    - Auto column widths
    - Freeze header pane
    """
    ws.freeze_panes = "A2"
    
    header_fill = PatternFill(start_color=header_fill_color, end_color=header_fill_color, fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    
    thin_border_side = Side(border_style="thin", color="CBD5E1")
    cell_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    
    # Style Header (Row 1)
    for col_idx in range(1, ws.max_column + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border
    
    ws.row_dimensions[1].height = 28
    
    # Style Data Rows
    for row_idx in range(2, ws.max_row + 1):
        ws.row_dimensions[row_idx].height = 20
        for col_idx in range(1, ws.max_column + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = data_font
            cell.border = cell_border
            
            # Numeric alignment and formatting
            val = cell.value
            if isinstance(val, (int, float)):
                if "Package" in str(ws.cell(row=1, column=col_idx).value or "") or "LPA" in str(ws.cell(row=1, column=col_idx).value or ""):
                    cell.number_format = '#,##0.00'
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                elif "CGPA" in str(ws.cell(row=1, column=col_idx).value or "") or "%" in str(ws.cell(row=1, column=col_idx).value or ""):
                    cell.number_format = '0.00'
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    # Auto column width
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val = cell.value
            if val is not None:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)


def add_summary_sheet(wb, kpis, report_type, filters_applied):
    """
    Creates an Executive Summary sheet as the first tab in the workbook.
    """
    ws = wb.create_sheet(title="Executive Summary", index=0)
    ws.views.sheetView[0].showGridLines = True
    
    # Title Block
    title_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    title_font = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
    ws.merge_cells("B2:F2")
    ws["B2"] = "Training & Placement Office - Placement Analytics Report"
    ws["B2"].fill = title_fill
    ws["B2"].font = title_font
    ws["B2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 36
    
    # Metadata Subtitle
    ws.merge_cells("B3:F3")
    now_str = datetime.now().strftime("%d %b %Y, %I:%M %p")
    ws["B3"] = f"Report Type: {report_type.replace('_', ' ').title()} | Generated On: {now_str}"
    ws["B3"].font = Font(name="Calibri", size=10, italic=True, color="475569")
    ws["B3"].alignment = Alignment(horizontal="center", vertical="center")
    
    # KPI Grid Headers
    kpi_items = [
        ("Total Students Registered", kpis['total_registered'], "Students"),
        ("Total Students Placed", kpis['total_placed'], "Students"),
        ("Placement Percentage", f"{kpis['placement_percentage']}%", "Rate"),
        ("Highest Package", f"{kpis['highest_package']} LPA", "Maximum"),
        ("Average Package", f"{kpis['average_package']} LPA", "Mean"),
        ("Median Package", f"{kpis['median_package']} LPA", "50th Percentile"),
    ]
    
    card_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    border_side = Side(border_style="thin", color="CBD5E1")
    card_border = Border(left=border_side, right=border_side, top=border_side, bottom=border_side)
    
    start_row = 5
    for idx, (label, val, subtitle) in enumerate(kpi_items):
        r = start_row + (idx * 2)
        ws.cell(row=r, column=2, value=label).font = Font(name="Calibri", size=11, bold=True, color="1E293B")
        ws.cell(row=r, column=2).fill = card_fill
        ws.cell(row=r, column=2).border = card_border
        
        val_cell = ws.cell(row=r, column=3, value=val)
        val_cell.font = Font(name="Calibri", size=12, bold=True, color="0284C7")
        val_cell.alignment = Alignment(horizontal="right")
        val_cell.fill = card_fill
        val_cell.border = card_border

        sub_cell = ws.cell(row=r, column=4, value=subtitle)
        sub_cell.font = Font(name="Calibri", size=9, italic=True, color="64748B")
        sub_cell.fill = card_fill
        sub_cell.border = card_border

    # Filters Section
    filter_start = start_row + (len(kpi_items) * 2) + 2
    ws.cell(row=filter_start, column=2, value="Applied Filter Parameters").font = Font(name="Calibri", size=11, bold=True, color="0F172A")
    for f_idx, (k, v) in enumerate(filters_applied.items()):
        f_row = filter_start + 1 + f_idx
        ws.cell(row=f_row, column=2, value=str(k).replace('_', ' ').title()).font = Font(name="Calibri", size=10, bold=True, color="475569")
        ws.cell(row=f_row, column=3, value=str(v) if v else "All").font = Font(name="Calibri", size=10, color="1E293B")
        ws.cell(row=f_row, column=2).border = card_border
        ws.cell(row=f_row, column=3).border = card_border

    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 22
    ws.column_dimensions["D"].width = 20
    ws.column_dimensions["E"].width = 16
    ws.column_dimensions["F"].width = 16


def generate_placement_excel(report_type, raw_data, filters=None):
    """
    Main generator dispatch function.
    report_type: 'student_wise' | 'company_wise' | 'branch_wise' | 'year_wise'
    raw_data: dictionary containing:
        - 'students': list of student dicts
        - 'placements': list of placement dicts
        - 'companies': list of company dicts
        - 'drives': list of drive dicts
    """
    if filters is None:
        filters = {}

    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    students = raw_data.get('students', [])
    kpis = compute_kpis(students)

    if report_type == 'student_wise':
        ws = wb.create_sheet(title="Student Details")
        headers = [
            "Roll No", "Student Name", "Branch", "Batch Year", "CGPA", 
            "Backlogs", "Placement Status", "Company Placed", "Drive Title", 
            "Package (LPA)", "Offer Date"
        ]
        ws.append(headers)
        for s in students:
            row = [
                s.get('roll_no', ''),
                s.get('name', ''),
                s.get('branch', ''),
                s.get('passing_year', ''),
                s.get('cgpa', 0.0),
                s.get('active_backlogs', 0),
                "Placed" if s.get('is_placed') else "Unplaced",
                s.get('company_name', '-'),
                s.get('drive_title', '-'),
                s.get('package', 0.0) if s.get('is_placed') else 0.0,
                s.get('offer_date', '-')
            ]
            ws.append(row)
        style_worksheet(ws, header_fill_color="1E3A8A")

    elif report_type == 'company_wise':
        ws = wb.create_sheet(title="Company Summary")
        headers = [
            "Company Name", "Industry", "Total Drives", "Total Applicants",
            "Students Placed", "Highest Package (LPA)", "Avg Package (LPA)"
        ]
        ws.append(headers)
        comp_records = raw_data.get('company_summary', [])
        for c in comp_records:
            ws.append([
                c.get('name', ''),
                c.get('industry', ''),
                c.get('total_drives', 0),
                c.get('total_applicants', 0),
                c.get('placed_count', 0),
                c.get('highest_pkg', 0.0),
                c.get('avg_pkg', 0.0)
            ])
        style_worksheet(ws, header_fill_color="065F46")

    elif report_type == 'branch_wise':
        ws = wb.create_sheet(title="Branch Summary")
        headers = [
            "Branch", "Registered Students", "Placed Students", 
            "Placement %", "Highest Package (LPA)", "Avg Package (LPA)", "Median Package (LPA)"
        ]
        ws.append(headers)
        branch_records = raw_data.get('branch_summary', [])
        for b in branch_records:
            ws.append([
                b.get('branch', ''),
                b.get('registered', 0),
                b.get('placed', 0),
                b.get('placement_pct', 0.0),
                b.get('highest_pkg', 0.0),
                b.get('avg_pkg', 0.0),
                b.get('median_pkg', 0.0)
            ])
        style_worksheet(ws, header_fill_color="7C2D12")

    elif report_type == 'year_wise':
        ws = wb.create_sheet(title="Batch Year Summary")
        headers = [
            "Batch Year", "Registered Students", "Placed Students",
            "Placement %", "Highest Package (LPA)", "Avg Package (LPA)", "Median Package (LPA)"
        ]
        ws.append(headers)
        year_records = raw_data.get('year_summary', [])
        for y in year_records:
            ws.append([
                y.get('batch_year', ''),
                y.get('registered', 0),
                y.get('placed', 0),
                y.get('placement_pct', 0.0),
                y.get('highest_pkg', 0.0),
                y.get('avg_pkg', 0.0),
                y.get('median_pkg', 0.0)
            ])
        style_worksheet(ws, header_fill_color="581C87")

    # Add Executive Summary as the first sheet
    add_summary_sheet(wb, kpis, report_type, filters)

    # Save to in-memory bytes buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
