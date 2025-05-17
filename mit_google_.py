import os
import csv
import json
import pytesseract
from pdf2image import convert_from_path
import requests
import re
import cv2  # OpenCV für Bildvorverarbeitung
import numpy as np  # Für OpenCV

# Tesseract & Poppler Pfade anpassen!
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\Program Files\poppler-24.08.0\Library\bin"  # Passe ggf. an

API_URL = "http://10.0.0.20:1233/v1/chat/completions"
MODEL_NAME = "lmstudio-community/qwen2.5-vl-7b-instruct"
#MODEL_NAME = "lmstudio-community/qwen3-14b"


def preprocess_image_for_ocr(pil_image):
    """
    Verbessert die Bildqualität für OCR mit OpenCV.
    """
    open_cv_image = np.array(pil_image)
    # Konvertiere RGB/BGR zu Gray
    if len(open_cv_image.shape) == 3:
        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
    else:
        gray = open_cv_image  # Ist bereits Graustufen

    # 1. Entzerren (Deskewing) - Einfacher Ansatz
    # Nur anwenden, wenn das Bild nicht bereits hauptsächlich weiß ist (um Fehler bei leeren Seiten zu vermeiden)
    if np.mean(gray) < 250:  # Schwellenwert für "nicht leer"
        coords = np.column_stack(np.where(gray < np.mean(gray) * 0.8))  # Punkte dunkler als Durchschnitt
        if coords.shape[0] > 100:  # Nur wenn genügend dunkle Punkte vorhanden sind
            try:
                angle = cv2.minAreaRect(coords)[-1]
                if angle < -45:
                    angle = -(90 + angle)
                else:
                    angle = -angle

                # Nur bei signifikanter Schieflage korrigieren (z.B. > 1 Grad und < 45 Grad)
                if abs(angle) > 1 and abs(angle) < 45:
                    (h, w) = gray.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    # Fülle die Ränder mit Weiß (255), um schwarze Artefakte zu vermeiden
                    gray = cv2.warpAffine(gray, M, (w, h),
                                          flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT,
                                          borderValue=(255, 255, 255))
            except Exception as e:
                print(f"Deskewing fehlgeschlagen: {e}")
                # Fahre mit dem Original-Graustufenbild fort

    # 2. Rauschunterdrückung (optional, kann bei manchen Bildern helfen, bei anderen schaden)
    # gray = cv2.medianBlur(gray, 3) # Gut gegen Salz-und-Pfeffer-Rauschen
    # gray = cv2.GaussianBlur(gray, (3,3), 0) # Weichzeichnen

    # 3. Binarisierung
    # Adaptive Thresholding ist oft gut für variierende Lichtverhältnisse
    # binary_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    #                                   cv2.THRESH_BINARY, 11, 4) # Parameter testen!
    # Oder Otsu's Binarisierung (oft ein guter Standard)
    _, binary_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Manchmal hilft es, das Bild leicht zu "verdicken" (Dilatation) oder "zu verdünnen" (Erosion)
    # kernel = np.ones((1,1), np.uint8)
    # binary_img = cv2.dilate(binary_img, kernel, iterations=1)
    # binary_img = cv2.erode(binary_img, kernel, iterations=1)

    return binary_img


def ask_pdf_ocr(pdf_path, page_number=0, dpi=300, lang="deu"):
    """
    Konvertiert eine PDF-Seite in Text mit Vorverarbeitung.
    """
    try:
        pages = convert_from_path(pdf_path, dpi=dpi, poppler_path=POPPLER_PATH, first_page=page_number + 1,
                                  last_page=page_number + 1)
    except Exception as e:
        print(f"Fehler bei convert_from_path für {pdf_path}: {e}")
        return ""  # Leeren String zurückgeben, um den Prozess nicht abzubrechen

    if not pages:
        raise ValueError(f"PDF {pdf_path} hat keine Seite {page_number} oder konnte nicht gelesen werden.")

    page_pil_img = pages[0]

    # Bildvorverarbeitung
    processed_cv_img = preprocess_image_for_ocr(page_pil_img)

    # Tesseract-Konfiguration
    # PSM-Modi:
    # 3: Auto page segmentation with OSD (default)
    # 4: Assume a single column of text of variable sizes.
    # 6: Assume a single uniform block of text. (oft gut für Belege)
    # 11: Sparse text. Find as much text as possible in no particular order.
    # 12: Sparse text with OSD.
    # OEM 3: LSTM engine only (default und meist am besten)
    custom_config = r'--oem 3 --psm 6'  # Teste hier verschiedene PSM-Werte!

    try:
        text = pytesseract.image_to_string(processed_cv_img, lang=lang, config=custom_config)
    except Exception as e:
        print(f"Tesseract OCR Fehler für {pdf_path}: {e}")
        text = pytesseract.image_to_string(page_pil_img, lang=lang, config=custom_config)  # Fallback auf Originalbild
    return text


