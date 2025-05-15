
# 25.5.2025 mit perplexity erstellt, funktioniert


import base64
import fitz  # PyMuPDF
import requests
import os

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "ingu627/Qwen2.5-VL-7B-Instruct-Q5_K_M"

def pdf_page_to_base64(pdf_path, page_number=0):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF nicht gefunden: {pdf_path}")
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number)
    pix = page.get_pixmap(dpi=300)
    img_bytes = pix.tobytes("png")
    base64_img = base64.b64encode(img_bytes).decode()
    return base64_img

def call_ollama_vision(base64_img, prompt_text):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt_text,
        "images": [base64_img],
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        if "response" in data:
            return data["response"]
        else:
            print("Unerwartete Antwort:", data)
            return None
    except Exception as e:
        print("Fehler beim Modellaufruf:", str(e))
        return None

if __name__ == "__main__":
    pdf_path = r"C:\temp\test_belege\Computer_Maus1_22_11_2024.pdf"
    try:
        base64_img = pdf_page_to_base64(pdf_path, 0)
        prompt_text = "Bitte extrahiere aus dem Bild Betrag, Datum, MwSt. und Rechnungsnummer."
        response = call_ollama_vision(base64_img, prompt_text)
        print("Antwort vom Modell:")
        print(response)
    except Exception as err:
        print("Fehler:", err)
