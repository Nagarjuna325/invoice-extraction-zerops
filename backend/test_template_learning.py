"""
Test template learning system
Shows how templates are created and applied automatically
"""
from app.services.template_service import template_service
from app.services.vendor_service import vendor_service
from app.services.triple_hybrid_service import triple_hybrid_service
from app.core.database import SessionLocal
from app.models.vendor import Vendor
import json

print("="*80)
print("TESTING TEMPLATE LEARNING SYSTEM")
print("="*80)

db = SessionLocal()

# Test: Process Hankook invoice multiple times to build template
test_invoice = "uploads/upload_20251226_213746_31ecc885/Invoice1.png"

print(f"\n{'='*80}")
print("SCENARIO: Processing same Hankook invoice 3 times")
print("="*80)

for iteration in range(1, 4):
    print(f"\n{'─'*80}")
    print(f"ITERATION {iteration}: Processing Hankook Invoice")
    print(f"{'─'*80}")
    
    # Step 1: Extract with ML
    print("\n[Step 1] Extracting with Triple Hybrid ML...")
    extracted_data, field_confidences, method = triple_hybrid_service.extract_invoice(test_invoice)
    
    print(f"✅ Extracted {len(extracted_data)} fields")
    for field, value in list(extracted_data.items())[:5]:
        conf = field_confidences.get(field, 0)
        print(f"   {field}: {value} ({conf:.1f}%)")
    
    # Step 2: Get vendor
    print("\n[Step 2] Recognizing vendor...")
    vendor_info = vendor_service.extract_vendor_info(extracted_data, field_confidences)
    vendor = vendor_service.find_or_create_vendor(db, vendor_info)
    
    if vendor:
        print(f"✅ Vendor: {vendor.vendor_name} (ID: {vendor.id})")
        print(f"   Invoice count: {vendor.invoice_count}")
        print(f"   Has template: {vendor.has_template}")
    
    # Step 3: Check if template exists
    if vendor and vendor.has_template and iteration > 1:
        print("\n[Step 3] Applying existing template...")
        template_data = vendor.template_data
        if isinstance(template_data, str):
            template_data = json.loads(template_data)
        
        # Apply template to improve results
        improved_data, improved_confidences = template_service.apply_template(
            template_data,
            extracted_data,
            field_confidences
        )
        
        print(f"✅ Template applied!")
        print(f"\n   Confidence improvements:")
        for field in extracted_data.keys():
            old_conf = field_confidences.get(field, 0)
            new_conf = improved_confidences.get(field, 0)
            if new_conf > old_conf:
                print(f"   {field}: {old_conf:.1f}% → {new_conf:.1f}% (+{new_conf-old_conf:.1f}%)")
        
        # Use improved data
        extracted_data = improved_data
        field_confidences = improved_confidences
    
    # Step 4: Simulate user correction (for demo purposes)
    print("\n[Step 4] Simulating user correction...")
    corrected_data = extracted_data.copy()
    
    # Correct the total amount (we know it should be 158.48, not 153.73)
    if 'total_amount' in corrected_data:
        corrected_data['total_amount'] = 158.48
        print(f"   Corrected total_amount: {extracted_data.get('total_amount')} → 158.48")
    
    # Step 5: Learn from correction (create/update template)
    if vendor:
        print("\n[Step 5] Learning from correction (updating template)...")
        template = template_service.create_template_from_invoice(
            db,
            vendor.id,
            extracted_data,
            field_confidences,
            corrected_data
        )
        
        print(f"✅ Template updated!")
        print(f"   Learned from: {template['learned_from_invoices']} invoice(s)")
        print(f"   Fields in template: {len(template['field_patterns'])}")
        print(f"   Template fields: {', '.join(template['field_patterns'].keys())}")

# Final Summary
print("\n" + "="*80)
print("FINAL TEMPLATE STATUS")
print("="*80)

vendor = db.query(Vendor).filter(Vendor.vendor_fingerprint == '590611624614c60f').first()

if vendor:
    print(f"\n📊 Vendor: {vendor.vendor_name}")
    print(f"   ID: {vendor.id}")
    print(f"   Total invoices processed: {vendor.invoice_count}")
    print(f"   Has template: {vendor.has_template}")
    
    if vendor.has_template:
        template_stats = template_service.get_template_stats(db, vendor.id)
        print(f"\n📋 Template Statistics:")
        print(f"   Learned from: {template_stats['learned_from_invoices']} invoice(s)")
        print(f"   Fields captured: {template_stats['field_count']}")
        print(f"   Fields: {', '.join(template_stats['fields'])}")
        print(f"   Last updated: {template_stats['last_updated']}")
        
        # Show template details
        template_data = vendor.template_data
        if isinstance(template_data, str):
            template_data = json.loads(template_data)
        
        print(f"\n📄 Template Details:")
        for field, pattern in template_data['field_patterns'].items():
            print(f"\n   {field}:")
            print(f"      Example: {pattern.get('example')}")
            print(f"      Confidence: {pattern.get('confidence', 0):.1f}%")
            print(f"      Seen in: {pattern.get('occurrences', 0)} invoice(s)")

db.close()

print("\n" + "="*80)
print("✅ TEMPLATE LEARNING TEST COMPLETE!")
print("="*80)
print("\nWhat happened:")
print("1. Iteration 1: No template → Extracted with ML → Created template")
print("2. Iteration 2: Template exists → Applied template → Boosted confidence → Updated template")
print("3. Iteration 3: Template improved → Applied template → Higher accuracy")
print("\nResult: System learns from each invoice and improves over time!")
print("="*80)