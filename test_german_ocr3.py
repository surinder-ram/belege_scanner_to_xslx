import os
import re
import json
import torch
import pandas as pd
import fitz  # PyMuPDF
from PIL import Image
import io

from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

# ===================== CONFIG =====================
BASE_FOLDER = r"C:\Users\surin\Meine Ablage (surinder.ram@gmail.com)\Firma\Belege\2025"

# PFADE
LOCAL_MODEL_PATH = r"C:\temp\german-ocr-3"
BASE_MODEL_ID = "Qwen/Qwen2-VL-2B-Instruct"  # Für den Processor (online)

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"--- System nutzt: {device} ---")


# ===================== MODEL LOAD =====================

def get_model_and_processor():
    print(f"Lade Processor von {BASE_MODEL_ID}...")
    processor = AutoProcessor.from_pretrained(BASE_MODEL_ID)

    print(f"Lade Modell-Gewichte lokal von {LOCAL_MODEL_PATH}...")
    # Wir laden das Modell von deinem C:\temp Ordner
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        LOCAL_MODEL_PATH,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        trust_remote_code=True,
        local_files_only=True  # Erzwingt Nutzung der lokalen Dateien
    )
    return model, processor


try:
    model, processor = get_model_and_processor()
    print("✅ System bereit!")
except Exception as e:
    print(f"❌ Fehler beim Laden: {e}")
    exit()


# ===================== HELPERS =====================

def clean_to_float(val):
    if val is None or val == "" or str(val).lower() == "n/a":
        return 0.0
    s = str(val).replace("EUR", "").replace("€", "").replace(" ", "").strip()
    if "," in s and "." in s:
        if s.find(".") < s.find(","):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        match = re.search(r"[-+]?\d*\.\d+|\d+", s)
        return float(match.group(0)) if match else 0.0
    except:
        return 0.0


def process_pdf(path):
    doc = fitz.open(path)
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0))
    image = Image.open(io.BytesIO(pix.tobytes("png")))
    doc.close()

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text",
                 "text": "Extrahiere Rechnungsdaten als JSON: Lieferant, Datum, Bezeichnung, MwSt_Satz, MwSt_Betrag, Gesamt, Netto. Antworte NUR mit JSON."},
            ],
        }
    ]

    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, _ = process_vision_info(messages)

    inputs = processor(
        text=[text],
        images=image_inputs,
        padding=True,
        return_tensors="pt",
    ).to(device)

    with torch.no_grad():
        output_ids = model.generate(**inputs, max_new_tokens=512)
        generated_ids = [out[len(ins):] for ins, out in zip(inputs.input_ids, output_ids)]
        output_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

    print(f"\nKI-Output:\n{output_text}")
    match = re.search(r"\{.*\}", output_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            return None
    return None


# ===================== MAIN =====================

def main():
    if not os.path.exists(BASE_FOLDER):
        print(f"Pfad existiert nicht: {BASE_FOLDER}")
        return

    all_data = []
    for root, _, files in os.walk(BASE_FOLDER):
        pdfs = [f for f in files if f.lower().endswith(".pdf") and not f.startswith("_")]
        if not pdfs: continue

        for f in pdfs:
            print(f"📄 Analyse: {f}...")
            try:
                data = process_pdf(os.path.join(root, f))
                if data:
                    res = {
                        "Datei": f,
                        "Lieferant": data.get("Lieferant"),
                        "Brutto": clean_to_float(data.get("Gesamt") or data.get("total")),
                        "Datum": data.get("Datum")
                    }
                    all_data.append(res)
                    print(f"   ✅ Erfolg: {res['Brutto']}€")
            except Exception as e:
                print(f"   ❌ Fehler: {e}")

    if all_data:
        df = pd.DataFrame(all_data)
        out_path = os.path.join(BASE_FOLDER, "OCR_Ergebnisse_Lokal.xlsx")
        df.to_excel(out_path, index=False)
        print(f"\n💾 Gespeichert unter: {out_path}")


if __name__ == "__main__":
    main()