

import os
import fitz  # PyMuPDF
import requests
import base64
import pytesseract
from pdf2image import convert_from_path

API_URL = "http://10.0.0.20:1233/v1/chat/completions"
MODEL_NAME = "lmstudio-community/qwen2.5-vl-7b-instruct"

def pdf_page_to_base64(pdf_path, page_number=0):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number)
    pix = page.get_pixmap(dpi=300)
    img_bytes = pix.tobytes("png")
    base64_img = base64.b64encode(img_bytes).decode()
    return base64_img

def ask_pdf(pdf_path, prompt, page_number=0):
    base64_img = pdf_page_to_base64(pdf_path, page_number)
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_img}"
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }
    ]
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 1024,
        "stream": False
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(API_URL, json=payload, headers=headers, timeout=120)
    if response.status_code == 200:
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            return data
    else:
        raise RuntimeError(f"Fehler: {response.status_code} - {response.text}")

def ask_pdf_ocr(pdf_path, page_number=0, dpi=300, lang="deu"):
    """
    Extrahiert reinen Text aus einer PDF-Seite per Tesseract OCR.
    """
    # PDF-Seite als Bild (PIL) mit pdf2image
    pages = convert_from_path(pdf_path, dpi=dpi)
    if page_number >= len(pages):
        raise ValueError(f"PDF hat nur {len(pages)} Seiten, aber Seite {page_number} wurde angefragt.")
    page_img = pages[page_number]
    # OCR mit Tesseract
    text = pytesseract.image_to_string(page_img, lang=lang)
    return text

if __name__ == "__main__":
    pdf_file = r"C:\temp\test_belege\Computer_Maus1_22_11_2024.pdf"
    prompt = "Bitte extrahiere aus dem Bild Betrag, Datum, MwSt. und Rechnungsnummer."

    print("--- LLM-Ergebnis ---")
    try:
        antwort = ask_pdf(pdf_file, prompt)
        print(antwort)
    except Exception as e:
        print("Fehler LLM:", e)

    print("\n--- OCR-Text (Tesseract) ---")
    try:
        ocr_text = ask_pdf_ocr(pdf_file, page_number=0, dpi=300, lang="deu")
        print(ocr_text)
    except Exception as e:
        print("Fehler OCR:", e)
