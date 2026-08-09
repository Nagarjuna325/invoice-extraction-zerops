"""
Comprehensive invoice testing script
Tests triple hybrid on multiple invoices and generates report
"""
import os
import glob
from app.services.triple_hybrid_service import triple_hybrid_service
from PIL import Image
import json
from datetime import datetime


class InvoiceTester:
    """Test invoice extraction on multiple files"""
    
    def __init__(self):
        self.results = []
    
    def find_test_invoices(self):
        """Find all invoice images in uploads directory"""
        invoice_files = []
        
        # Search in uploads directory
        upload_dirs = glob.glob("uploads/upload_*/")
        
        for upload_dir in upload_dirs:
            # Find image files
            images = glob.glob(f"{upload_dir}*.png") + glob.glob(f"{upload_dir}*.jpg")
            invoice_files.extend(images)
        
        return invoice_files
    
    def test_invoice(self, image_path, expected_data=None):
        """Test extraction on single invoice"""
        print(f"\n{'='*80}")
        print(f"Testing: {image_path}")
        print(f"{'='*80}")
        
        try:
            # Get image info
            image = Image.open(image_path)
            print(f"Image size: {image.size}")
            
            # Extract
            print("\nExtracting...")
            start_time = datetime.now()
            extracted_data, field_confidences, method = triple_hybrid_service.extract_invoice(image_path)
            end_time = datetime.now()
            
            processing_time = (end_time - start_time).total_seconds()
            
            # Calculate stats
            avg_confidence = sum(field_confidences.values()) / len(field_confidences) if field_confidences else 0
            
            # Display results
            print(f"\n✅ Extraction complete in {processing_time:.1f} seconds")
            print(f"Method: {method}")
            print(f"Fields extracted: {len(extracted_data)}")
            print(f"Average confidence: {avg_confidence:.1f}%")
            print(f"\n{'-'*80}")
            print("EXTRACTED FIELDS:")
            print(f"{'-'*80}")
            
            for field, value in extracted_data.items():
                conf = field_confidences.get(field, 0)
                print(f"{field:20s}: {str(value):40s} ({conf:.1f}%)")
            
            # Calculate accuracy if expected data provided
            accuracy = None
            if expected_data:
                correct = 0
                total = len(expected_data)
                
                print(f"\n{'-'*80}")
                print("VALIDATION:")
                print(f"{'-'*80}")
                
                for field, expected_value in expected_data.items():
                    extracted_value = extracted_data.get(field, "NOT_EXTRACTED")
                    
                    # Simple match check
                    match = self._values_match(str(extracted_value), str(expected_value))
                    
                    if match:
                        correct += 1
                        status = "✅"
                    else:
                        status = "❌"
                    
                    print(f"{status} {field:20s}: Expected '{expected_value}' | Got '{extracted_value}'")
                
                accuracy = (correct / total * 100) if total > 0 else 0
                print(f"\n📊 Accuracy: {correct}/{total} = {accuracy:.1f}%")
            
            # Store result
            result = {
                'file': image_path,
                'fields_extracted': len(extracted_data),
                'avg_confidence': avg_confidence,
                'processing_time': processing_time,
                'accuracy': accuracy,
                'extracted_data': extracted_data,
                'confidences': field_confidences
            }
            
            self.results.append(result)
            
            return result
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            
            result = {
                'file': image_path,
                'error': str(e),
                'success': False
            }
            self.results.append(result)
            return result
    
    def _values_match(self, val1, val2):
        """Check if two values match (fuzzy)"""
        str1 = str(val1).lower().strip().replace(" ", "")
        str2 = str(val2).lower().strip().replace(" ", "")
        
        if str1 == str2:
            return True
        
        # Partial match for longer strings
        if len(str1) > 5 and len(str2) > 5:
            if str1 in str2 or str2 in str1:
                return True
        
        return False
    
    def generate_report(self):
        """Generate summary report"""
        print("\n" + "="*80)
        print("COMPREHENSIVE TEST REPORT")
        print("="*80)
        
        successful_tests = [r for r in self.results if 'error' not in r]
        failed_tests = [r for r in self.results if 'error' in r]
        
        print(f"\nTotal tests: {len(self.results)}")
        print(f"Successful: {len(successful_tests)}")
        print(f"Failed: {len(failed_tests)}")
        
        if successful_tests:
            print(f"\n{'-'*80}")
            print("SUCCESSFUL EXTRACTIONS:")
            print(f"{'-'*80}")
            
            for result in successful_tests:
                print(f"\n📄 {result['file']}")
                print(f"   Fields: {result['fields_extracted']}")
                print(f"   Confidence: {result['avg_confidence']:.1f}%")
                print(f"   Time: {result['processing_time']:.1f}s")
                if result['accuracy']:
                    print(f"   Accuracy: {result['accuracy']:.1f}%")
            
            # Calculate averages
            avg_fields = sum(r['fields_extracted'] for r in successful_tests) / len(successful_tests)
            avg_conf = sum(r['avg_confidence'] for r in successful_tests) / len(successful_tests)
            avg_time = sum(r['processing_time'] for r in successful_tests) / len(successful_tests)
            
            tested_accuracy = [r for r in successful_tests if r['accuracy'] is not None]
            avg_accuracy = sum(r['accuracy'] for r in tested_accuracy) / len(tested_accuracy) if tested_accuracy else None
            
            print(f"\n{'-'*80}")
            print("AVERAGES:")
            print(f"{'-'*80}")
            print(f"Fields per invoice: {avg_fields:.1f}")
            print(f"Confidence: {avg_conf:.1f}%")
            print(f"Processing time: {avg_time:.1f}s")
            if avg_accuracy:
                print(f"Accuracy: {avg_accuracy:.1f}%")
        
        if failed_tests:
            print(f"\n{'-'*80}")
            print("FAILED EXTRACTIONS:")
            print(f"{'-'*80}")
            for result in failed_tests:
                print(f"❌ {result['file']}: {result.get('error', 'Unknown error')}")
        
        print("\n" + "="*80)
        
        # Save report to file
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n📊 Full report saved to: {report_file}")
        
        return self.results


def main():
    """Run comprehensive tests"""
    print("="*80)
    print("COMPREHENSIVE INVOICE EXTRACTION TESTING")
    print("="*80)
    
    tester = InvoiceTester()
    
    # Find all test invoices
    print("\nSearching for invoice files...")
    invoice_files = tester.find_test_invoices()
    
    print(f"Found {len(invoice_files)} invoice(s)")
    
    if not invoice_files:
        print("\n⚠️  No invoice files found in uploads directory!")
        print("Please upload invoice images to test.")
        return
    
    # Test each invoice
    # Define expected data for known invoices
    expected_data_map = {
        "Invoice1.png": {
            "vendor_name": "Hankook Tire America Corp",
            "invoice_number": "9146515234",
            "invoice_date": "2025-12-04",
            "total_amount": "158.48"
        },
        "Screenshot 2025-11-18 234357.png": {
            "vendor_name": "BELLE TIRE RECEIPT",
            "invoice_number": "45752969",
            "invoice_date": "2025-05-12",
            "total_amount": "0.0"
        }
    }
    
    for invoice_file in invoice_files:
        # Get filename
        filename = os.path.basename(invoice_file)
        
        # Get expected data if available
        expected_data = expected_data_map.get(filename)
        
        # Test
        tester.test_invoice(invoice_file, expected_data)
    
    # Generate report
    tester.generate_report()


if __name__ == "__main__":
    main()