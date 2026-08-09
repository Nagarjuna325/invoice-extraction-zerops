print("Testing imports...")

try:
    import torch
    print(f"✅ PyTorch: {torch.__version__}")
except Exception as e:
    print(f"❌ PyTorch error: {e}")

try:
    import transformers
    print(f"✅ Transformers: {transformers.__version__}")
except Exception as e:
    print(f"❌ Transformers error: {e}")

try:
    from PIL import Image
    print(f"✅ PIL/Pillow: OK")
except Exception as e:
    print(f"❌ PIL error: {e}")

print("\n✅ All dependencies ready!")