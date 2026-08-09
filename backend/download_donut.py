print("Downloading Donut model...")
print("This is a ~500MB download, will take 2-3 minutes...\n")

from transformers import DonutProcessor, VisionEncoderDecoderModel
import torch

print("Step 1: Downloading processor...")
processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-cord-v2")
print("✅ Processor downloaded!\n")

print("Step 2: Downloading model...")
model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-cord-v2")
print("✅ Model downloaded!\n")

print("Step 3: Testing model...")
# Quick test
print(f"Model type: {type(model)}")
print(f"Device: CPU")
print("\n✅ Donut model ready to use!")