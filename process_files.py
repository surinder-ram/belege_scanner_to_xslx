import os
import csv
import pytesseract
from pdf2image import convert_from_path
import requests

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
        "Extrahiere aus folgendem OCR-Text die folgenden Felder und gib die Antwort ausschließlich als JSON-Objekt zurück:\n"
        "- Rechnungsnummer\n"
        "- Datum\n"
        "- MwSt-Satz (in Prozent, z.B. 19 oder 7)\n"
        "- MwSt-Betrag (in Euro)\n"
        "- Gesamtbetrag (in Euro, inkl. MwSt)\n"
        "- Nettobetrag (in Euro, ohne MwSt)\n"
        "Falls ein Wert nicht gefunden werden kann, schreibe \"NICHT GEFUNDEN\".\n"
        "Beispiel für das gewünschte JSON-Format:\n"
        "{\n"
        "  \"Rechnungsnummer\": \"...\",\n"
        "  \"Datum\": \"...\",\n"
        "  \"MwSt-Satz\": \"...\",\n"
        "  \"MwSt-Betrag\": \"...\",\n"
        "  \"Gesamtbetrag\": \"...\",\n"
        "  \"Nettobetrag\": \"...\"\n"
        "}\n\n"
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

def process_all_pdfs(ordner, out_csv="extraktion_llm_ergebnisse.csv"):
    ergebnisse = []
    for dateiname in os.listdir(ordner):
        if dateiname.lower().endswith(".pdf"):
            pfad = os.path.join(ordner, dateiname)
            print(f"Verarbeite: {dateiname}")
            try:
                ocr_text = ask_pdf_ocr(pfad)
                llm_result = extract_with_llm(ocr_text)
                print(f"LLM-Output: {llm_result}")
                ergebnisse.append({"Datei": dateiname, "LLM-Extraktion": llm_result})
            except Exception as e:
                print(f"Fehler bei {dateiname}: {e}")
                ergebnisse.append({"Datei": dateiname, "LLM-Extraktion": f"Fehler: {e}"})

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Datei", "LLM-Extraktion"])
        writer.writeheader()
        writer.writerows(ergebnisse)
    print(f"Ergebnisse gespeichert in {out_csv}")

if __name__ == "__main__":
    ORDNER = r"C:\temp\test_belege\1"  # Passe den Ordnerpfad an
    process_all_pdfs(ORDNER)
