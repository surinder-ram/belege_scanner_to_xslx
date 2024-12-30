import os
from openai import OpenAI

# Connect to LM Studio
client = OpenAI(base_url="http://localhost:1233/v1/", api_key="lm-studio")


def extract_info_from_pdf(pdf_path):
    """
    Sends a PDF file to the model to extract specific information.
    """
    with open(pdf_path, 'rb') as pdf_file:
        pdf_data = pdf_file.read()

    try:
        response = client.Completion.create(
            model="dein-modell-name",  # Ersetze mit deinem Modellnamen
            files=[("file", pdf_path, pdf_data)],  # PDF als Datei anhängen
            prompt="""
                Bitte extrahiere die folgenden Informationen aus der hochgeladenen PDF:
                - Datum
                - Betrag
                - MwSt.
                - Beschreibung

                Gib die Ergebnisse im JSON-Format zurück.
            """,
            max_tokens=200,
            temperature=0.2
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"Fehler bei der Verarbeitung von {pdf_path}: {e}")
        return ""


def process_pdfs_in_directory(directory):
    """
    Processes all PDF files in the given directory.
    """
    pdf_files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    results = {}

    for pdf_file in pdf_files:
        pdf_path = os.path.join(directory, pdf_file)
        print(f"Verarbeite: {pdf_path}")
        extracted_info = extract_info_from_pdf(pdf_path)
        if extracted_info:
            results[pdf_file] = extracted_info
        else:
            print(f"Keine Informationen extrahiert aus {pdf_file}.")

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
