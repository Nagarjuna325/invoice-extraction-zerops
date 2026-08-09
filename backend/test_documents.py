"""
Test invoice extraction on PDF, Excel, and CSV files
"""
import os
from app.services.triple_hybrid_service import triple_hybrid_service
from pdf2image import convert_from_path
from PIL import Image
import pandas as pd


def test_pdf_invoice(pdf_path):
    """Test extraction on PDF (convert to images first)"""
    print(f"\n{'='*80}")
    print(f"Testing PDF: {pdf_path}")
    print(f"{'='*80}")
    
    try:
        # Convert PDF to images
        print("Converting PDF to images...")
        pages = convert_from_path(pdf_path, dpi=200)
        
        print(f"PDF has {len(pages)} page(s)")
        
        # Test first page
        print("\nProcessing page 1...")
        
        # Save temporary image
        temp_image = "temp_pdf_page.png"
        pages[0].save(temp_image)
        
        # Extract
        extracted_data, field_confidences, method = triple_hybrid_service.extract_invoice(temp_image)
        
        # Display results
        print(f"\n✅ Extraction complete")
        print(f"Fields extracted: {len(extracted_data)}")
        print(f"\n{'-'*80}")
        print("EXTRACTED FIELDS:")
        print(f"{'-'*80}")
        
        for field, value in extracted_data.items():
            conf = field_confidences.get(field, 0)
            print(f"{field:20s}: {str(value):40s} ({conf:.1f}%)")
        
        # Cleanup
        os.remove(temp_image)
        
        return extracted_data
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {}


def test_excel_invoice(excel_path):
    """Test Excel invoice (check if it's a scanned image or data)"""
    print(f"\n{'='*80}")
    print(f"Testing Excel: {excel_path}")
    print(f"{'='*80}")
    
    try:
        # Try to read as data
        df = pd.read_excel(excel_path)
        
        print(f"Excel has {len(df)} rows, {len(df.columns)} columns")
        print("\nFirst few rows:")
        print(df.head())
        
        # Check if this looks like invoice data
        print("\n⚠️  Excel file contains structured data")
        print("This requires different extraction logic than images!")
        print("Would need to parse Excel cells directly.")
        
        return {}
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return {}


def test_csv_invoice(csv_path):
    """Test CSV invoice"""
    print(f"\n{'='*80}")
    print(f"Testing CSV: {csv_path}")
    print(f"{'='*80}")
    
    try:
        df = pd.read_csv(csv_path)
        
        print(f"CSV has {len(df)} rows, {len(df.columns)} columns")
        print("\nData:")
        print(df.to_string())
        
        print("\n⚠️  CSV file contains structured data")
        print("This requires parsing CSV cells, not image extraction!")
        
        return {}
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return {}


def main():
    """Test all document types"""
    print("="*80)
    print("TESTING PDF/EXCEL/CSV INVOICES")
    print("="*80)
    
    # Find files in uploads directory
    uploads_dir = "uploads"
    
    pdf_files = [f for f in os.listdir(uploads_dir) if f.endswith('.pdf')]
    excel_files = [f for f in os.listdir(uploads_dir) if f.endswith(('.xlsx', '.xls'))]
    csv_files = [f for f in os.listdir(uploads_dir) if f.endswith('.csv')]
    
    print(f"\nFound:")
    print(f"  PDFs: {len(pdf_files)}")
    print(f"  Excel: {len(excel_files)}")
    print(f"  CSV: {len(csv_files)}")
    
    # Test PDFs
    for pdf_file in pdf_files:
        pdf_path = os.path.join(uploads_dir, pdf_file)
        test_pdf_invoice(pdf_path)
    
    # Test Excel
    for excel_file in excel_files:
        excel_path = os.path.join(uploads_dir, excel_file)
        test_excel_invoice(excel_path)
    
    # Test CSV
    for csv_file in csv_files:
        csv_path = os.path.join(uploads_dir, csv_file)
        test_csv_invoice(csv_path)


if __name__ == "__main__":
    main()