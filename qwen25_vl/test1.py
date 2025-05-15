
# 25.5.2025 mit perplexity erstellt, funktioniert
    # v2: nun lm studio da ollama nicht gut funktionert (unstabil)
    #


import os
import fitz  # PyMuPDF
import lmstudio as lms

# Optional: Wenn dein Server nicht auf localhost:1234 läuft, sondern z.B. auf 10.0.0.20:1233:
lms.configure_default_client("10.0.0.20:1233")

MODEL_NAME = "lmstudio-community/qwen2.5-vl-7b-instruct"

def pdf_page_to_image(pdf_path, page_number=0, image_path="temp_page.png"):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF nicht gefunden: {pdf_path}")
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number)
    pix = page.get_pixmap(dpi=200)
    pix.save(image_path)
    return image_path

def call_lmstudio(image_path, prompt_text):
    model = lms.llm(MODEL_NAME)
    chat = lms.Chat()
    image_handle = lms.prepare_image(image_path)
    chat.add_user_message(prompt_text, images=[image_handle])
    try:
        response = model.respond(chat)
        return response
    except Exception as e:
        print("Fehler beim Modellaufruf:", str(e))
        return None

def test_file():
    pdf_path = r"C:\temp\test_belege\Computer_Maus1_22_11_2024.pdf"
    image_path = "temp_page.png"
    try:
        image_path = pdf_page_to_image(pdf_path, 0, image_path)
        prompt_text = "Bitte extrahiere aus dem Bild Betrag, Datum, MwSt. und Rechnungsnummer."
        response = call_lmstudio(image_path, prompt_text)
        print("Antwort vom Modell:")
        print(response)
    except Exception as err:
        print("Fehler:", err)
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

if __name__ == "__main__":
    test_file()
