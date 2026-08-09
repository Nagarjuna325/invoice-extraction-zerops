print("Downloading LayoutLMv3 model...")
print("This will download ~500MB, may take 2-3 minutes...\n")

from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
import torch

print("Step 1: Downloading processor...")
processor = LayoutLMv3Processor.from_pretrained(
    "microsoft/layoutlmv3-base",
    apply_ocr=True
)
print("✅ Processor downloaded!\n")

print("Step 2: Downloading model...")
model = LayoutLMv3ForTokenClassification.from_pretrained(
    "microsoft/layoutlmv3-base"
)
print("✅ Model downloaded!\n")

print("Step 3: Testing model...")
print(f"Model type: {type(model)}")
print(f"Device: CPU")
print(f"Number of parameters: {sum(p.numel() for p in model.parameters()):,}")

print("\n✅ LayoutLMv3 model ready to use!")