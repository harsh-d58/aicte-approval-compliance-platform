"""Generate high-resolution statutory certificates and deeds for AICTE PS-04 testing."""

import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path("sample_documents")
OUT_DIR.mkdir(exist_ok=True)

def generate_fire_safety_pdf():
    pdf_path = OUT_DIR / "aicte_fire_safety_certificate.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        alignment=1, # Center
        textColor=colors.HexColor('#0f2b5c')
    )
    sub_style = ParagraphStyle(
        'SubStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        alignment=1,
        textColor=colors.HexColor('#334155')
    )
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        alignment=1,
        textColor=colors.HexColor('#991b1b')
    )
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        alignment=4, # Justify
        textColor=colors.HexColor('#1e293b')
    )

    story.append(Paragraph("GOVERNMENT OF NATIONAL CAPITAL TERRITORY OF DELHI", header_style))
    story.append(Paragraph("HEADQUARTERS: DELHI FIRE SERVICE: NEW DELHI – 110001", header_style))
    story.append(Paragraph("DIRECTORATE OF FIRE PREVENTION & LIFE SAFETY", sub_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0f2b5c'), spaceBefore=2, spaceAfter=10))

    meta_data = [
        [
            Paragraph("<b>Certificate / Reference No:</b> DFS/HQ/2026/FSC/8842", styles['Normal']),
            Paragraph("<b>Dated / Issue Date:</b> 10-03-2026", styles['Normal'])
        ],
        [
            Paragraph("<b>Application ID:</b> AICTE-2026-DRAFT", styles['Normal']),
            Paragraph("<b>Statutory Validity:</b> 3 Years (Valid upto: 09-03-2029)", styles['Normal'])
        ]
    ]
    t = Table(meta_data, colWidths=[280, 240])
    t.setStyle(TableStyle([
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#1e293b')),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    story.append(Paragraph("FIRE SAFETY CERTIFICATE", title_style))
    story.append(Spacer(1, 10))

    text1 = (
        "Certified that the technical educational premises of <b>Cedar Institute of Technology</b> located at "
        "Plot No. 12, Institutional Area, Knowledge Park Phase-II, New Delhi comprised of Basement, Ground plus "
        "four upper institutional floors owned and occupied by Cedar Education Foundation have complied with the fire prevention "
        "and fire safety requirements in accordance with Rule 33 of Delhi Fire Service Rules, 2010 and verified by the officers "
        "concerned of Fire Service on 02/03/2026 in the presence of Principal and Management Representatives."
    )
    story.append(Paragraph(text1, body_style))
    story.append(Spacer(1, 10))

    text2 = (
        "The building premises is hereby certified fit for educational occupancy class <b>Group B (Educational: Sub-Division B-1)</b> "
        "with effect from <b>10-03-2026</b> for a period of <b>Three (3) Years</b> in accordance with Rule 36 unless renewed under "
        "Rule 37 or sooner cancelled under Rule 40 of Delhi Fire Service Rules, 2010, subject to continuous compliance with "
        "prescribed National Building Code (NBC Part-IV) fire safety standards and AICTE Approval Process Handbook guidelines."
    )
    story.append(Paragraph(text2, body_style))
    story.append(Spacer(1, 14))

    conditions = [
        "1. All means of escape, corridors, and emergency exit staircases shall remain unobstructed at all times.",
        "2. First aid hose reels, wet risers, automatic sprinkler systems, and yard hydrants shall be kept pressurized and in operational state.",
        "3. Qualified fire wardens and security staff must be trained periodically in accordance with mandatory fire drill protocols.",
        "4. Any structural deviation or unauthorised occupancy alteration shall automatically invalidate this certificate.",
        "5. The institution shall submit an annual renewal declaration in Form 'K' six months prior to the date of expiry."
    ]
    for c in conditions:
        story.append(Paragraph(f"• {c}", ParagraphStyle('Cond', parent=styles['Normal'], fontSize=8.5, leading=12, textColor=colors.HexColor('#334155'))))
        story.append(Spacer(1, 3))

    story.append(Spacer(1, 25))

    footer_data = [
        [
            Paragraph("<b>Issuing Authority:</b><br/>DELHI FIRE SERVICE<br/>Headquarters, Connaught Place, New Delhi", styles['Normal']),
            Paragraph("<b>Authorised Signatory:</b><br/>(A. K. Sharma)<br/>Deputy Chief Fire Officer (HQ)<br/>Government of NCT of Delhi", styles['Normal'])
        ]
    ]
    tf = Table(footer_data, colWidths=[280, 240])
    tf.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(tf)

    doc.build(story)
    print(f"Generated PDF: {pdf_path}")
    return pdf_path

def generate_fire_safety_image():
    img_path = OUT_DIR / "aicte_fire_safety_certificate.png"
    # Create high-res 1654 x 2338 (approx 200 DPI A4)
    w, h = 1654, 2338
    img = Image.new("RGB", (w, h), color=(254, 254, 252))
    draw = ImageDraw.Draw(img)

    # Decorative border
    draw.rectangle([40, 40, w - 40, h - 40], outline=(15, 43, 92), width=4)
    draw.rectangle([48, 48, w - 48, h - 48], outline=(180, 83, 9), width=2)

    # Draw header text using default or bitmap font scaling
    # Standard header lines
    lines = [
        ("GOVERNMENT OF NATIONAL CAPITAL TERRITORY OF DELHI", 42, (15, 43, 92), True),
        ("HEADQUARTERS: DELHI FIRE SERVICE: NEW DELHI - 110001", 34, (15, 43, 92), True),
        ("DIRECTORATE OF FIRE PREVENTION & LIFE SAFETY MEASURES", 26, (71, 85, 105), False),
    ]

    y = 100
    for text, size, color, bold in lines:
        draw.text((w // 2, y), text, fill=color, anchor="mm")
        y += 45

    # Separator line
    y += 20
    draw.line([(80, y), (w - 80, y)], fill=(15, 43, 92), width=3)
    y += 40

    # Meta block
    draw.text((100, y), "Certificate / Reference No: DFS/HQ/2026/FSC/8842", fill=(17, 24, 39))
    draw.text((w - 550, y), "Dated / Issue Date: 10-03-2026", fill=(17, 24, 39))
    y += 45
    draw.text((100, y), "Application Reference: AICTE-2026-DRAFT", fill=(17, 24, 39))
    draw.text((w - 550, y), "Statutory Validity: 3 Years (Expiry: 09-03-2029)", fill=(17, 24, 39))
    y += 70

    # Title box
    draw.rectangle([w // 2 - 350, y, w // 2 + 350, y + 60], fill=(254, 242, 242), outline=(185, 28, 28), width=2)
    draw.text((w // 2, y + 30), "FIRE SAFETY CERTIFICATE", fill=(185, 28, 28), anchor="mm")
    y += 110

    # Body paragraphs
    body_lines = [
        "Certified that the technical educational premises of Cedar Institute of Technology",
        "situated at Plot No. 12, Institutional Area, Knowledge Park Phase-II, New Delhi - 110092,",
        "comprising Basement, Ground plus four upper institutional floors owned and occupied by",
        "Cedar Education Foundation, have complied with the statutory fire prevention and fire",
        "safety requirements under Rule 33 of Delhi Fire Service Rules, 2010.",
        "",
        "The building premises were inspected on 02/03/2026 in the presence of the Principal and",
        "authorized administrative representatives, and found to strictly conform to National",
        "Building Code (NBC 2016 Part-IV) life safety standards and AICTE APH regulations.",
        "",
        "The building is hereby declared fit for occupancy class Group B (Educational: Sub-Division B-1)",
        "with effect from 10-03-2026 for a statutory period of 3 Years in accordance with Rule 36,",
        "valid until 09-03-2029, unless renewed under Rule 37 or sooner cancelled under Rule 40.",
        "",
        "Conditions for Continuous Statutory Validity:",
        "1. All emergency exit corridors, staircases, and muster areas shall remain unobstructed.",
        "2. Fire pump house, wet risers, and automatic sprinkler systems shall remain pressurized.",
        "3. Annual renewal declaration in Form K must be submitted six months prior to expiry date.",
        "4. Any structural or occupancy alteration without prior sanction renders this certificate void."
    ]

    for bl in body_lines:
        if bl.startswith("Conditions") or bl.startswith("1.") or bl.startswith("2.") or bl.startswith("3.") or bl.startswith("4."):
            draw.text((120, y), bl, fill=(71, 85, 105))
            y += 42
        elif bl == "":
            y += 20
        else:
            draw.text((120, y), bl, fill=(30, 41, 59))
            y += 44

    y += 80
    # Authority and Signature Box
    draw.rectangle([100, y, 650, y + 180], outline=(203, 213, 225), width=2)
    draw.text((120, y + 25), "Issuing Authority:", fill=(15, 23, 42))
    draw.text((120, y + 65), "DELHI FIRE SERVICE", fill=(15, 43, 92))
    draw.text((120, y + 105), "Headquarters: Connaught Place, New Delhi", fill=(71, 85, 105))
    draw.text((120, y + 140), "Government of National Capital Territory of Delhi", fill=(71, 85, 105))

    draw.rectangle([w - 650, y, w - 100, y + 180], outline=(203, 213, 225), width=2)
    draw.text((w - 630, y + 25), "Authorised Signatory:", fill=(15, 23, 42))
    draw.text((w - 630, y + 65), "A. K. Sharma, Dy. Chief Fire Officer (HQ)", fill=(15, 43, 92))
    draw.text((w - 630, y + 105), "Digitally Verified & Registered", fill=(16, 185, 129))
    draw.text((w - 630, y + 140), "SHA256: 7e9b42...8842-AUTHENTICATED", fill=(100, 116, 139))

    img.save(img_path, format="PNG")
    print(f"Generated Image: {img_path}")
    return img_path

def generate_land_lease_pdf():
    pdf_path = OUT_DIR / "aicte_land_lease_deed.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    story.append(Paragraph("GOVERNMENT OF NCT OF DELHI — REGISTRATION & STAMPS DEPARTMENT", ParagraphStyle('H1', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, alignment=1, textColor=colors.HexColor('#0f2b5c'))))
    story.append(Paragraph("OFFICE OF THE SUB-REGISTRAR: DISTRICT SOUTH-EAST, NEW DELHI", ParagraphStyle('H2', parent=styles['Normal'], fontName='Helvetica', fontSize=9, alignment=1, textColor=colors.HexColor('#475569'))))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0f2b5c'), spaceBefore=2, spaceAfter=10))

    meta = [
        [Paragraph("<b>Deed Registration No:</b> REG/LEASE/2023/5540", styles['Normal']), Paragraph("<b>Registered On:</b> 15-01-2023", styles['Normal'])],
        [Paragraph("<b>Institution Name:</b> Cedar Institute of Technology", styles['Normal']), Paragraph("<b>Lease Tenure:</b> 30 Years (Valid upto 14-01-2053)", styles['Normal'])],
    ]
    t = Table(meta, colWidths=[280, 240])
    story.append(t)
    story.append(Spacer(1, 15))

    story.append(Paragraph("REGISTERED PERPETUAL / LONG-TERM LAND LEASE DEED", ParagraphStyle('T', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=13, alignment=1, textColor=colors.HexColor('#1e3a8a'))))
    story.append(Spacer(1, 12))

    body = (
        "This Indenture of Lease executed on this Fifteenth day of January, 2023 by and between the Delhi Development Authority (Lessor) "
        "and Cedar Education Foundation represented by its Chairman for establishing and running <b>Cedar Institute of Technology</b> (Lessee). "
        "The Lessor hereby demises unto the Lessee all that piece of institutional land measuring <b>5.20 Acres (21,043.6 Sq. Meters)</b> "
        "situated at Plot No. 12, Institutional Area, Knowledge Park Phase-II, New Delhi for establishing higher technical education "
        "programmes in engineering and technology, strictly conforming to AICTE land norms and municipal building regulations.<br/><br/>"
        "<b>Statutory Lease Tenure:</b> The lease is granted for a firm, non-revocable term of <b>30 (Thirty) Years</b> commencing from "
        "15-01-2023 and subsisting through 14-01-2053, with right of renewal subject to payment of ground rent and statutory observance."
    )
    story.append(Paragraph(body, ParagraphStyle('B', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=14, alignment=4)))
    story.append(Spacer(1, 30))

    footer = [
        [Paragraph("<b>Issuing Sub-Registrar Authority:</b><br/>Sub-Registrar IX, New Delhi<br/>Department of Revenue, Govt. of NCT of Delhi", styles['Normal']),
         Paragraph("<b>Authorised Sub-Registrar:</b><br/>(V. K. Bansal)<br/>Sub-Registrar District South-East<br/>Seal & Registered Document Hash", styles['Normal'])]
    ]
    story.append(Table(footer, colWidths=[280, 240]))
    doc.build(story)
    print(f"Generated PDF: {pdf_path}")
    return pdf_path

if __name__ == "__main__":
    generate_fire_safety_pdf()
    generate_fire_safety_image()
    generate_land_lease_pdf()
    print("ALL SAMPLE STATUTORY DOCUMENTS GENERATED SUCCESSFULLY!")

