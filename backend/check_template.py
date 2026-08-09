from app.core.database import SessionLocal
from app.models.vendor import Vendor
import json

db = SessionLocal()

vendor = db.query(Vendor).filter(Vendor.id == 3).first()

if vendor and vendor.has_template:
    print("="*80)
    print("TEMPLATE DATA FOR 'GLOBAL ENTERPRISES'")
    print("="*80)
    
    template = vendor.template_data
    if isinstance(template, str):
        template = json.loads(template)
    
    print(f"\nLearned from: {template.get('learned_from_invoices')} invoice(s)")
    print(f"\nField Patterns:")
    
    for field, pattern in template['field_patterns'].items():
        print(f"\n  {field}:")
        print(f"    Expected value: {pattern.get('example')}")
        print(f"    Confidence: {pattern.get('confidence', 0):.1f}%")

db.close()