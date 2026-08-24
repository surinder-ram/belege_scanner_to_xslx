import os
import re
import json
import base64
import shutil
import requests
import pandas as pd
import pymupdf  # pip install pymupdf (nicht mehr "PyMuPDF"/"fitz" installieren)

# ===================== CONFIG =====================
# Bitte prüfe in LM Studio, ob der Port wirklich stimmt (Server-Tab -> "Local Server").
API_URL = "http://10.0.0.20:1234/v1/chat/completions"

# Empfehlung für RTX 4060 Ti 16GB (Stand: heute):
#   - Schnell & passt komplett ins VRAM:  "qwen3-vl-8b-instruct"      (Q8_0, ~9-10 GB)
#   - Beste Qualität, darf langsam sein:  "qwen3-vl-30b-a3b-instruct" (Q4_K_S/M, ~17-19 GB,
#     läuft mit leichtem CPU-Offload, bleibt dank MoE-Architektur trotzdem brauchbar schnell)
# Der Name hier muss mit dem in LM Studio geladenen Modell übereinstimmen (siehe Server-Tab).
MODEL_NAME = "qwen3-vl-30b-a3b-instruct"

BASE_FOLDER = r"C:\temp\Rechnung2026\Rechnungen"

# Name des Unterordners (wird in jedem verarbeiteten Ordner angelegt), in den die
# umbenannten Kopien geschrieben werden. Die Originaldateien bleiben unangetastet.
RENAMED_SUBFOLDER = "_umbenannt"

UMLAUT_MAP = str.maketrans({
    "ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"
})


def sanitize_for_filename(text):
    """Macht aus z.B. 'Wasserhahn Grohe' -> 'WasserhahnGrohe', filesystem-sicher."""
    if not text:
        return ""
    text = str(text).translate(UMLAUT_MAP)
    words = re.findall(r"[A-Za-z0-9]+", text)
    return "".join(w[:1].upper() + w[1:] for w in words) or "Unbekannt"


def format_date_for_filename(datum_str):
    """'01.03.2026' -> '01-03-2026'. Bei fehlendem/unlesbarem Datum: 'OhneDatum'."""
    if not datum_str:
        return "OhneDatum"
    match = re.match(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})", str(datum_str).strip())
    if not match:
        return "OhneDatum"
    tag, monat, jahr = match.groups()
    if len(jahr) == 2:
        jahr = "20" + jahr
    return f"{int(tag):02d}-{int(monat):02d}-{jahr}"


def clean_to_float(val):
    if val is None or val == "": return 0.0
    s = str(val).replace("EUR", "").replace("€", "").strip()
    if "," in s and "." in s: s = s.replace(".", "")
    s = s.replace(",", ".")
    try:
        match = re.search(r"[-+]?\d*\.\d+|\d+", s)
        return float(match.group(0)) if match else 0.0
    except:
        return 0.0


