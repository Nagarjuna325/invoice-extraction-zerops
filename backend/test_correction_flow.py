"""
Test Correction Endpoint & Template Learning Flow
Demonstrates how the system learns from user corrections
"""
import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000/api/v1"

print("="*80)
print("TESTING CORRECTION & TEMPLATE LEARNING FLOW")
print("="*80)

# Test connection first
try:
    response = requests.get("http://localhost:8000/")
    print(f"\n✅ Server is running: {response.json()}")
except Exception as e:
    print(f"\n❌ ERROR: Cannot connect to server!")
    print(f"   Make sure backend is running: python run.py")
    print(f"   Error: {e}")
    sys.exit(1)

# ============================================================================
# SCENARIO: Upload same vendor invoice twice, correct it, see improvement
# ============================================================================

print("\n" + "="*80)
print("SCENARIO: Learning from Corrections")
print("="*80)

try:
    # Step 1: Upload first invoice from Hankook
    print("\n[Step 1] Uploading Hankook invoice (first time)...")
    print("-"*80)

    with open("uploads/upload_20251226_213746_31ecc885/Invoice1.png", "rb") as f:
        files = {"file": ("Invoice1.png", f, "image/png")}
        data = {"ocr_engine": "triple_hybrid"}
        
        response = requests.post(f"{BASE_URL}/invoices/upload", files=files, data=data)
        response.raise_for_status()
        upload1 = response.json()
        
    print(f"✅ Upload ID: {upload1['upload_id']}")
    print(f"   Status: {upload1['status']}")

    # Wait for processing
    print("\n⏳ Waiting for processing (90 seconds)...")
    for i in range(9):
        time.sleep(10)
        print(f"   {(i+1)*10} seconds...")

    # Get results
    print("\n[Step 2] Getting extraction results...")
    print("-"*80)

    response = requests.get(f"{BASE_URL}/invoices/{upload1['upload_id']}")
    response.raise_for_status()
    result1 = response.json()

    print(f"✅ Extraction complete!")
    print(f"   Vendor: {result1.get('vendor_name')}")
    print(f"   Vendor ID: {result1.get('vendor_id')}")
    print(f"   Template exists: {result1.get('used_template')}")
    print(f"   Overall confidence: {result1.get('overall_confidence')}%")

    print("\n📊 Extracted Data:")
    for field, value in result1['extracted_data'].items():
        conf = result1['field_confidences'].get(field, 0)
        print(f"   {field}: {value} ({conf:.1f}%)")

    # Step 3: Submit correction
    print("\n[Step 3] User reviews and corrects extraction errors...")
    print("-"*80)

    corrected_data = {
        "vendor_name": "Hankook Tire America Corp",
        "invoice_number": "9146515234",
        "invoice_date": "2025-12-04",
        "total_amount": 158.48,
        "currency": "USD"
    }

    print("Corrected data:")
    for field, value in corrected_data.items():
        original = result1['extracted_data'].get(field)
        if str(original) != str(value):
            print(f"   {field}: {original} → {value} ✅ CORRECTED")
        else:
            print(f"   {field}: {value} (unchanged)")

    correction_request = {
        "upload_id": upload1['upload_id'],
        "corrected_data": corrected_data
    }

    response = requests.post(
        f"{BASE_URL}/invoices/correct",
        json=correction_request,
        headers={"Content-Type": "application/json"}
    )
    response.raise_for_status()
    correction_result = response.json()

    print(f"\n✅ Correction submitted!")
    print(f"   Success: {correction_result.get('success')}")
    print(f"   Template updated: {correction_result.get('template_updated')}")
    print(f"   Vendor ID: {correction_result.get('vendor_id')}")
    print(f"   Learned from: {correction_result.get('learned_from_invoices')} invoice(s)")

    # Step 4: Upload same invoice again
    print("\n[Step 4] Uploading another invoice from same vendor...")
    print("-"*80)

    with open("uploads/upload_20251226_213746_31ecc885/Invoice1.png", "rb") as f:
        files = {"file": ("Invoice1.png", f, "image/png")}
        data = {"ocr_engine": "triple_hybrid"}
        
        response = requests.post(f"{BASE_URL}/invoices/upload", files=files, data=data)
        response.raise_for_status()
        upload2 = response.json()

    print(f"✅ Upload ID: {upload2['upload_id']}")

    # Wait for processing
    print("\n⏳ Waiting for processing (90 seconds)...")
    for i in range(9):
        time.sleep(10)
        print(f"   {(i+1)*10} seconds...")

    # Get results
    print("\n[Step 5] Getting results (with template applied)...")
    print("-"*80)

    response = requests.get(f"{BASE_URL}/invoices/{upload2['upload_id']}")
    response.raise_for_status()
    result2 = response.json()

    print(f"✅ Extraction complete!")
    print(f"   Vendor: {result2.get('vendor_name')}")
    print(f"   Vendor ID: {result2.get('vendor_id')}")
    print(f"   Template applied: {result2.get('used_template')} {'✅' if result2.get('used_template') else '❌'}")
    if result2.get('template_match_confidence'):
        print(f"   Template confidence: {result2.get('template_match_confidence'):.1f}%")
    print(f"   Overall confidence: {result2.get('overall_confidence')}%")

    print("\n📊 Extracted Data (with template):")
    for field, value in result2['extracted_data'].items():
        conf = result2['field_confidences'].get(field, 0)
        print(f"   {field}: {value} ({conf:.1f}%)")

    # Step 6: Compare results
    print("\n" + "="*80)
    print("COMPARISON: Before vs After Template Learning")
    print("="*80)

    print(f"\n{'Field':<20} {'Before Conf':<15} {'After Conf':<15} {'Improvement'}")
    print("-"*80)

    for field in corrected_data.keys():
        before_conf = result1['field_confidences'].get(field, 0)
        after_conf = result2['field_confidences'].get(field, 0)
        improvement = after_conf - before_conf
        
        arrow = "📈" if improvement > 0 else "→"
        print(f"{field:<20} {before_conf:<15.1f} {after_conf:<15.1f} {arrow} +{improvement:.1f}%")

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    print(f"\n1st Invoice (No Template):")
    print(f"   Overall Confidence: {result1.get('overall_confidence')}%")
    print(f"   Template Applied: No ❌")

    print(f"\n2nd Invoice (With Template):")
    print(f"   Overall Confidence: {result2.get('overall_confidence')}%")
    print(f"   Template Applied: {'Yes ✅' if result2.get('used_template') else 'No ❌'}")
    conf_improvement = result2.get('overall_confidence', 0) - result1.get('overall_confidence', 0)
    print(f"   Confidence Improvement: +{conf_improvement:.1f}%")

    print("\n✅ Template Learning Test Complete!")
    if result2.get('used_template'):
        print("   🎉 The system successfully learned from your correction!")
        print("   🎉 Future invoices from this vendor will have higher accuracy!")
    else:
        print("   ⚠️  Template not applied. Check vendor recognition.")

    print("\n" + "="*80)

except requests.exceptions.RequestException as e:
    print(f"\n❌ HTTP Error: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"   Status: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
except FileNotFoundError as e:
    print(f"\n❌ File Error: {e}")
    print("   Make sure the test invoice file exists:")
    print("   uploads/upload_20251226_213746_31ecc885/Invoice1.png")
except Exception as e:
    print(f"\n❌ Unexpected Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("TEST COMPLETE!")
print("="*80)