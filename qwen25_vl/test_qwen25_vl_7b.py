#schrott geht nicht


import fitz  # PyMuPDF
from PIL import Image
from io import BytesIO
import base64
import subprocess

pdf_path = r"C:\temp\test_belege\Computer_Maus1_22_11_2024.pdf"

def pdf_page_to_base64_image(pdf_path, page_number=0, dpi=300):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number)
    pix = page.get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode()
    return img_b64

def call_qwen_ollama(base64_img, prompt_text):
    prompt = f"<image>{base64_img}</image>\n{prompt_text}"

    result = subprocess.run(
        ["ollama", "run", "ingu627/Qwen2.5-VL-7B-Instruct-Q5_K_M"],
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return result.stdout

if __name__ == "__main__":
    img_b64 = pdf_page_to_base64_image(pdf_path)
    prompt = "Bitte extrahiere Betrag, Datum und MwSt. aus der Rechnung."
    try:
        output = call_qwen_ollama(img_b64, prompt)
        print("Modell-Ausgabe:\n", output)
    except subprocess.CalledProcessError as e:
        print("Fehler beim Modellaufruf:")
        print(e.stderr)

