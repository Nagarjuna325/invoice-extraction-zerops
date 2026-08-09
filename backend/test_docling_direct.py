from docling.document_converter import DocumentConverter

print("Testing Docling PDF extraction...")

try:
    # Initialize
    print("1. Initializing Docling...")
    converter = DocumentConverter()
    print("✅ Docling initialized!")
    
    # Your PDF path
    pdf_path = r"C:\Users\nagar\Downloads\Vendor-Invoice-Template-Someka-Example-PDF-V1.pdf"
    print(f"2. Converting: {pdf_path}")
    
    # Convert
    result = converter.convert(pdf_path)
    print("✅ Conversion complete!")
    
    # Get document
    doc = result.document
    print(f"\n3. Document info:")
    print(f"   Type: {type(doc)}")
    if hasattr(doc, 'pages'):
        print(f"   Pages: {len(doc.pages)}")
    if hasattr(doc, 'tables'):
        print(f"   Tables: {len(doc.tables)}")
    
    # Get text
    print(f"\n4. Extracting text...")
    if hasattr(doc, 'export_to_markdown'):
        text = doc.export_to_markdown()
        print(f"   Text length: {len(text)} characters")
        print(f"\n5. Full extracted text:")
        print("="*80)
        print(text)
        print("="*80)
    elif hasattr(doc, 'export_to_text'):
        text = doc.export_to_text()
        print(f"   Text length: {len(text)} characters")
        print(f"\n5. Full extracted text:")
        print("="*80)
        print(text)
        print("="*80)
    else:
        print("   ⚠️  No text export method found")
        print(f"   Available methods: {[m for m in dir(doc) if not m.startswith('_')]}")
    
    # Check for key values
    print(f"\n6. Looking for key values...")
    text_lower = text.lower() if 'text' in locals() else ""
    
    if '824' in text_lower:
        print("   ✅ Found '824'")
    if 'total' in text_lower:
        print("   ✅ Found 'total'")
    if 'inv-2023-025' in text_lower:
        print("   ✅ Found invoice number")
    if 'global enterprises' in text_lower:
        print("   ✅ Found vendor name")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()