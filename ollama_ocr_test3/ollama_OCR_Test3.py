
#based on https://github.com/imanoop7/Ollama-OCR

from ollama_ocr import OCRProcessor
import json
import os

input_path="c:\\temp\\test_belege\\"

# Initialize OCR processor
ocr = OCRProcessor(model_name='llama3.2-vision', max_workers=6)  # max workers for parallel processing

# Process multiple images
# Process multiple images with progress tracking
batch_results = ocr.process_batch(
    input_path=input_path,  # Directory or list of image paths
    format_type="key_value",
    recursive=False,  # Search subdirectories
    preprocess=True  # Enable image preprocessing
)
# Access results
for file_path, text in batch_results['results'].items():
    print(f"\nFile: {file_path}")
    print(f"Extracted Text: {text}")

# View statistics
print("\nProcessing Statistics:")
print(f"Total images: {batch_results['statistics']['total']}")
print(f"Successfully processed: {batch_results['statistics']['successful']}")
print(f"Failed: {batch_results['statistics']['failed']}")




with open(input_path+"\\results.json", 'w', encoding='utf-8') as json_file:
    json.dump(batch_results["results"], json_file, ensure_ascii=False, indent=4)