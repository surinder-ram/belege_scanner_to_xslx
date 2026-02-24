
from paddleocr import PaddleOCR
import os
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

import os
import json
import io
import re
import requests
import numpy as np



from pdf2image import convert_from_path
from paddleocr import PaddleOCR
from openpyxl import Workbook
from openpyxl.styles import Font, NamedStyle, Alignment
from datetime import datetime

# ---------------- LM STUDIO SETTINGS ----------------

API_URL = "http://10.0.0.20:1233/v1/chat/completions"
MODEL_NAME = "google/gemma-3-27b"

# ---------------- SYSTEM PATHS ----------------

POPPLER_PATH = r"C:\Program Files\poppler-25.12.0\Library\bin"

# ---------------- PADDLE OCR INIT ----------------


OCR_ENGINE = PaddleOCR(
    use_textline_orientation=True,
    device="cpu"
)
# ---------------- EXCEL STYLES ----------------

def create_excel_styles(workbook):
    header_font = Font(bold=True)

    amount_style = NamedStyle(name="amount_style", number_format="#,##0.00")
    date_style = NamedStyle(name="date_style", number_format="DD.MM.YYYY")

    if "amount_style" not in workbook.style_names:
        workbook.add_named_style(amount_style)
    if "date_style" not in workbook.style_names:
        workbook.add_named_style(date_style)

    return header_font, "amount_style", "date_style"


# ---------------- PARSER HELPERS ----------------

def parse_german_float(s_val):
    if isinstance(s_val, (int, float)):
        return float(s_val)

    if isinstance(s_val, str):
        s_val = s_val.replace(".", "").replace(",", ".")
        try:
            return float(s_val)
        except:
            return None
    return None


def parse_german_date(s_date):
    if isinstance(s_date, str):
        try:
            return datetime.strptime(s_date, "%d.%m.%Y")
        except:
            return None
    return None


# ---------------- OCR STEP ----------------

def extract_text_with_paddle(pdf_path, dpi=300):
    print(f"    OCR lese: {os.path.basename(pdf_path)}")

    pages = convert_from_path(
        pdf_path,
        dpi=dpi,
        poppler_path=POPPLER_PATH,
        first_page=1,
        last_page=1
    )

    if not pages:
        raise ValueError("Keine Seite erkannt")

    img_np = np.array(pages[0])

    result = OCR_ENGINE.ocr(img_np, cls=True)

    lines = []
    for block in result:
        for line in block:
            lines.append(line[1][0])

    text = "\n".join(lines)

    print(f"    → {len(lines)} Textzeilen erkannt")
    return text


# ---------------- LLM STRUCTURING ----------------

def send_text_to_llm(ocr_text):
    system_prompt = (
        "Du bist ein präziser Buchhaltungs-Parser. "
        "Du darfst KEINE Informationen erfinden. "
        "Wenn ein Feld fehlt → NICHT GEFUNDEN."
    )

    user_prompt = f"""
Extrahiere strukturierte Rechnungsdaten aus diesem OCR-Text.

TEXT:
{ocr_text}

Gib ausschließlich JSON zurück:

{{
"Rechnungsnummer":"",
"Datum":"",
"Bezeichnung":"",
"MwSt-Satz":"",
"MwSt-Betrag":"",
"Gesamtbetrag":"",
"Nettobetrag":"",
"Lieferant":""
}}

Regeln:
- Zahlen mit Komma
- Datum TT.MM.JJJJ
- Keine Halluzination
"""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 1200
    }

    response = requests.post(API_URL, json=payload, timeout=300)
    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]


# ---------------- JSON CLEANUP ----------------

def extract_json(text):
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except:
        return {}


# ---------------- MAIN PROCESS ----------------

def process_pdf(pdf_path):
    ocr_text = extract_text_with_paddle(pdf_path)
    llm_answer = send_text_to_llm(ocr_text)
    data = extract_json(llm_answer)

    return data, llm_answer


# ---------------- EXCEL EXPORT ----------------

def process_folder_to_excel(folder, output_excel):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Rechnungsdaten"

    header_font, amount_style, date_style = create_excel_styles(workbook)

    headers = [
        "Datei","Rechnungsnummer","Datum","Bezeichnung",
        "MwSt-Satz","MwSt-Betrag","Gesamtbetrag",
        "Nettobetrag","Lieferant","Rohe_LLM_Antwort"
    ]

    for col, h in enumerate(headers,1):
        cell = sheet.cell(row=1,column=col,value=h)
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    row = 2

    for file in sorted(os.listdir(folder)):
        if not file.lower().endswith(".pdf"):
            continue

        path = os.path.join(folder,file)

        try:
            data, raw = process_pdf(path)

            values = [
                file,
                data.get("Rechnungsnummer"),
                parse_german_date(data.get("Datum")),
                data.get("Bezeichnung"),
                data.get("MwSt-Satz"),
                parse_german_float(data.get("MwSt-Betrag")),
                parse_german_float(data.get("Gesamtbetrag")),
                parse_german_float(data.get("Nettobetrag")),
                data.get("Lieferant"),
                raw
            ]

        except Exception as e:
            values = [file] + ["FEHLER"]*8 + [str(e)]

        for col,val in enumerate(values,1):
            cell = sheet.cell(row=row,column=col,value=val)

            if headers[col-1]=="Datum" and isinstance(val,datetime):
                cell.style=date_style
            elif headers[col-1] in ["MwSt-Betrag","Gesamtbetrag","Nettobetrag"] and isinstance(val,float):
                cell.style=amount_style

        row+=1

    workbook.save(output_excel)
    print(f"\n✔ Excel gespeichert: {output_excel}")


# ---------------- RUN ----------------

if __name__ == "__main__":
    input_folder = r"C:\Users\surin\Meine Ablage (surinder.ram@gmail.com)\Firma\Belege\2025\Hardware"
    output_excel = r"C:\Users\surin\Meine Ablage (surinder.ram@gmail.com)\Firma\Belege\2025\Hardware\Ergebnis.xlsx"

    process_folder_to_excel(input_folder, output_excel)