def extract_with_llm(ocr_text):
    system_message_content = (
        "Du bist ein spezialisierter Assistent zur Extraktion von Rechnungsdaten aus OCR-Text. "
        "Antworte ausschließlich im JSON-Format, wie im User-Prompt spezifiziert. "
        "Verwende für Dezimalzahlen das deutsche Komma (z.B. 19,00). "
        "Gib bei Beträgen und Sätzen nur die Zahl zurück, ohne Währungssymbole oder Prozentzeichen. "
        "Wenn ein Wert nicht gefunden wird, verwende den String \"NICHT GEFUNDEN\" für das entsprechende Feld."
        "Stelle sicher, dass die JSON-Struktur exakt dem Beispiel entspricht und keine zusätzlichen Erklärungen enthält."
    )

    user_message_content = (
                               "Extrahiere aus folgendem OCR-Text die folgenden Felder. "
                               "Felder:\n"
                               "- Rechnungsnummer\n"
                               "- Datum (Verwende für das Datum das Format TT.MM.JJJJ, z.B. 05.12.2024)\n"
                               "- Bezeichnung (Falls es eine Restaurant-Rechnung ist, nimm den Restaurant-Namen. Für Supermärkte 'Einkauf' oder den Supermarkt-Namen, falls klar ersichtlich.)\n"
                               "- MwSt-Satz (in Prozent, nur Zahl, KEIN %, KEIN Punkt, sondern Komma! z.B. '19,00'. Wenn mehrere Sätze vorhanden sind, nimm den häufigsten oder wichtigsten.)\n"
                               "- MwSt-Betrag (nur Zahl, KEIN €. Wenn mehrere MwSt-Beträge vorhanden sind, summiere sie oder nimm den zur Haupt-MwSt gehörenden Betrag.)\n"
                               "- Gesamtbetrag (nur Zahl, KEIN €, inkl. MwSt)\n"
                               "- Nettobetrag (nur Zahl, KEIN €, ohne MwSt. Berechne diesen ggf. aus Gesamtbetrag und MwSt-Betrag, falls nicht explizit genannt.)\n"
                               "- Lieferant (Name des Unternehmens, das die Rechnung ausgestellt hat)\n\n"
                               "Antworte ausschließlich mit folgendem JSON-Format (ohne weitere Erklärungen, Kommentare oder Text):\n"
                               "{\n"
                               "  \"Rechnungsnummer\": \"WERT_ODER_NICHT_GEFUNDEN\",\n"
                               "  \"Datum\": \"WERT_ODER_NICHT_GEFUNDEN\",\n"
                               "  \"Bezeichnung\": \"WERT_ODER_NICHT_GEFUNDEN\",\n"
                               "  \"MwSt-Satz\": \"WERT_ODER_NICHT_GEFUNDEN\",\n"
                               "  \"MwSt-Betrag\": \"WERT_ODER_NICHT_GEFUNDEN\",\n"
                               "  \"Gesamtbetrag\": \"WERT_ODER_NICHT_GEFUNDEN\",\n"
                               "  \"Nettobetrag\": \"WERT_ODER_NICHT_GEFUNDEN\",\n"
                               "  \"Lieferant\": \"WERT_ODER_NICHT_GEFUNDEN\"\n"
                               "}\n\n"
                               "Achtung: Schreibe niemals einen Punkt als Dezimaltrennzeichen, sondern IMMER ein Komma!\n"
                               "Achte darauf, dass alle angeforderten Felder im JSON enthalten sind, auch wenn der Wert \"NICHT GEFUNDEN\" ist.\n\n"
                               "OCR-Text:\n"
                           ) + ocr_text

    messages = [
        {"role": "system", "content": system_message_content},
        {"role": "user", "content": user_message_content}
    ]
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.1,  # Noch niedriger für mehr Konsistenz
        "max_tokens": 1500,  # Etwas mehr Puffer
        "stream": False
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=180)  # Längerer Timeout
        response.raise_for_status()  # Wirft einen Fehler für 4xx/5xx Antworten
        data = response.json()

        # Debug: Rohe Antwort des LLM ausgeben
        # print(f"LLM Raw Response: {data}")

        if "choices" in data and data["choices"] and "message" in data["choices"][0] and "content" in \
                data["choices"][0]["message"]:
            return data["choices"][0]["message"]["content"]
        else:
            print(f"Unerwartete LLM-Antwortstruktur: {data}")
            return "{}"  # Leeres JSON als Fallback
    except requests.exceptions.RequestException as e:
        print(f"API-Anfragefehler: {e}")
        raise RuntimeError(f"API-Anfragefehler: {e}")
    except Exception as e:
        print(f"Allgemeiner Fehler in extract_with_llm: {e}")
        return "{}"


