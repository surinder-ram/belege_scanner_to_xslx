
import os
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
    Du bist ein Dokumentenanalyst. Bitte extrahiere die folgenden Informationen aus dem Text:
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

def process_pdfs_in_directory(directory):
    """
    Verarbeitet alle PDF-Dateien im angegebenen Verzeichnis.
    """
    pdf_files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    results = {}

    for pdf_file in pdf_files:
        pdf_path = os.path.join(directory, pdf_file)
        print(f"Verarbeite: {pdf_path}")

        # Extrahiere den Text aus der PDF
        pdf_text = extract_text_from_pdf(pdf_path)

        if pdf_text:
            # Extrahiere Informationen mit deinem Modell
            extracted_info = extract_info_from_text_with_model(pdf_text)
            if extracted_info:
                results[pdf_file] = extracted_info
            else:
                print(f"Keine Informationen extrahiert aus {pdf_file}.")
        else:
            print(f"Kein Text aus {pdf_file} extrahiert.")

    return results

# Hauptprogramm
directory = r"C:\temp\test_belege"  # Verzeichnis mit den PDF-Dateien
all_results = process_pdfs_in_directory(directory)

# Ergebnisse anzeigen
print("\nErgebnisse der Verarbeitung:")
for pdf_name, info in all_results.items():
    print(f"Datei: {pdf_name}")
    print(info)
    print("-" * 40)