def process_with_vision_model(pdf_path):
    filename = os.path.basename(pdf_path)
    print(f"\n{'=' * 50}")
    print(f"📄 DATEI: {filename}")

    try:
        doc = pymupdf.open(pdf_path)
        # Render Seite 1 (höhere Auflösung hilft bei kleinen Kassenbons/Thermodruck)
        pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(4.0, 4.0))
        base64_image = base64.b64encode(pix.tobytes("png")).decode('utf-8')

        prompt = """Analysiere diesen Beleg (Rechnung/Kassenbon) für die steuerliche Erfassung.
Extrahiere die Daten als JSON. Gib NUR das JSON zurück, keinen weiteren Text.

Hinweise:
- "Land": das Land des Lieferanten/Ausstellers als ISO-Ländercode (z.B. "AT", "DE", "IT"),
  ermittelt aus Adresse, Telefonvorwahl oder UID-Nummer (z.B. ATU... = AT, DE... = DE).
- "Datum": das Rechnungs-/Belegdatum, wie auf dem Beleg aufgedruckt.
- "Abbuchungsdatum": NUR falls auf dem Beleg selbst ein tatsächliches Zahlungs-/Abbuchungsdatum
  vermerkt ist (z.B. bei Kartenzahlungsbelegen oder Zahlungsbestätigungen). Steht auf dem Beleg
  nur das Rechnungsdatum, lasse dieses Feld leer ("") - es NICHT mit dem Rechnungsdatum gleichsetzen.
- "MwSt_Satz": Steuersatz in Prozent (z.B. "20%"). Falls mehrere Sätze vorkommen, den
  Hauptsatz bzw. alle als kommagetrennte Liste angeben.
- "Kurzbezeichnung": 1-3 Wörter, was gekauft wurde, für einen Dateinamen geeignet
  (z.B. "Wasserhahn Grohe", "Kleber", "Bürobedarf", "Kabelbinder"). Bei mehreren
  unterschiedlichen Artikeln den Hauptartikel bzw. die Kategorie nennen. Keine
  Sonderzeichen, keine Satzzeichen.

{
  "Lieferant": "",
  "Land": "",
  "Datum": "TT.MM.JJJJ",
  "Abbuchungsdatum": "TT.MM.JJJJ",
  "Bezeichnung": "",
  "Kurzbezeichnung": "",
  "MwSt_Satz": "",
  "MwSt_Betrag": "",
  "Gesamt": "",
  "Netto": ""
}"""

        payload = {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                    ]
                }
            ],
            "temperature": 0.0
        }

        print(f"📡 Sende an LM Studio (Modell: {MODEL_NAME}) ...")
        # Größeres Modell + evtl. CPU-Offload -> mehr Timeout einplanen
        response = requests.post(API_URL, json=payload, timeout=600)

        if response.status_code != 200:
            print(f"❌ HTTP FEHLER {response.status_code}: {response.text}")
            return None

        res_data = response.json()

        if "choices" in res_data:
            content = res_data["choices"][0]["message"]["content"]
            print(f"\n--- ROHER TEXT VOM MODELL ---")
            print(content if content else "[LEERE ANTWORT]")
            print(f"-----------------------------\n")

            if not content:
                return None

            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                json_str = match.group(0)
                # Fix für fehlende Quotes bei Prozentangaben
                json_str = re.sub(r':\s?(\d+)%', r': "\1%"', json_str)
                return json.loads(json_str)
            else:
                print("⚠️ Regex konnte kein JSON finden.")
                return None
        else:
            print(f"❌ Unerwartetes Antwort-Format: {res_data}")
            return None

    except Exception as e:
        print(f"⚠️ Script-Fehler bei {filename}: {e}")
        return None


def main():
    print(f"🚀 Starte Analyse mit {MODEL_NAME} ...")

    for root, dirs, files in os.walk(BASE_FOLDER):
        pdfs = [f for f in files if f.lower().endswith('.pdf')]
        if not pdfs: continue

        print(f"\n📂 ORDNER: {os.path.basename(root)}")
        extracted_results = []

        zielordner = os.path.join(root, RENAMED_SUBFOLDER)
        counter = 1

        for f in pdfs:
            data = process_with_vision_model(os.path.join(root, f))
            if data:
                lieferant_clean = sanitize_for_filename(data.get("Lieferant"))
                kurz_clean = sanitize_for_filename(data.get("Kurzbezeichnung") or data.get("Bezeichnung"))
                datum_clean = format_date_for_filename(data.get("Datum"))
                neuer_name = f"{counter:03d}_{lieferant_clean}_{kurz_clean}_{datum_clean}.pdf"

                os.makedirs(zielordner, exist_ok=True)
                shutil.copy2(os.path.join(root, f), os.path.join(zielordner, neuer_name))

                cleaned = {
                    "Nr": counter,
                    "Datei_Original": f,
                    "Neuer_Dateiname": neuer_name,
                    "Datum": data.get("Datum"),
                    "Abbuchungsdatum": data.get("Abbuchungsdatum"),
                    "Lieferant": data.get("Lieferant"),
                    "Land": data.get("Land"),
                    "Bezeichnung": data.get("Bezeichnung"),
                    "Kurzbezeichnung": data.get("Kurzbezeichnung"),
                    "MwSt_Satz": data.get("MwSt_Satz"),
                    "MwSt_Betrag": clean_to_float(data.get("MwSt_Betrag")),
                    "Brutto": clean_to_float(data.get("Gesamt") or data.get("Gesamtbetrag")),
                    "Netto": clean_to_float(data.get("Netto") or data.get("Nettobetrag"))
                }
                extracted_results.append(cleaned)
                counter += 1
                print(f"✅ ERGEBNIS: {cleaned['Brutto']}€ | Land: {cleaned['Land']} | -> {neuer_name}")
            else:
                print(f"❌ DATEI ÜBERSPRUNGEN.")

        if extracted_results:
            df = pd.DataFrame(extracted_results)
            output_name = f"_Steuer_Extraktion_{os.path.basename(root)}.xlsx"
            df.to_excel(os.path.join(root, output_name), index=False)
            print(f"\n💾 EXCEL GESPEICHERT: {output_name}")


if __name__ == "__main__":
    main()