def extract_json_from_response(response_text):
    response_text = response_text.strip()
    # Versuche zuerst, direkt zu parsen, falls das LLM sauberes JSON liefert
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Wenn das fehlschlägt, versuche, Markdown-Codeblöcke zu entfernen
        response_text = re.sub(r"^```(?:json)?\s*", "", response_text, flags=re.IGNORECASE)
        response_text = re.sub(r"\s*```$", "", response_text)

        # Suche nach dem ersten vollständigen JSON-Objekt im Text
        # Dies handhabt Fälle, in denen das LLM vor oder nach dem JSON noch Text ausgibt.
        match = re.search(r"\{[\s\S]*\}", response_text)  # [\s\S] matched auch Newlines
        if match:
            json_str = match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"JSON-Parsing-Fehler nach Regex: {e}")
                print(f"Fehlerhafter JSON-String: >>>{json_str}<<<")
                return {}  # Leeres Dict zurückgeben
        else:
            print("Kein JSON-Objekt im Antworttext gefunden.")
            print(f"Antworttext war: >>>{response_text}<<<")
            return {}


def process_all_pdfs(ordner, out_csv="extraktion_llm_ergebnisse.csv"):
    fieldnames = [
        "Datei", "Rechnungsnummer", "Datum", "Bezeichnung", "MwSt-Satz",
        "MwSt-Betrag", "Gesamtbetrag", "Nettobetrag", "Lieferant", "Roher_OCR_Text", "Rohe_LLM_Antwort"
    ]
    ergebnisse = []
    for dateiname in os.listdir(ordner):
        if dateiname.lower().endswith(".pdf"):
            pfad = os.path.join(ordner, dateiname)
            print(f"Verarbeite: {dateiname}")
            roher_ocr_text = ""
            rohe_llm_antwort = ""
            try:
                ocr_text = ask_pdf_ocr(pfad, dpi=300)  # DPI hier konsistent halten
                roher_ocr_text = ocr_text  # Für Debugging speichern
                # print(f"--- OCR Text für {dateiname} ---")
                # print(ocr_text)
                # print(f"--- Ende OCR Text ---")

                if not ocr_text.strip():
                    print(f"Warnung: OCR-Text für {dateiname} ist leer.")
                    result_json = {}
                else:
                    llm_result_str = extract_with_llm(ocr_text)
                    rohe_llm_antwort = llm_result_str  # Für Debugging speichern
                    # print(f"--- LLM Output String für {dateiname} ---")
                    # print(llm_result_str)
                    # print(f"--- Ende LLM Output String ---")
                    result_json = extract_json_from_response(llm_result_str)
                    print(result_json)

                if not result_json:
                    print(f"Warnung: Konnte keine valide JSON-Antwort parsen für {dateiname}.")

                row = {
                    "Datei": dateiname,
                    "Rechnungsnummer": result_json.get("Rechnungsnummer", "NICHT GEFUNDEN"),
                    "Datum": result_json.get("Datum", "NICHT GEFUNDEN"),
                    "Bezeichnung": result_json.get("Bezeichnung", "NICHT GEFUNDEN"),
                    "MwSt-Satz": result_json.get("MwSt-Satz", "NICHT GEFUNDEN"),
                    "MwSt-Betrag": result_json.get("MwSt-Betrag", "NICHT GEFUNDEN"),
                    "Gesamtbetrag": result_json.get("Gesamtbetrag", "NICHT GEFUNDEN"),
                    "Nettobetrag": result_json.get("Nettobetrag", "NICHT GEFUNDEN"),
                    "Lieferant": result_json.get("Lieferant", "NICHT GEFUNDEN"),
                    "Roher_OCR_Text": roher_ocr_text,
                    "Rohe_LLM_Antwort": rohe_llm_antwort
                }
                ergebnisse.append(row)

            except Exception as e:
                print(f"Fehler bei der Verarbeitung von {dateiname}: {e}")
                ergebnisse.append({
                    "Datei": dateiname, "Rechnungsnummer": "FEHLER", "Datum": "FEHLER",
                    "Bezeichnung": "FEHLER", "MwSt-Satz": "FEHLER", "MwSt-Betrag": "FEHLER",
                    "Gesamtbetrag": "FEHLER", "Nettobetrag": "FEHLER", "Lieferant": "FEHLER",
                    "Roher_OCR_Text": roher_ocr_text, "Rohe_LLM_Antwort": str(e)
                })

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ergebnisse)
    print(f"Ergebnisse gespeichert in {out_csv}")


