

import ollama
from PIL import Image
from pdf2image import convert_from_path

import io
import re
import time

import spacy #python -m spacy download de_core_news_sm  # für Deutsch
# Lade das deutsche Sprachmodell in spaCy
nlp = spacy.load('de_core_news_sm')


def load_file_as_bytestream(file_path: str) -> bytes:
    """
    Lädt eine Datei und gibt den Inhalt als Bytestream zurück (ähnlich wie Streamlit).

    :param file_path: Pfad zur Datei (z. B. .png, .jpg, .jpeg).
    :return: Inhalt der Datei als Bytestream.
    """
    try:
        with open(file_path, "rb") as file:
            return file.read()
    except Exception as e:
        print(f"Fehler beim Laden der Datei: {e}")
        return None




def load_file_from_pdf_as_bytestream(pdf_path: str) -> bytes:
    """
    Lädt ein PDF, konvertiert die erste Seite in ein Bild und gibt den Bytestream des Bildes zurück.

    :param pdf_path: Pfad zur PDF-Datei.
    :return: Bytestream des Bildes (als PNG).
    """
    try:
        # Konvertiere die PDF in Bilder (nur die erste Seite)
        images = convert_from_path(pdf_path, dpi=400)  # 300 dpi für gute Qualität
        if not images:
            raise ValueError("Keine Bilder im PDF gefunden.")

        # Wähle das erste Bild
        first_image = images[0]

        # Speicher das Bild in einen Bytestream
        image_stream = io.BytesIO()
        first_image.save(image_stream, format='PNG')  # Speichere als PNG
        image_stream.seek(0)  # Setze den Stream-Zeiger auf den Anfang

        return image_stream.read()

    except Exception as e:
        raise RuntimeError(f"Fehler beim Laden des PDFs als Bild-Bytestream: {e}")





def parse_extracted_data(extracted_text: str) -> dict:
    """
    Verarbeitet den extrahierten Text durch das Llama-Modell und gibt strukturierte Daten zurück.

    :param extracted_text: String mit den extrahierten Rechnungsdaten.
    :return: Dictionary mit den verarbeiteten Werten (Betrag, MwSt, Produktbezeichnung, Dateiname).
    """
    try:
        # Prompt für das Modell
        prompt = f"""
        Hier sind die extrahierten Rechnungsdaten:
        {extracted_text}

        Verarbeite die Daten und extrahiere die folgenden Informationen:
        1. Betrag (nur der Betrag ohne Währung)
        2. MwSt-Prozentsatz (nur der Prozentsatz ohne das Prozentzeichen)
        3. Produktbezeichnung (max. 40 Zeichen)
        4. Dateiname (aus der Rechnung, möglichst prägnant)

        Gib die Daten im folgenden Format zurück:
        Betrag: <Betrag>
        MwSt: <MwSt-Prozentsatz>
        Produktbezeichnung: <Produktbezeichnung>
        Dateiname: <Dateiname>
        """

        # Llama Modell anrufen
        response = ollama.chat(
            model='llama3.2-vision',
            messages=[{
                'role': 'user',
                'content': prompt
            }]
        )

        # Antwort des Modells verarbeiten
        response_content = response['message']['content']

        # Hier den Antwortstring verarbeiten und in ein Dictionary umwandeln
        parsed_data = {}
        lines = response_content.split("\n")

        for line in lines:
            if line.startswith("Betrag:"):
                parsed_data["Betrag"] = line.replace("Betrag:", "").strip()
            elif line.startswith("MwSt:"):
                parsed_data["MwSt"] = line.replace("MwSt:", "").strip()
            elif line.startswith("Produktbezeichnung:"):
                parsed_data["Produktbezeichnung"] = line.replace("Produktbezeichnung:", "").strip()
            elif line.startswith("Dateiname:"):
                parsed_data["Dateiname"] = line.replace("Dateiname:", "").strip()

        return parsed_data

    except Exception as e:
        raise ValueError(f"Fehler beim Verarbeiten des Textes: {str(e)}")


def get_image_response(uploaded_file):
                try:
                    response = ollama.chat(
                        model='llama3.2-vision',
                        messages=[{
                            'role': 'user',
                            'content': (
                                "Bitte analysiere die hochgeladene Rechnung und extrahiere folgende Informationen:\n\n"
                                "1. **MwSt-Prozentsatz**: Der Prozentsatz der Mehrwertsteuer (z. B. 19 oder 7).\n"
                                "2. **Betrag**: Der Gesamtbetrag in Euro (z. B. 123,45).\n"
                                "3. **Beschreibung**: Eine kurze, prägnante Beschreibung (maximal 40 Zeichen), "
                                "die das gekaufte Produkt oder die Dienstleistung beschreibt.\n"
                                "4. **Dateiname**: Vorschlag für einen geeigneten Dateinamen, der das Produkt oder die Dienstleistung widerspiegelt "
                                "(z. B. 'monitor_rechnung.pdf').\n\n"
                                "Bitte gebe die Ergebnisse in einer strukturierten und klaren Liste zurück. "
                                "Keine weiteren Details oder Informationen hinzufügen."
                            ),
                            'images': [uploaded_file]  # Bytestream der hochgeladenen Datei
                        }]
                    )

                    result = response.message.content
                except Exception as e:
                    print(f"Error processing image: {str(e)}")
                    result=[]
                return result


if __name__ == "__main__":
    a=time.time()
    print("processing")
    #image = load_file_as_bytestream("C:\\temp\\output_image.png")
    image = load_file_from_pdf_as_bytestream("C:\\temp\\test_belege\\Rechnung_USBC-VIdeo_kabel.pdf")
    response_text = get_image_response(image)
    b=time.time()
    print("...time consumed", int(b-a))

    print(response_text)
    parsed_data = parse_extracted_data(response_text)
    print(parsed_data)



