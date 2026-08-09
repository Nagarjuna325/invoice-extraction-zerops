from app.services.layoutlm_service import layoutlm_service

print("Testing LayoutLMv3 on invoice...")
print("=" * 60)

image_path = "uploads/upload_20251216_012328_dbc8454c/Screenshot 2025-11-18 234357.png"

try:
    extracted_data, confidence = layoutlm_service.extract_invoice(image_path)
    
    print("\n✅ LAYOUTLM EXTRACTION SUCCESSFUL!")
    print("=" * 60)
    print(f"Confidence: {confidence}%")
    print("=" * 60)
    print("\nExtracted Fields:")
    print("-" * 60)
    
    for field, value in extracted_data.items():
        print(f"{field:20s}: {value}")
    
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()