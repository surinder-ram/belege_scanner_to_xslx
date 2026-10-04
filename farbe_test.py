from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def create_large_mandarin_palette():
    pdf_filename = "mandarin_6x6_farbpalette.pdf"

    # A4 Dokument mit schmalen 20pt Rändern anlegen (~0.7 cm) für maximalen Platz
    doc = SimpleDocTemplate(pdf_filename, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    story = []

    # Textstile definieren
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=20,
        alignment=1,
        spaceAfter=5
    )
    text_style = ParagraphStyle(
        'TextStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        alignment=1,
        spaceAfter=10
    )
    label_style = ParagraphStyle(
        'LabelStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        alignment=1
    )

    # Titel hinzufügen
    story.append(Paragraph("<b>Große Farbmatrix: 36 Pastell- & Mandarin-Nuancen</b>", title_style))
    story.append(
        Paragraph("An die Fassade halten, Wunschfeld ankreuzen und das gewählte Quadrat im Bauhaus scannen lassen.",
                  text_style))
    story.append(Spacer(1, 10))

    # 6x6 Matrix (Name/Code, R, G, B)
    # Jede Reihe geht von hell/pastellig (links) zu intensiver (rechts)
    color_data = [
        # Reihe A: Sehr sanftes, milchiges Apricot
        [("A1", 255, 240, 225), ("A2", 255, 230, 210), ("A3", 255, 220, 195), ("A4", 255, 210, 180),
         ("A5", 255, 200, 165), ("A6", 255, 190, 150)],
        # Reihe B: Klassischer Pfirsich-Farbton
        [("B1", 255, 235, 215), ("B2", 255, 218, 193), ("B3", 255, 203, 172), ("B4", 255, 187, 150),
         ("B5", 255, 171, 127), ("B6", 255, 154, 102)],
        # Reihe C: Spritziges Pastell-Mandarin
        [("C1", 255, 225, 190), ("C2", 255, 210, 165), ("C3", 255, 194, 138), ("C4", 255, 178, 110),
         ("C5", 255, 161, 80), ("C6", 255, 143, 43)],
        # Reihe D: Sonnige Clementine / Melone
        [("D1", 255, 235, 190), ("D2", 255, 222, 160), ("D3", 255, 208, 130), ("D4", 255, 193, 98),
         ("D5", 255, 177, 63), ("D6", 255, 160, 20)],
        # Reihe E: Sanftes Lachs- & Korallen-Orange
        [("E1", 255, 225, 210), ("E2", 255, 205, 188), ("E3", 255, 185, 165), ("E4", 255, 164, 140),
         ("E5", 255, 142, 115), ("E6", 255, 119, 89)],
        # Reihe F: Erdig-warmes Honig-Apricot
        [("F1", 245, 222, 185), ("F2", 235, 205, 160), ("F3", 225, 188, 135), ("F4", 215, 170, 110),
         ("F5", 205, 151, 85), ("F6", 195, 131, 60)]
    ]

    table_content = []
    table_styles = [
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 2, colors.white),  # Weiße Gitterlinien zur klaren Trennung
    ]

    # Spaltenbreiten (6 Spalten à 92 points = ~3,2 cm)
    col_widths = [92] * 6
    # Zeilenhöhen (6 Reihen à 105 points = ~3,7 cm)
    row_heights = [105] * 6

    for row_idx, row in enumerate(color_data):
        row_cells = []
        for col_idx, cell in enumerate(row):
            label, r, g, b = cell

            rl_color = colors.Color(r / 255.0, g / 255.0, b / 255.0)

            # Kontrastprüfung für die Schriftfarbe (Schwarz oder Weiß)
            brightness = (r * 0.299 + g * 0.587 + b * 0.114)
            text_color = "#000000" if brightness > 140 else "#FFFFFF"

            box_label_style = ParagraphStyle(
                f'Label_{row_idx}_{col_idx}',
                parent=label_style,
                textColor=colors.HexColor(text_color)
            )

            # Beschriftung mit Code und RGB-Wert zur Sicherheit
            cell_text = f"<b>{label}</b><br/><font size=6>R{r} G{g} B{b}</font>"
            row_cells.append(Paragraph(cell_text, box_label_style))

            # Farbe der jeweiligen Zelle zuweisen
            table_styles.append(('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), rl_color))

        table_content.append(row_cells)

    # Tabelle bauen und hinzufügen
    color_table = Table(table_content, colWidths=col_widths, rowHeights=row_heights)
    color_table.setStyle(TableStyle(table_styles))
    story.append(color_table)

    # PDF generieren
    doc.build(story)
    print(f"Datei erfolgreich erstellt: '{pdf_filename}'")


if __name__ == '__main__':
    create_large_mandarin_palette()
