import csv
from pathlib import Path
from io import BytesIO

from django.conf import settings
from django.http import HttpResponse

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


PDF_FONT_NAME = "Helvetica"
PDF_FONT_BOLD_NAME = "Helvetica-Bold"
PDF_FONTS_READY = False


def _to_text(value):
    if value is None:
        return ""
    return str(value)


def _register_pdf_fonts():
    global PDF_FONT_NAME, PDF_FONT_BOLD_NAME, PDF_FONTS_READY
    if PDF_FONTS_READY:
        return

    candidates = [
        (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf"), "MPTArial"),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            "MPTDejaVu",
        ),
        (
            settings.BASE_DIR / "static" / "fonts" / "DejaVuSans.ttf",
            settings.BASE_DIR / "static" / "fonts" / "DejaVuSans-Bold.ttf",
            "MPTDejaVuLocal",
        ),
    ]
    for regular_path, bold_path, family_name in candidates:
        if regular_path.exists() and bold_path.exists():
            pdfmetrics.registerFont(TTFont(family_name, str(regular_path)))
            pdfmetrics.registerFont(TTFont(f"{family_name}-Bold", str(bold_path)))
            PDF_FONT_NAME = family_name
            PDF_FONT_BOLD_NAME = f"{family_name}-Bold"
            break

    PDF_FONTS_READY = True


def export_csv_response(filename, headers, rows):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_to_text(cell) for cell in row])
    return response


def export_xlsx_response(filename, sheet_name, headers, rows):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name[:31] or "Report"

    worksheet.append(headers)
    for row in rows:
        worksheet.append([_to_text(cell) for cell in row])

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
    return response


def export_pdf_response(filename, title, headers, rows):
    _register_pdf_fonts()
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        leftMargin=24,
        rightMargin=24,
        topMargin=24,
        bottomMargin=24,
    )

    styles = getSampleStyleSheet()
    styles["Title"].fontName = PDF_FONT_BOLD_NAME
    styles["Normal"].fontName = PDF_FONT_NAME
    styles["Normal"].fontSize = 8
    styles["Normal"].leading = 10
    header_style = styles["Normal"].clone("PdfTableHeader")
    header_style.fontName = PDF_FONT_BOLD_NAME
    header_style.textColor = colors.whitesmoke
    elements = [Paragraph(title, styles["Title"]), Spacer(1, 12)]

    empty_row = ["No data"] + [""] * (len(headers) - 1)
    table_data = [[Paragraph(_to_text(cell), header_style) for cell in headers]]
    table_data.extend(
        [[Paragraph(_to_text(cell), styles["Normal"]) for cell in row] for row in (rows or [empty_row])]
    )

    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), PDF_FONT_BOLD_NAME),
                ("FONTNAME", (0, 1), (-1, -1), PDF_FONT_NAME),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elements.append(table)

    document.build(elements)
    output.seek(0)

    response = HttpResponse(output.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
    return response
