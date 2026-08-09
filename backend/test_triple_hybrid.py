import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

print("=" * 70)
print("TESTING TRIPLE HYBRID (Impira + LayoutLM + Donut)")
print("=" * 70)

try:
    print("\n[1/4] Importing service...")
    from app.services.triple_hybrid_service import triple_hybrid_service
    print("✅ Import successful")
    
    print("\n[2/4] Loading image path...")
    image_path = "uploads/upload_20251226_213746_31ecc885/Invoice1.png"
    
    import os
    if not os.path.exists(image_path):
        print(f"❌ ERROR: Image not found at {image_path}")
        print(f"Current directory: {os.getcwd()}")
        print("\nAvailable uploads:")
        if os.path.exists("uploads"):
            for item in os.listdir("uploads"):
                print(f"  - uploads/{item}")
        sys.exit(1)
    
    print(f"✅ Image found: {image_path}")
    
    print("\n[3/4] Extracting with triple hybrid...")
    print("This will take 30-60 seconds (running 3 models)...\n")
    
    extracted_data, field_confidences, method = triple_hybrid_service.extract_invoice(image_path)
    
    print("\n[4/4] ✅ EXTRACTION COMPLETE!")
    print("=" * 70)
    print(f"Method: {method}")
    print(f"Fields extracted: {len(extracted_data)}")
    print("=" * 70)
    
    if extracted_data:
        print("\nEXTRACTED FIELDS:")
        print("-" * 70)
        for field, value in extracted_data.items():
            conf = field_confidences.get(field, 0)
            print(f"{field:20s}: {str(value):30s} ({conf:.1f}%)")
        print("=" * 70)
    else:
        print("\n⚠️  No fields extracted!")
    
    print("\nEXPECTED:")
    print("-" * 70)
    print("vendor_name         : Hankook Tire America Corp.")
    print("invoice_number      : 9146515234")
    print("invoice_date        : 2025-12-04")
    print("total_amount        : 158.48")
    print("=" * 70)
    
except ImportError as e:
    print(f"\n❌ IMPORT ERROR: {e}")
    print("\nMake sure all service files exist:")
    print("  - app/services/triple_hybrid_service.py")
    print("  - app/services/donut_service.py")
    print("  - app/services/layoutlm_service.py")
    import traceback
    traceback.print_exc()
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()