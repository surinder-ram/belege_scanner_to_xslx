import os
import re
import json
import base64
import requests
import pandas as pd
import fitz  # PyMuPDF

# ===================== CONFIG =====================
# Bitte prüfe in LM Studio, ob der Port wirklich 1233 ist!
API_URL = "http://localhost:1233/v1/chat/completions"
MODEL_NAME = "google/gemma-4-26b-a4b"
BASE_FOLDER = r"C:\Users\surin\Meine Ablage (surinder.ram@gmail.com)\Firma\Belege\2025"


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


def process_with_gemma_vision(pdf_path):
    filename = os.path.basename(pdf_path)
    print(f"\n{'=' * 50}")
    print(f"📄 DATEI: {filename}")

    try:
        doc = fitz.open(pdf_path)
        # Render Seite 1
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(3.0, 3.0))
        base64_image = base64.b64encode(pix.tobytes("png")).decode('utf-8')

        prompt = """Analysiere diesen Beleg. Extrahiere die Daten als JSON.
Gib NUR das JSON zurück.

{
  "Lieferant": "",
  "Datum": "TT.MM.JJJJ",
  "Bezeichnung": "",
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

        print(f"📡 Sende an LM Studio...")
        response = requests.post(API_URL, json=payload, timeout=300)

        # --- DEBUG: Rohe Server-Antwort ---
        if response.status_code != 200:
            print(f"❌ HTTP FEHLER {response.status_code}: {response.text}")
            return None

        res_data = response.json()

        # --- DEBUG: Was das Modell wirklich gesagt hat ---
        if "choices" in res_data:
            content = res_data["choices"][0]["message"]["content"]
            print(f"\n--- ROHER TEXT VOM MODELL ---")
            print(content if content else "[LEERE ANTWORT]")
            print(f"-----------------------------\n")

            if not content:
                return None

            # Suche JSON
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                json_str = match.group(0)
                # Fix für fehlende Quotes bei MwSt
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
    print(f"🚀 Starte Analyse mit Gemma-4-26b-Vision...")

    for root, dirs, files in os.walk(BASE_FOLDER):
        pdfs = [f for f in files if f.lower().endswith('.pdf')]
        if not pdfs: continue

        print(f"\n📂 ORDNER: {os.path.basename(root)}")
        extracted_results = []

        for f in pdfs:
            data = process_with_gemma_vision(os.path.join(root, f))
            if data:
                cleaned = {
                    "Datei": f,
                    "Datum": data.get("Datum"),
                    "Lieferant": data.get("Lieferant"),
                    "Bezeichnung": data.get("Bezeichnung"),
                    "MwSt_Satz": data.get("MwSt_Satz"),
                    "MwSt_Betrag": clean_to_float(data.get("MwSt_Betrag")),
                    "Brutto": clean_to_float(data.get("Gesamt") or data.get("Gesamtbetrag")),
                    "Netto": clean_to_float(data.get("Netto") or data.get("Nettobetrag"))
                }
                extracted_results.append(cleaned)
                print(f"✅ ERGEBNIS: {cleaned['Brutto']}€")
            else:
                print(f"❌ DATEI ÜBERSPRUNGEN.")

        if extracted_results:
            df = pd.DataFrame(extracted_results)
            output_name = f"_Steuer_Gemma4_{os.path.basename(root)}.xlsx"
            df.to_excel(os.path.join(root, output_name), index=False)
            print(f"\n💾 EXCEL GESPEICHERT: {output_name}")


if __name__ == "__main__":
    main()