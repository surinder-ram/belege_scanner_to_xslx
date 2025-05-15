

#obsolet code, do not use

import os
import fitz  # PyMuPDF für die PDF-Verarbeitung
import pandas as pd
from PIL import Image
import pytesseract
import io
import requests
from datetime import datetime
from dateutil import parser
import openai

# Pfade definieren
directory_path = r"C:\\Users\\surin\\Meine Ablage\\Firma\\Belege\\2023\\Telekom"  # Hier den Pfad zu Ihrem Verzeichnis mit den PDFs angeben
output_excel_path = r"C:\\temp\\Telekom.xlsx"  # Hier den Pfad für die Ausgabe der Excel-Datei angeben

# Funktion zur Extraktion von Text aus PDFs mit PyMuPDF und pytesseract
def extract_text_with_ocr(pdf_path):
    text = ""
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), dpi=600)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        custom_config = r'--oem 1 --psm 3 -l deu'  # Beispiel: Verwendung von LSTM-basierten Engine und Auto Page Segmentation Mode
        text += pytesseract.image_to_string(img, config=custom_config)
    return text


# Funktion zum Abrufen von Daten über LLM
def extract_data_with_llm(text, prompt, api_url, api_key, model_name):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    system_prompt = "you will parse information from an invoice. the invoice contains lot of data which is maybe shuffled."
    data = {"model": model_name, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}, {"role": "user", "content": text}], "max_tokens": 120000,
        "temperature": 0.7}
    response = requests.post(f"{api_url}/chat/completions", headers=headers, json=data)

    try:
        response_json = response.json()
        print(response_json)  # Zum Debuggen
        result = response_json.get("choices", [])[0].get("message", {}).get("content", "").strip()
    except Exception as e:
        print(f"Error during LLM request: {e}")
        result = ""

    return result

# Funktion zur Verarbeitung des Verzeichnisses mit PDFs
def process_pdf_directory(directory, api_url, api_key, model_name):
    data = []
    for filename in os.listdir(directory):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(directory, filename)
            print(f"Verarbeite Datei: {pdf_path}")
            ocr_text = extract_text_with_ocr(pdf_path)
            print(f"Extrahierter OCR-Text:\n{ocr_text}\n")
            datum_prompt = "Finde das Bestelldatum der Rechnung. Das Ausgabeformat soll TT.MM.JJJJ sein. Wenn kein Datum gefunden werden kann, gebe 01.01.1900 aus. Deine Antwort soll nur das Datum beinhalten bitte keinen weiteren Text. \n"
            betrag_prompt = "Finde den bezahlten Gesamtbetrag aus dem Text heraus. Das Ausgabeformat soll xx,xx sein. Wenn kein Gesamtbetrag gefunden werden kann, gebe 00,00 aus. Die Rückgabe soll nur ein Betrag sein bitte keinen weiteren Text (auch kein € zeichen).#"
            datum = extract_data_with_llm(ocr_text, datum_prompt, api_url, api_key,model_name)
            betrag = extract_data_with_llm(ocr_text, betrag_prompt, api_url, api_key,model_name)

            formatted_date = datum
            formatted_amount = betrag
            date_comment = None
            amount_comment = None
            print(f"Extrahiertes Datum: {formatted_date}")
            print(f"Extrahierter Betrag: {formatted_amount}")


            data.append({'Dateiname': filename, 'Datum': formatted_date, 'Betrag': formatted_amount, 'datum-Kommentar': date_comment, 'betrag-Kommentar': amount_comment})
    return data



# API-Informationen
api_url = "http://localhost:1234/v1"  # Beispiel für die lokale API-URL
api_key = "lm-studio"  # API-Schlüssel, wenn erforderlich
model_name = "rubra-ai/Phi-3-mini-128k-instruct-GGUF"  # Name des Modells

# Verzeichnis verarbeiten und Daten in Excel speichern
extracted_data = process_pdf_directory(directory_path, api_url, api_key, model_name)


df = pd.DataFrame(extracted_data)
df.to_excel(output_excel_path, index=False)
print(f"Daten wurden erfolgreich in {output_excel_path} gespeichert.")


