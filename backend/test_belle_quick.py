from app.services.triple_hybrid_service import triple_hybrid_service

print("QUICK TEST: Belle Tire Invoice\n")
image_path = "uploads/upload_20251216_012328_dbc8454c/Screenshot 2025-11-18 234357.png"

extracted_data, field_confidences, method = triple_hybrid_service.extract_invoice(image_path)

print("RESULTS:")
for field, value in extracted_data.items():
    conf = field_confidences.get(field, 0)
    print(f"{field:20s}: {str(value):30s} ({conf:.1f}%)")

print("\nEXPECTED:")
print("vendor_name  : BELLE TIRE RECEIPT")
print("invoice_number: 45752969")
print("invoice_date : 2025-05-12")
print("total_amount : 0.0")