def batch():
    main_dir = r"C:\Users\surin\Meine Ablage (surinder.ram@gmail.com)\Firma\Belege\2024"  # Beispielpfad anpassen

    for ordner_name in os.listdir(main_dir):
        ordner_pfad = os.path.join(main_dir, ordner_name)
        if os.path.isdir(ordner_pfad):
            csv_name = os.path.join(main_dir,
                                    f"extraktion_{ordner_name}.csv")  # CSV im Hauptordner speichern, um Verwechslung zu vermeiden
            print(f"\nVerarbeite Ordner: {ordner_name} -> {csv_name}")
            process_all_pdfs(ordner_pfad, out_csv=csv_name)



def einzeltest():
    # Einzeltest:
    # Passe den Pfad zu einer deiner PDF-Dateien an
    # file_path = r"C:\Pfad\zu\deiner\Testrechnung.pdf"
    file_path = r"C:\Users\surin\Meine Ablage (surinder.ram@gmail.com)\Firma\Belege\2024\Bewirtung\208_Hofer_Bewirtung_12_10_2024.pdf"

    print(f"Teste einzelne Datei: {file_path}")
    try:
        ocr_text = ask_pdf_ocr(file_path, page_number=0, dpi=300, lang="deu")  # DPI hier konsistent halten
        print("--- Roher OCR Text ---")
        print(ocr_text)
        print("--- Ende OCR Text ---\n")

        if ocr_text and ocr_text.strip():
            llm_response_str = extract_with_llm(ocr_text)
            print("--- Rohe LLM Antwort ---")
            print(llm_response_str)
            print("--- Ende Rohe LLM Antwort ---\n")

            extracted_json = extract_json_from_response(llm_response_str)
            print("--- Extrahiertes JSON ---")
            print(json.dumps(extracted_json, indent=2, ensure_ascii=False))
            print("--- Ende Extrahiertes JSON ---")
        else:
            print("OCR-Text ist leer, LLM-Extraktion übersprungen.")

    except Exception as e:
        print(f"Fehler im Einzeltest: {e}")

if __name__ == "__main__":
     batch() # Für die Verarbeitung aller Ordner
    # einzeltest()
