import base64
from pdf2image import convert_from_path


def pdf_to_base64(pdf_path: str) -> list:
    """
    Konvertiert die Seiten einer PDF-Datei in Base64-codierte PNG-Bilder.

    :param pdf_path: Pfad zur PDF-Datei.
    :return: Liste von Base64-codierten Strings der Bilder.
    """
    try:
        # PDF in Bilder umwandeln
        images = convert_from_path(pdf_path, dpi=200)

        # Base64-codierte Bilder speichern
        base64_images = []
        for image in images:
            # Bild in Base64 umwandeln
            with open("../temp_image.png", "wb") as temp_file:
                image.save(temp_file, format="PNG")
            with open("../temp_image.png", "rb") as temp_file:
                base64_image = base64.b64encode(temp_file.read()).decode("utf-8")
                base64_images.append(base64_image)

        return base64_images

    except Exception as e:
        raise RuntimeError(f"Fehler bei der PDF-Verarbeitung: {str(e)}")


def save_base64_as_png(base64_string: str, output_path: str):
    """
    Speichert einen Base64-codierten String als PNG-Datei. (zum testen)

    :param base64_string: Der Base64-codierte String des Bildes.
    :param output_path: Der Pfad, an dem das Bild gespeichert werden soll.
    """
    try:
        # Base64-String in Bytes umwandeln
        image_data = base64.b64decode(base64_string)

        # Das Bild als PNG speichern
        with open(output_path, "wb") as f:
            f.write(image_data)
        print(f"Bild erfolgreich gespeichert unter: {output_path}")
    except Exception as e:
        raise RuntimeError(f"Fehler beim Speichern des Base64-Bildes: {str(e)}")