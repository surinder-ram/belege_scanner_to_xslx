
import base64
import requests
from image_coding import pdf_to_base64, save_base64_as_png

def call_model_with_images(base64_images):
    """
    Ruft das Modell auf und übergibt ihm die Base64-kodierten Bilder.

    :param base64_images: Liste der Base64-kodierten Bilder
    :return: Modellantwort
    """
    url = "http://127.0.0.1:1233/v1/chat/completions"

    # Generiere die Anfrage
    data = {
        "model": "llama-3.1-unhinged-vision-8b",  # Dein Modell
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Dies ist eine Rechnung im png format (aus einem pdf erstellt). Extrahiere bitte folgende Informationen: Datum, MwSt. (nur Zahl), Kaufobjekt."
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_images[0]}"}  # Hier verwenden wir das erste Bild
                    }
                ]
            }
        ],
        "temperature": 0.7,
        "max_tokens": -1,
        "stream": False
    }

    output_path = "c:\\temp\\output_image.png"
    save_base64_as_png(base64_images[0], output_path)

    # Sende die Anfrage
    response = requests.post(url, json=data)

    # Gib die Antwort zurück
    return response.json()

def extract_information_from_response(response):
    """
    Extrahiert relevante Daten (Datum, MwSt., und Kaufobjekt) aus der Modellantwort.

    :param response: Modellantwort
    :return: Extrahierte Daten
    """
    try:
        response_text = response["choices"][0]["message"]["content"]

        # Hier können einfache Such- oder Reguläre Ausdrücke verwendet werden
        extracted_data = {
            "Datum": None,
            "MwSt. Betrag": None,
            "MwSt. Prozent": None,
            "Kaufobjekt": None
        }

        # Beispiel für einfache Textextraktion
        if "Datum" in response_text:
            extracted_data["Datum"] = response_text.split("Datum:")[1].split("\n")[0].strip()
        if "MwSt." in response_text:
            extracted_data["MwSt. Betrag"] = response_text.split("MwSt. Betrag:")[1].split("\n")[0].strip()
            extracted_data["MwSt. Prozent"] = response_text.split("MwSt. Prozent:")[1].split("\n")[0].strip()
        if "Kaufobjekt" in response_text:
            extracted_data["Kaufobjekt"] = response_text.split("Kaufobjekt:")[1].split("\n")[0].strip()

        return extracted_data

    except Exception as e:
        print(f"Fehler bei der Extraktion der Daten: {str(e)}")
        return None

def main(pdf_path):
    """
    Der Hauptprozess, der PDF in Bilder umwandelt, das Modell abruft und Daten extrahiert.

    :param pdf_path: Pfad zur PDF-Datei
    """
    # Schritt 1: PDF in Base64-Bilder umwandeln
    base64_images = pdf_to_base64(pdf_path)

    # Schritt 2: Anfrage an das Modell senden
    response = call_model_with_images(base64_images)

    # Schritt 3: Extrahiere die relevanten Informationen aus der Modellantwort
    extracted_data = extract_information_from_response(response)

    # Ausgabe der extrahierten Informationen
    print(extracted_data)

# Beispielaufruf
pdf_path = "c:\\temp\\test_belege\\halter_monitor.pdf"  # Pfad zur PDF-Datei
main(pdf_path)
