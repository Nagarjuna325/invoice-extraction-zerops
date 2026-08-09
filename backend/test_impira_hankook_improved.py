from transformers import pipeline
from PIL import Image

print("=" * 70)
print("TESTING IMPIRA WITH IMPROVED QUESTIONS")
print("=" * 70)

extractor = pipeline(
    "document-question-answering",
    model="impira/layoutlm-document-qa"
)

image_path = "uploads/upload_20251226_213746_31ecc885/Invoice1.png"
image = Image.open(image_path).convert("RGB")

print(f"\nImage: {image_path}\n")

# IMPROVED: More specific questions
questions = {
    "vendor_name": [
        "What is the vendor name?",
        "Who is the seller?",
        "What is the company name at the top?"
    ],
    "invoice_number": [
        "What is the invoice number?",
        "What is the invoice no?"
    ],
    "invoice_date": [
        "What is the invoice issue date?",
        "What is the invoice date?",
        "When was the invoice issued?"
    ],
    "total_amount": [
        "What is the invoice total?",
        "What is the balance due?",
        "What is the final payment amount?"
    ],
    "billing_customer": [
        "What is the billing address company name?",
        "Who is the bill to customer?"
    ]
}

print("Extracting with multiple question attempts...\n")
final_results = {}

for field, question_list in questions.items():
    best_answer = None
    best_confidence = 0.0
    
    print(f"Field: {field}")
    for question in question_list:
        try:
            result = extractor(image=image, question=question)
            if result and len(result) > 0:
                answer = result[0]['answer']
                confidence = result[0]['score']
                print(f"  Q: {question}")
                print(f"  A: {answer} ({confidence:.1%})")
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_answer = answer
        except Exception as e:
            print(f"  Q: {question} - Error: {e}")
    
    final_results[field] = (best_answer or "Not found", best_confidence)
    print(f"  ✅ BEST: {best_answer} ({best_confidence:.1%})\n")

print("=" * 70)
print("FINAL RESULTS (Best Answer from Multiple Questions):")
print("=" * 70)
for field, (value, conf) in final_results.items():
    print(f"{field:20s}: {value:30s} (confidence: {conf:.1%})")
print("=" * 70)