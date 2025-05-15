
#ist nicht ocr frei; kurzer Test: geht nicht,.... also lasse iches


import torch
from transformers import LayoutLMv3Processor, LayoutLMv3ForQuestionAnswering
from pdf2image import convert_from_path
from PIL import Image
import pytesseract

# === PDF zu Bild konvertieren ===
pdf_path = r"C:\temp\test_belege\Computer_Maus1_22_11_2024.pdf"
images = convert_from_path(pdf_path, dpi=300)
image = images[0]  # Nur erste Seite

# === OCR-Text + Bbox mit pytesseract holen ===
ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

# === Tokens, Bounding Boxes, Text extrahieren ===
words, boxes = [], []
for i in range(len(ocr_data["text"])):
    if int(ocr_data["conf"][i]) > 60:  # nur zuverlässiger Text
        words.append(ocr_data["text"][i])
        (x, y, w, h) = (ocr_data["left"][i], ocr_data["top"][i], ocr_data["width"][i], ocr_data["height"][i])
        boxes.append([x, y, x + w, y + h])

# === Frage stellen ===
question = "Was ist das Rechnungsdatum?"

# === Modell & Processor laden ===
processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base", apply_ocr=False)
model = LayoutLMv3ForQuestionAnswering.from_pretrained("microsoft/layoutlmv3-base")

# === Eingabedaten vorbereiten ===
encoding = processor(
    image,
    question=question,
    words=words,
    boxes=boxes,
    return_tensors="pt",
    truncation=True,
    padding="max_length"
)

# === Modell ausführen ===
outputs = model(**encoding)
start = torch.argmax(outputs.start_logits)
end = torch.argmax(outputs.end_logits) + 1

answer = processor.tokenizer.decode(encoding.input_ids[0][start:end])
print("Antwort:", answer)
