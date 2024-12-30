import os
import json
import requests
import fitz  # PyMuPDF


def extract_text_from_pdf(pdf_path):
    """
    Extrahiert Text aus einer PDF-Datei mit PyMuPDF (fitz).
    """
    try:
        # Öffnen der PDF-Datei
        document = fitz.open(pdf_path)

        # Extrahieren des Textes aus allen Seiten
        text = ""
        for page_num in range(document.page_count):
            page = document.load_page(page_num)
            text += page.get_text("text")  # Text im reinen Textformat extrahieren

        return text
    except Exception as e:
        print(f"Fehler beim Extrahieren des Textes: {e}")
        return ""


def extract_info_from_text_with_model(text, model="meta-llama-3.1-8b-instruct"):
    """
    Sende den extrahierten Text an dein Modell, um spezifische Informationen zu extrahieren.
    """
    url = "http://localhost:1233/v1/chat/completions"  # Deine lokale Modell-URL
    headers = {"Content-Type": "application/json"}

    # Der prompt für die Extraktion der Informationen
    prompt = f"""
    Du bist ein Dokumentenanalyst. Bitte extrahier die folgenden Informationen aus dem Text:
    - Datum
    - Betrag
    - MwSt.
    - Beschreibung

    Text:
    {text}
    """

    # Aufbau der Anfrage an das Modell
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Du bist ein Assistent, der Informationen aus PDFs extrahiert."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 512,
        "stream": False
    }

    # Anfrage senden
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Fehler bei der HTTP-Anfrage auslösen
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Fehler bei der Anfrage an das Modell: {e}")
        return ""


def generate_filename_from_content(text):
    """
    Generiert einen kurzen Dateinamen basierend auf dem Textinhalt der PDF.
    Hier sicherstellen, dass nur der Name ohne zusätzliche Vorschläge zurückgegeben wird.
    """
    prompt = f"""
    Generiere einen kurzen Dateinamen basierend auf folgendem Inhalt:
    Der Name sollte das Datum und eine kurze Beschreibung des Kaufobjektes enthalten. Gib nur den Dateinamen zurück, wie zb. WD-Festplatte_27_10_2019.pdf

    Inhalt:
    {text}
    """

    url = "http://localhost:1233/v1/chat/completions"
    headers = {"Content-Type": "application/json"}

    payload = {
        "model": "meta-llama-3.1-8b-instruct",  # Dein Modell
        "messages": [
            {
                "role": "system",
                "content": "Du bist ein Assistent, der kurze, prägnante Dateinamen generiert."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.5,
        "max_tokens": 50,  # Maximale Länge des Dateinamens
        "stream": False
    }

    # Anfrage senden
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Fehler bei der HTTP-Anfrage auslösen
        # Der Modellname sollte jetzt direkt nur den Dateinamen zurückgeben
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Fehler bei der Anfrage an das Modell: {e}")
        return "unbekanntes_dokument"


def process_pdfs_in_directory(directory, output_directory):
    """
    Verarbeitet alle PDF-Dateien im angegebenen Verzeichnis und speichert die Ergebnisse als strukturierte JSON-Dateien.
    """
    pdf_files = [f for f in os.listdir(directory) if f.endswith('.pdf')]

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    for pdf_file in pdf_files:
        pdf_path = os.path.join(directory, pdf_file)
        print(f"Verarbeite: {pdf_path}")

        # Extrahiere den Text aus der PDF
        pdf_text = extract_text_from_pdf(pdf_path)

        if pdf_text:
            # Extrahiere Informationen mit deinem Modell
            extracted_info = extract_info_from_text_with_model(pdf_text)
            if extracted_info:
                # Strukturierte Daten erstellen
                structured_data = {
                    "file": pdf_file,
                    "extracted_info": {
                        "date": None,
                        "amount": None,
                        "vat": None,
                        "description": None,
                        "generated_filename": None  # Hier wird der Dateiname gespeichert
                    }
                }

                # Annehmen, dass das Modell die Informationen als Text zurückgibt
                # Wir könnten hier ein einfaches Parsing durchführen, um die Werte zu extrahieren
                # z.B. mit regulären Ausdrücken oder einem einfachen Split

                # Beispiel: Parsing der Ergebnisse (du kannst es nach Bedarf anpassen)
                lines = extracted_info.split("\n")
                for line in lines:
                    if "Datum" in line:
                        structured_data["extracted_info"]["date"] = line.split(":")[-1].strip()
                    elif "Betrag" in line:
                        structured_data["extracted_info"]["amount"] = line.split(":")[-1].strip()
                    elif "MwSt" in line:
                        structured_data["extracted_info"]["vat"] = line.split(":")[-1].strip()
                    elif "Beschreibung" in line:
                        structured_data["extracted_info"]["description"] = line.split(":")[-1].strip()

                # Generiere einen Dateinamen basierend auf dem Inhalt
                generated_filename = generate_filename_from_content(pdf_text)
                structured_data["extracted_info"]["generated_filename"] = generated_filename

                # Speichern der extrahierten Informationen in einer strukturierten JSON-Datei
                json_path = os.path.join(output_directory, f"{pdf_file}.json")
                with open(json_path, 'w', encoding='utf-8') as json_file:
                    json.dump(structured_data, json_file, ensure_ascii=False, indent=4)
                print(f"Ergebnisse gespeichert in: {json_path}")
            else:
                print(f"Keine Informationen extrahiert aus {pdf_file}.")
        else:
            print(f"Kein Text aus {pdf_file} extrahiert.")


# Hauptprogramm
directory = r"C:\temp\test_belege"  # Verzeichnis mit den PDF-Dateien
output_directory = directory
process_pdfs_in_directory(directory, output_directory)
