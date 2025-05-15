

import fitz  # PyMuPDF
import base64
from io import BytesIO
from PIL import Image
import subprocess
import tempfile

def pdf_page_to_base64_image(pdf_path, page_number=0, max_size=(640, 640)):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number)
    pix = page.get_pixmap(dpi=150)  # DPI anpassen nach Bedarf
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Optional skalieren
    img.thumbnail(max_size)

    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_bytes = buffered.getvalue()
    base64_img = base64.b64encode(img_bytes).decode('utf-8')
    return base64_img

def test_ollama_model_with_pdf(pdf_path, prompt_text, model_name="ingu627/Qwen2.5-VL-7B-Instruct-Q5_K_M"):
    # 1. PDF-Seite in Base64 Bild konvertieren
    base64_img = pdf_page_to_base64_image(pdf_path)

    # 2. Prompt mit Bild bauen
    prompt = f"<image>{base64_img}</image>\n{prompt_text}"

    # 3. Prompt in temporäre Datei schreiben
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=True) as tmpfile:
        tmpfile.write(prompt)
        tmpfile.flush()

        # 4. Modellaufruf mit Ollama via subprocess
        try:
            result = subprocess.run(
                ["ollama", "run", model_name, tmpfile.name],
                capture_output=True,
                text=True,
                timeout=180
            )
            if result.returncode != 0:
                print(f"Fehler beim Modellaufruf:\n{result.stderr}")
            else:
                print("Modell-Ausgabe:\n", result.stdout)
        except subprocess.TimeoutExpired:
            print("Fehler: Modellaufruf hat zu lange gedauert (Timeout)")
        except Exception as e:
            print(f"Unbekannter Fehler beim Modellaufruf: {e}")

if __name__ == "__main__":
    pdf_path = r"C:\temp\test_belege\Computer_Maus1_22_11_2024.pdf"
    prompt_text = "Bitte extrahiere Betrag, Datum, MwSt aus diesem Beleg."
    test_ollama_model_with_pdf(pdf_path, prompt_text)
