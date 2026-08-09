"""
Test script for Quadruple Hybrid system
Run this to verify Phase 1 is working correctly
"""

import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.quadruple_hybrid_service import quadruple_hybrid_service
import json

def test_quadruple_hybrid():
    """Test the quadruple hybrid system"""
    
    print("="*80)
    print("TESTING QUADRUPLE HYBRID SYSTEM")
    print("="*80)
    
    # Test file path
    test_pdf = "Vendor-Invoice-Template-Someka-Example-PDF-V1.pdf"
    test_image = "uploads/upload_20251231_011941_6fd51419/Vendor-Invoice-Template-Someka-Example-PDF-V1.pdf_page_1.png"
    
    if not os.path.exists(test_image):
        print(f"❌ Test image not found: {test_image}")
        print("Please upload an invoice first to create the image")
        return
    
    print(f"\nTest file: {test_pdf}")
    print(f"Test image: {test_image}")
    
    # Run extraction
    print("\n" + "="*80)
    print("RUNNING EXTRACTION...")
    print("="*80)
    
    result = quadruple_hybrid_service.extract_invoice(
        image_path=test_image,
        pdf_path=test_pdf if os.path.exists(test_pdf) else None
    )
    
    # Display results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    
    print(f"\nExtracted Data:")
    print(json.dumps(result['extracted_data'], indent=2))
    
    print(f"\nField Confidences:")
    print(json.dumps(result['field_confidences'], indent=2))
    
    print(f"\nModels Used: {result['models_used']}")
    print(f"Overall Confidence: {result['overall_confidence']:.1f}%")
    print(f"Processing Time: {result['processing_time_ms']}ms")
    
    print(f"\nNeeds Review: {len(result['needs_review'])} fields")
    for item in result['needs_review']:
        print(f"  - {item['field']}: {item['reason']}")
    
    print(f"\nLine Items: {len(result['line_items'])}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    test_quadruple_hybrid()