print("Testing Donut on sample invoice...")

from transformers import DonutProcessor, VisionEncoderDecoderModel
from PIL import Image
import torch

# Load model and processor
print("Loading Donut model...")
processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-cord-v2")
model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-cord-v2")

print("✅ Model loaded!\n")

# Test on Belle Tire invoice
image_path = "uploads/upload_20251216_012328_dbc8454c/Screenshot 2025-11-18 234357.png"

try:
    print(f"Loading image: {image_path}")
    image = Image.open(image_path).convert("RGB")
    print(f"✅ Image loaded: {image.size}\n")
    
    print("Processing with Donut...")
    # Prepare inputs
    pixel_values = processor(image, return_tensors="pt").pixel_values
    
    # Generate predictions
    task_prompt = "<s_cord-v2>"
    decoder_input_ids = processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="pt").input_ids
    
    outputs = model.generate(
        pixel_values,
        decoder_input_ids=decoder_input_ids,
        max_length=model.decoder.config.max_position_embeddings,
        early_stopping=True,
        pad_token_id=processor.tokenizer.pad_token_id,
        eos_token_id=processor.tokenizer.eos_token_id,
        use_cache=True,
        num_beams=1,
        bad_words_ids=[[processor.tokenizer.unk_token_id]],
        return_dict_in_generate=True,
    )
    
    # Decode output
    sequence = processor.batch_decode(outputs.sequences)[0]
    sequence = sequence.replace(processor.tokenizer.eos_token, "").replace(processor.tokenizer.pad_token, "")
    sequence = sequence.replace(task_prompt, "")
    
    print("✅ Processing complete!\n")
    print("=" * 50)
    print("DONUT EXTRACTION RESULT:")
    print("=" * 50)
    print(sequence)
    print("=" * 50)
    
except FileNotFoundError:
    print(f"❌ Image not found at: {image_path}")
    print("Please provide path to an invoice image to test!")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ Donut test complete!")