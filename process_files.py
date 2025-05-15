import os
import csv
import json
import pytesseract
from pdf2image import convert_from_path
import requests

import re
import json

# Tesseract & Poppler Pfade anpassen!
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\Program Files\poppler-24.08.0\Library\bin"  # Passe ggf. an

API_URL = "http://10.0.0.20:1233/v1/chat/completions"
MODEL_NAME = "lmstudio-community/qwen2.5-vl-7b-instruct"

def ask_pdf_ocr(pdf_path, page_number=0, dpi=300, lang="deu"):
    pages = convert_from_path(pdf_path, dpi=dpi, poppler_path=POPPLER_PATH)
    if page_number >= len(pages):
        raise ValueError(f"PDF hat nur {len(pages)} Seiten, aber Seite {page_number} wurde angefragt.")
    page_img = pages[page_number]
    text = pytesseract.image_to_string(page_img, lang=lang)
    return text

def extract_with_llm(ocr_text):
    prompt = (
        "Extrahiere aus folgendem OCR-Text die folgenden Felder und gib die Antwort ausschließlich als JSON-Objekt zurück. "
        "WICHTIG: Verwende für Dezimalzahlen das deutsche Komma (z.B. 19,00), nicht den Punkt. "
        "Gib bei allen Beträgen und Sätzen ausschließlich die Zahl zurück, OHNE Euro-Zeichen, Prozent-Zeichen oder andere Einheiten. "
        "Beispiel: '19,00' oder '7,00' für MwSt-Satz, '1234,56' für Beträge.\n"
        "Felder:\n"
        "- Rechnungsnummer\n"
        "- Datum\n"
        "- Bezeichnung\n"
        "- MwSt-Satz (in Prozent, nur Zahl, KEIN %, KEIN Punkt, sondern Komma!)\n"
        "- MwSt-Betrag (nur Zahl, KEIN €)\n"
        "- Gesamtbetrag (nur Zahl, KEIN €, inkl. MwSt)\n"
        "- Nettobetrag (nur Zahl, KEIN €, ohne MwSt)\n"
        "- Lieferant (Name)\n"
        "Falls ein Wert nicht gefunden werden kann, schreibe \"NICHT GEFUNDEN\".\n"
        "Antworte ausschließlich mit folgendem JSON-Format (ohne weitere Erklärungen, Kommentare oder Text):\n"
        "{\n"
        "  \"Rechnungsnummer\": \"123456\",\n"
        "  \"Datum\": \"01.01.2024\",\n"
        "  \"Bezeichnung\": \"Artikelname\",\n"
        "  \"MwSt-Satz\": \"19,00\",\n"
        "  \"MwSt-Betrag\": \"23,45\",\n"
        "  \"Gesamtbetrag\": \"123,45\",\n"
        "  \"Nettobetrag\": \"100,00\",\n"
        "  \"Lieferant\": \"Beispiel GmbH\"\n"
        "}\n\n"
        "Achtung: Schreibe niemals einen Punkt als Dezimaltrennzeichen, sondern IMMER ein Komma!\n"
        "OCR-Text:\n"
    ) + ocr_text
    # ... Rest wie gehabt ...



    messages = [{"role": "user", "content": prompt}]
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 1024,
        "stream": False
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(API_URL, json=payload, headers=headers, timeout=120)
    if response.status_code == 200:
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            return data
    else:
        raise RuntimeError(f"Fehler: {response.status_code} - {response.text}")





def extract_json_from_response(response_text):
    # Entferne führende und abschließende Leerzeichen
    response_text = response_text.strip()
    # Entferne führende Markdown-Backticks wie ```json oder ```
    response_text = re.sub(r"^```(?:json)?\s*", "", response_text)
    # Entferne abschließende Backticks ```
    response_text = re.sub(r"\s*```$", "", response_text)
    # Suche nach dem ersten JSON-Objekt im Text
    match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except Exception as e:
            print(f"JSON-Parsing-Fehler: {e}")
            return {}
    else:
        return {}



def process_all_pdfs(ordner, out_csv="extraktion_llm_ergebnisse.csv"):
    fieldnames = [
        "Datei", "Rechnungsnummer", "Datum", "Bezeichnung", "MwSt-Satz",
        "MwSt-Betrag", "Gesamtbetrag", "Nettobetrag", "Lieferant"
    ]
    ergebnisse = []
    for dateiname in os.listdir(ordner):
        if dateiname.lower().endswith(".pdf"):
            pfad = os.path.join(ordner, dateiname)
            print(f"Verarbeite: {dateiname}")
            try:
                ocr_text = ask_pdf_ocr(pfad)
                llm_result = extract_with_llm(ocr_text)
                print(f"LLM-Output: {llm_result}")
                result_json = extract_json_from_response(llm_result)
                if not result_json:
                    print(f"Warnung: Konnte keine JSON-Antwort parsen für {dateiname}.")
                row = {
                    "Datei": dateiname,
                    "Rechnungsnummer": result_json.get("Rechnungsnummer", ""),
                    "Datum": result_json.get("Datum", ""),
                    "Bezeichnung": result_json.get("Bezeichnung", ""),
                    "MwSt-Satz": result_json.get("MwSt-Satz", ""),
                    "MwSt-Betrag": result_json.get("MwSt-Betrag", ""),
                    "Gesamtbetrag": result_json.get("Gesamtbetrag", ""),
                    "Nettobetrag": result_json.get("Nettobetrag", ""),
                    "Lieferant": result_json.get("Lieferant", "")
                }
                ergebnisse.append(row)
            except Exception as e:
                print(f"Fehler bei {dateiname}: {e}")
                ergebnisse.append({
                    "Datei": dateiname,
                    "Rechnungsnummer": "",
                    "Datum": "",
                    "Bezeichnung": "",
                    "MwSt-Satz": "",
                    "MwSt-Betrag": "",
                    "Gesamtbetrag": "",
                    "Nettobetrag": "",
                    "Lieferant": ""
                })

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ergebnisse)
    print(f"Ergebnisse gespeichert in {out_csv}")

if __name__ == "__main__":
    ORDNER = r"C:\temp\test_belege\2"  # Passe den Ordnerpfad an
    process_all_pdfs(ORDNER)
