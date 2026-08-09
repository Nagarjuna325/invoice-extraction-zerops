"""
Test all document types: Images, PDFs, Excel, CSV
"""
from app.services.document_processor import document_processor
from app.services.triple_hybrid_service import triple_hybrid_service


def test_single_document(file_path):
    """Test extraction on any document type"""
    print(f"\n{'='*80}")
    print(f"Testing: {file_path}")
    print(f"{'='*80}")
    
    try:
        # Step 1: Process document (detect type and convert if needed)
        doc_type, processed_data = document_processor.process_document(file_path)
        
        print(f"Document type: {doc_type}")
        
        # Step 2: Extract based on type
        if doc_type == 'image':
            # Direct image extraction
            extracted_data, confidences, method = triple_hybrid_service.extract_invoice(processed_data)
            
        elif doc_type == 'pdf':
            # PDF converted to images
            print(f"PDF converted to {len(processed_data)} page(s)")
            
            # Extract from first page (for now)
            print("\nProcessing page 1...")
            extracted_data, confidences, method = triple_hybrid_service.extract_invoice(processed_data[0])
            
            # Cleanup temp files
            document_processor.cleanup_temp_files(processed_data)
            
        elif doc_type in ['excel', 'csv']:
            # Structured data already extracted
            extracted_data = processed_data
            confidences = processed_data.get('_confidences', {})
            method = f'{doc_type}_parsing'
            
            # Remove internal fields
            if '_confidences' in extracted_data:
                del extracted_data['_confidences']
        
        else:
            print(f"❌ Unsupported document type: {doc_type}")
            return
        
        # Display results
        print(f"\n✅ Extraction complete!")
        print(f"Method: {method}")
        print(f"Fields extracted: {len(extracted_data)}")
        print(f"\n{'-'*80}")
        print("EXTRACTED FIELDS:")
        print(f"{'-'*80}")
        
        for field, value in extracted_data.items():
            conf = confidences.get(field, 0)
            print(f"{field:20s}: {str(value):40s} ({conf:.1f}%)")
        
        print(f"{'='*80}")
        
        return extracted_data
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {}


def main():
    """Test all document types"""
    print("="*80)
    print("UNIVERSAL DOCUMENT EXTRACTION TEST")
    print("="*80)
    
    # Test files
    test_files = [
        # PDFs
        "uploads/Bookkeeping-Invoice-Template-Someka-Example-PDF-V1.pdf",
        "uploads/Vendor-Invoice-Template-Someka-Example-PDF-V1.pdf",
        
        # Excel
        "uploads/Vendor-Invoice-Template-Someka-Example-Excel-V1.xlsx",
        
        # CSV
        "uploads/Vendor-Invoice-Template-Someka-Example-Google-Sheets-V1 - Invoice.csv",
        
        # Image (for comparison)
        "uploads/upload_20251216_012328_dbc8454c/Screenshot 2025-11-18 234357.png",
    ]
    
    results = []
    
    for test_file in test_files:
        import os
        if os.path.exists(test_file):
            result = test_single_document(test_file)
            results.append({
                'file': test_file,
                'data': result
            })
        else:
            print(f"\n⚠️  File not found: {test_file}")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"\nTotal files tested: {len(results)}")
    
    for result in results:
        fields = len(result['data']) if result['data'] else 0
        print(f"\n📄 {result['file']}")
        print(f"   Fields extracted: {fields}")
        if result['data']:
            print(f"   Fields: {', '.join(result['data'].keys())}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()