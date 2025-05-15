
#ergebnis 25.5.2025, nur mal kurz probiert, es kommt nur schrott raus



import fitz  # PyMuPDF
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel
import torch
import re

def main():
    pdf_path = r"C:\temp\test_belege\Computer_Maus1_22_11_2024.pdf"

    processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
    model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()

    print("model initialized")

    # PDF mit PyMuPDF öffnen und erste Seite rendern
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=400)
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Task-Prompt für DocVQA (z.B. Rechnungsdatum abfragen)
    task_prompt = "<s_docvqa><s_question>Was steht auf der Seite?</s_question><s_answer>"
    decoder_input_ids = processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="pt").input_ids
    pixel_values = processor(image, return_tensors="pt").pixel_values

    outputs = model.generate(
        pixel_values.to(device),
        decoder_input_ids=decoder_input_ids.to(device),
        max_length=model.decoder.config.max_position_embeddings,
        pad_token_id=processor.tokenizer.pad_token_id,
        eos_token_id=processor.tokenizer.eos_token_id,
        use_cache=True,
        bad_words_ids=[[processor.tokenizer.unk_token_id]],
        return_dict_in_generate=True,
    )

    sequence = processor.batch_decode(outputs.sequences)[0]
    sequence = sequence.replace(processor.tokenizer.eos_token, "").replace(processor.tokenizer.pad_token, "")
    sequence = re.sub(r"<.*?>", "", sequence, count=1).strip()

    result = processor.token2json(sequence)
    print(result)

if __name__ == "__main__":
    main()
