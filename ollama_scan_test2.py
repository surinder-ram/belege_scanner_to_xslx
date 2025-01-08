
import os
import ollama
from PIL import Image
from pdf2image import convert_from_path
import json
import io
import re
import time

import pathlib

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
        images = convert_from_path(pdf_path, dpi=350)  # 300 dpi für gute Qualität
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
        Hier sind extrahierte Rechnungsdaten aus einem Papierrechnunvg:
        {extracted_text}

        Verarbeite die Daten und extrahiere die folgenden Informationen:
        1. Betrag (nur der Betrag ohne Währung)
        2. MwSt-Prozentsatz (nur der Prozentsatz ohne das Prozentzeichen)
        3. Produktbezeichnung (max. 50 Zeichen)
        4. Dateiname (aus der Rechnung, möglichst prägnant)
        5. Datum (dd.mm.yyyy) (es soll das Rechnungsdatum sein)

        Gib die Daten im folgenden Format zurück:
        Betrag: <Betrag>
        MwSt: <MwSt-Prozentsatz>
        Produktbezeichnung: <Produktbezeichnung>
        Dateiname: <Dateiname>
        Datum: <Datum>
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

        # Verwenden von regulären Ausdrücken, um die Daten zu extrahieren
        betrag_match = re.search(r"Betrag:\s*([\d,]+(?:\s?€)?)", response_content)
        mwst_match = re.search(r"MwSt:\s*([\d,]+)%?", response_content)
        produktbezeichnung_match = re.search(r"Produktbezeichnung:\s*(.*?)\n", response_content)
        dateiname_match = re.search(r"Dateiname:\s*(\S+\.pdf)", response_content)
        datum_match = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", response_content)

        if betrag_match:
                parsed_data["Betrag"] = betrag_match.group(1).strip()
        if mwst_match:
                parsed_data["MwSt"] = mwst_match.group(1).strip()
        if produktbezeichnung_match:
                parsed_data["Produktbezeichnung"] = produktbezeichnung_match.group(1).strip()[:50]  # Max 50 Zeichen
        if dateiname_match:
                parsed_data["Dateiname"] = dateiname_match.group(1).strip()
        if datum_match:
                parsed_data["Datum"] = datum_match.group(1).strip()

        parsed_data["extracted_text-1"]=extracted_text
        parsed_data["response_content-2"]=response_content

        return parsed_data

    except Exception as e:
        raise ValueError(f"Fehler beim Verarbeiten des Textes: {str(e)}")
        return  "Error"


def get_image_response(uploaded_file):
                try:
                    response = ollama.chat(
                        model='llama3.2-vision',
                        messages=[{
                            'role': 'user',
                            'content': (
                                "Bitte analysiere die hochgeladene Rechnung und extrahiere folgende Informationen:\n\n"
                                "1. **MwSt-Prozentsatz**: Der Prozentsatz der Mehrwertsteuer (z. B. 19 oder 7) (manchmal kann es auch als UST genannt werden).\n"
                                "2. **Betrag**: Der Gesamtbetrag in Euro (z. B. 123,45).\n"
                                "3. **Beschreibung**: Eine kurze, prägnante Beschreibung (maximal 60 Zeichen) des Kaufs, möglichst auf übergeordnete Gattung nennen, und das ebenfalls danach das detail "
                                "die das gekaufte Produkt oder die Dienstleistung beschreibt.\n"
                                "4. **Dateiname**: Vorschlag für einen geeigneten Dateinamen, der das Produkt oder die Dienstleistung widerspiegelt (gerne auch die Gattung zb. Grafikarte), bitte nicht das Wort Rechnung verwenden "
                                "(positiv beispiel: 'monitor_rechnung_31_5_2024.pdf').\n"
                                "5. **Datum**: bitte gib mir das Rechnungsdatum \n\n"
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



def process_directory(directory_path):

    # Alle PDF-Dateien im Verzeichnis durchlaufen
    files = [f for f in os.listdir(directory_path) if f.endswith('.pdf')]

    # Liste zur Speicherung der extrahierten Daten
    all_data = []

    for file in files:
        process_single_file(directory_path, file)

    #print(f"done, saved in {json_output_path} .")





def process_single_file(directory_path, file):
    pdf_path = os.path.join(directory_path, file)

    # Lade das PDF als Bytestream (du hast die Funktion dafür)
    image = load_file_from_pdf_as_bytestream(pdf_path)

    # Hole die Antwort vom Modell
    a = time.time()
    print(f"processing file: {pdf_path}")

    response_text = get_image_response(image)
    #print(response_text)

    b = time.time()
    print(f"...time consumed: {int(b - a)} sec")

    # Parse die extrahierten Daten
    parsed_data = parse_extracted_data(response_text)
    print("parsed_data", parsed_data)

    # Speichere die Daten in der Liste
    # all_data.append(parsed_data)

    # Speichern der extrahierten Daten als JSON

    json_output_path = "C:\\temp\\" + file + ".json"
    with open(json_output_path, 'w', encoding='utf-8') as json_file:
        json.dump(parsed_data, json_file, ensure_ascii=False, indent=4)


if __name__ == "__main__":

    #directory
    process_directory(directory_path = "C:\\temp\\test_belege")

    #single file
    #process_single_file(directory_path = "C:\\temp\\test_belege", file="BohseKopfhörer_11_10_2024.pdf")




