"""Real CSV/JSON/XLSX/PDF output from one frozen, typed report snapshot."""
import csv
from datetime import date, datetime
from html import escape
from io import BytesIO, StringIO
import json
from zipfile import ZipFile, ZIP_DEFLATED


def safe_cell(value):
    text = "" if value is None else str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def export_report(rows, columns, manifest, format):
    if format == "json":
        return json.dumps({"manifest": manifest, "columns": columns, "data": rows},
                          ensure_ascii=False, default=str).encode(), "application/json"
    if format == "csv":
        out = StringIO(newline="")
        writer = csv.writer(out)
        writer.writerow(["Report", manifest.get("report_code", "")])
        writer.writerow(["Generated at", manifest.get("generated_at", "")])
        writer.writerow(["Period", manifest.get("date_from", ""), manifest.get("date_to", "")])
        writer.writerow(["Snapshot SHA-256", manifest.get("sha256", "")])
        writer.writerow(columns)
        writer.writerows([[safe_cell(row.get(column)) for column in columns] for row in rows])
        return out.getvalue().encode("utf-8-sig"), "text/csv"
    if format == "xlsx":
        def sheet(values):
            return ('<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' +
                    "".join('<row r="%s">%s</row>' % (i, "".join(
                        '<c t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % escape(str(cell) if cell is not None else "")
                        for cell in row)) for i, row in enumerate(values, 1)) + '</sheetData></worksheet>')
        out = BytesIO()
        with ZipFile(out, "w", ZIP_DEFLATED) as z:
            z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
            z.writestr('_rels/.rels', '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
            z.writestr('xl/workbook.xml', '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Report" sheetId="1" r:id="rId1"/><sheet name="Manifest" sheetId="2" r:id="rId2"/></sheets></workbook>')
            z.writestr('xl/_rels/workbook.xml.rels', '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/></Relationships>')
            z.writestr('xl/worksheets/sheet1.xml', sheet([columns, *[[row.get(c, "") for c in columns] for row in rows]]))
            z.writestr('xl/worksheets/sheet2.xml', sheet([[key, json.dumps(value, default=str) if isinstance(value, (dict, list)) else value] for key, value in manifest.items()]))
        return out.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if format == "pdf":
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A3, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle
        out = BytesIO()
        styles = getSampleStyleSheet()
        cell = ParagraphStyle("report_cell", parent=styles["BodyText"], fontSize=7, leading=9, wordWrap="CJK")
        width, height = landscape(A3)
        doc = SimpleDocTemplate(out, pagesize=(width, height), leftMargin=24, rightMargin=24, topMargin=28, bottomMargin=28)
        story = [Paragraph(escape(manifest.get("report_code", "Report")), styles["Heading1"]),
                 Paragraph(escape("Generated: %s | Period: %s - %s | Rows: %s" % (manifest.get("generated_at", ""), manifest.get("date_from", ""), manifest.get("date_to", ""), len(rows))), styles["BodyText"]),
                 Paragraph(escape("SHA-256: " + manifest.get("sha256", "")), styles["BodyText"]), Spacer(1, 12)]
        table = [[Paragraph(escape(str(c)), cell) for c in columns]]
        table += [[Paragraph(escape(str(row.get(c, ""))), cell) for c in columns] for row in rows]
        grid = LongTable(table, colWidths=[(width - 48) / max(1, len(columns))] * len(columns), repeatRows=1, splitInRow=1)
        grid.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9eef5")), ("GRID", (0, 0), (-1, -1), .3, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]))
        story.append(grid)
        doc.build(story, onFirstPage=lambda canvas, document: canvas.drawString(24, 12, f"Page {document.page}"), onLaterPages=lambda canvas, document: canvas.drawString(24, 12, f"Page {document.page}"))
        return out.getvalue(), "application/pdf"
    raise ValueError("Unsupported report format")
