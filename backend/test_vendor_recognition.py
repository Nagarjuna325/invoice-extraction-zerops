"""
Test automatic vendor recognition
Shows how vendor service extracts and normalizes vendor names from ML results
"""
from app.services.vendor_service import vendor_service
from app.services.triple_hybrid_service import triple_hybrid_service
from app.core.database import SessionLocal

print("="*80)
print("TESTING AUTOMATIC VENDOR RECOGNITION")
print("="*80)

# Test invoices
test_invoices = [
    "uploads/upload_20251226_213746_31ecc885/Invoice1.png",  # Hankook
    "uploads/upload_20251216_012328_dbc8454c/Screenshot 2025-11-18 234357.png",  # Belle Tire
]

db = SessionLocal()

for invoice_path in test_invoices:
    print(f"\n{'='*80}")
    print(f"Processing: {invoice_path}")
    print(f"{'='*80}")
    
    try:
        # Step 1: Extract with ML (automatic)
        print("\n[Step 1] Extracting with Triple Hybrid ML...")
        extracted_data, field_confidences, method = triple_hybrid_service.extract_invoice(invoice_path)
        
        print(f"✅ ML extracted {len(extracted_data)} fields")
        print(f"   Vendor from ML: '{extracted_data.get('vendor_name')}'")
        print(f"   Confidence: {field_confidences.get('vendor_name', 0):.1f}%")
        
        # Step 2: Process vendor (automatic)
        print("\n[Step 2] Processing vendor information...")
        vendor_info = vendor_service.extract_vendor_info(extracted_data, field_confidences)
        
        print(f"✅ Vendor info extracted:")
        print(f"   Original name: '{vendor_info['vendor_name']}'")
        print(f"   Normalized: '{vendor_info['vendor_name_normalized']}'")
        print(f"   Fingerprint: {vendor_info['vendor_fingerprint']}")
        print(f"   Confidence: {vendor_info['confidence']:.1f}%")
        
        # Step 3: Find or create vendor (automatic)
        print("\n[Step 3] Finding or creating vendor in database...")
        vendor = vendor_service.find_or_create_vendor(db, vendor_info)
        
        if vendor:
            print(f"✅ Vendor in database:")
            print(f"   ID: {vendor.id}")
            print(f"   Name: {vendor.vendor_name}")
            print(f"   Invoice count: {vendor.invoice_count}")
            print(f"   Has template: {vendor.has_template}")
            print(f"   Fingerprint: {vendor.vendor_fingerprint}")
        else:
            print("⚠️  Vendor not created (low confidence)")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

# Summary
print("\n" + "="*80)
print("VENDOR DATABASE SUMMARY")
print("="*80)

from app.models.vendor import Vendor
vendors = db.query(Vendor).all()

print(f"\nTotal vendors in database: {len(vendors)}")

for vendor in vendors:
    print(f"\n📊 {vendor.vendor_name}")
    print(f"   ID: {vendor.id}")
    print(f"   Normalized: {vendor.vendor_name_normalized}")
    print(f"   Fingerprint: {vendor.vendor_fingerprint}")
    print(f"   Invoices: {vendor.invoice_count}")
    print(f"   Has template: {vendor.has_template}")
    print(f"   Created: {vendor.created_at}")

db.close()

print("\n" + "="*80)
print("✅ VENDOR RECOGNITION TEST COMPLETE!")
print("="*80)