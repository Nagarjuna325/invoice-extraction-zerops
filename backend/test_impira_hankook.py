from transformers import pipeline
from PIL import Image

print("=" * 70)
print("TESTING IMPIRA ON HANKOOK TIRE INVOICE")
print("=" * 70)

# Load the invoice-trained model
extractor = pipeline(
    "document-question-answering",
    model="impira/layoutlm-document-qa"
)

# Load Hankook invoice
image_path = "uploads/upload_20251226_213746_31ecc885/Invoice1.png"
image = Image.open(image_path).convert("RGB")

print(f"\nImage: {image_path}")
print(f"Size: {image.size}\n")

# Ask questions (NO REGEX!)
questions = {
    "vendor_name": "What is the vendor name?",
    "invoice_number": "What is the invoice number?",
    "invoice_date": "What is the invoice date?",
    "total_amount": "What is the total amount?",
    "customer_name": "What is the customer name?"
}

print("Extracting fields using Q&A...\n")
results = {}

for field, question in questions.items():
    try:
        print(f"Q: {question}")
        result = extractor(image=image, question=question)
        answer = result[0]['answer'] if result else "Not found"
        confidence = result[0]['score'] if result else 0.0
        results[field] = answer
        print(f"A: {answer} (confidence: {confidence:.2%})\n")
    except Exception as e:
        print(f"A: Error - {e}\n")
        results[field] = "Error"

print("=" * 70)
print("EXTRACTION RESULTS:")
print("=" * 70)
for field, value in results.items():
    print(f"{field:20s}: {value}")
print("=" * 70)

# Compare with expected
print("\nEXPECTED vs ACTUAL:")
print("-" * 70)
expected = {
    "vendor_name": "Hankook Tire America Corp. (or BELLE TIRE from billing)",
    "invoice_number": "9146515234",
    "invoice_date": "2025-12-04",
    "total_amount": "$158.48",
    "customer_name": "BELLE TIRE"
}

correct = 0
total = 0
for field, expected_val in expected.items():
    actual_val = results.get(field, "Not found")
    total += 1
    # Simple match check
    if expected_val.replace(" ", "").lower() in actual_val.replace(" ", "").lower() or \
       actual_val.replace(" ", "").lower() in expected_val.replace(" ", "").lower():
        correct += 1
        status = "✅"
    else:
        status = "❌"
    print(f"{status} {field:20s}: Expected '{expected_val}' | Got '{actual_val}'")

print("-" * 70)
print(f"Accuracy: {correct}/{total} = {correct/total*100:.1f}%")
print("=" * 70)