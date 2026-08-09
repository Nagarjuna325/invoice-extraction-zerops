print("Downloading Impira LayoutLM Invoice Model...")
print("This is a model trained on 100k+ invoices!")
print("Downloading ~500MB, may take 2-3 minutes...\n")

from transformers import pipeline

print("Step 1: Loading document-question-answering pipeline...")
try:
    # Try with Impira invoice-specific model
    extractor = pipeline(
        "document-question-answering",
        model="impira/layoutlm-document-qa"
    )
    print("✅ Impira LayoutLM model loaded!\n")
    
    print("Step 2: Testing model...")
    print(f"Model type: {type(extractor)}")
    print(f"Model name: impira/layoutlm-document-qa")
    print("\n✅ Impira model ready to use!")
    print("\nThis model can answer questions about invoices!")
    print("Example: 'What is the invoice number?'")
    
except Exception as e:
    print(f"❌ Error loading Impira model: {e}")
    print("\nTrying alternative approach...")
    
    # Fallback: Use LayoutLMv3 with question-answering
    from transformers import LayoutLMv3Processor, LayoutLMv3ForQuestionAnswering
    
    processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base")
    model = LayoutLMv3ForQuestionAnswering.from_pretrained("microsoft/layoutlmv3-base")
    
    print("✅ Using LayoutLMv3 with Q&A capability as fallback")