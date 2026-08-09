from docling.document_converter import DocumentConverter
import sys

print("Testing Docling PDF extraction...")

try:
    # Initialize
    print("1. Initializing Docling...")
    converter = DocumentConverter()
    print("✅ Docling initialized!")
    
    # Test with your PDF
    pdf_path = "Vendor-Invoice-Template-Someka-Example-PDF-V1.pdf"
    print(f"2. Converting: {pdf_path}")
    
    result = converter.convert(pdf_path)
    print("✅ Conversion complete!")
    
    # Get document
    doc = result.document
    print(f"3. Document info:")
    print(f"   Pages: {len(doc.pages) if hasattr(doc, 'pages') else 'N/A'}")
    print(f"   Tables: {len(doc.tables) if hasattr(doc, 'tables') else 'N/A'}")
    
    # Get text
    if hasattr(doc, 'export_to_markdown'):
        text = doc.export_to_markdown()
        print(f"4. Extracted text length: {len(text)} chars")
        print(f"5. First 500 chars:")
        print(text[:500])
    else:
        print("⚠️  No text extraction method found")
        print(f"   Document type: {type(doc)}")
        print(f"   Available methods: {[m for m in dir(doc) if not m.startswith('_')]}")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("   Docling not properly installed")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()