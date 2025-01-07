import fitz  # PyMuPDF
import re
import requests
import base64


# Funktion zum Extrahieren von Text aus einer PDF-Datei
def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extrahiert den gesamten Text aus einer PDF-Datei.

    :param pdf_path: Pfad zur PDF-Datei.
    :return: Gesamter extrahierter Text der PDF.
    """
    try:
        pdf_document = fitz.open(pdf_path)
        full_text = ""
        for page_num in range(pdf_document.page_count):
            page = pdf_document.load_page(page_num)
            full_text += page.get_text()  # Extrahiere den Text von jeder Seite
        return full_text
    except Exception as e:
        raise RuntimeError(f"Fehler bei der Textextraktion: {str(e)}")


# Extrahiert das Datum (Format: dd.mm.yyyy)
def extract_date(text: str) -> str:
    match = re.search(r'\b\d{2}\.\d{2}\.\d{4}\b', text)
    return match.group() if match else ""


# Extrahiert den Betrag (Format: xx,xx)
def extract_amount(text: str) -> float:
    match = re.search(r'\b\d+,\d{2}\b', text)
    return float(match.group().replace(',', '.')) if match else 0.0


# Extrahiert den MwSt.-Betrag (xx ohne Prozentsatz)
def extract_vat(text: str) -> float:
    match = re.search(r'\b\d+,\d{2}(?=\s*(%|MwSt|Steuer))\b', text)
    return float(match.group().replace(',', '.')) if match else 0.0


# Extrahiert die Beschreibung (maximal 50 Zeichen)
def extract_description(text: str) -> str:
    match = re.search(r'([A-Za-z0-9\s,;:.-]{1,50})', text)
    return match.group(0) if match else ""


# Funktion zur Nachrichtenerstellung und Modellaufruf
def generate_and_call_model(pdf_path: str, model_url: str):
    """
    Extrahiert Informationen aus einer PDF, erstellt eine Nachricht und ruft das Modell auf.

    :param pdf_path: Der Pfad zur PDF-Datei.
    :param model_url: Die URL des Modells.
    :return: Die Antwort des Modells.
    """
    # Extrahiere Text aus der PDF
    text = extract_text_from_pdf(pdf_path)

    # Extrahiere die relevanten Daten
    details = {
        'Datum': extract_date(text),
        'Betrag': extract_amount(text),
        'MwSt.': extract_vat(text),
        'Beschreibung': extract_description(text)
    }

    # Generiere die Nachricht
    message = f"""
    Hier sind die extrahierten Informationen aus der PDF:
    - Datum: {details['Datum']}
    - Betrag: {details['Betrag']} EUR
    - MwSt.: {details['MwSt.']} EUR
    - Beschreibung: {details['Beschreibung']}
    """

    # Erstelle die Datenstruktur für den Modellaufruf
    payload = {
        "model": "llama-3.1-unhinged-vision-8b",  # Beispielmodell
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": message},
                ]
            }
        ],
        "temperature": 0.7,
        "max_tokens": -1,
        "stream": False
    }

    # Sende die Anfrage an das Modell
    response = requests.post(model_url, json=payload)

    if response.status_code == 200:
        return response.json()
    else:
        raise RuntimeError(f"Fehler beim Modellaufruf: {response.status_code} - {response.text}")


# Beispiel der Verwendung
pdf_path = r"c://temp//test_belege//halter_monitor.pdf"
model_url = "http://127.0.0.1:1233/v1/chat/completions"
response = generate_and_call_model(pdf_path, model_url)

# Ausgabe der Modellantwort
print(response)
