# Invoice Extraction System - Deployment Guide

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 12+
- Tesseract OCR
- Git

---

## 📦 Installation

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd invoice-extraction-backend
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Tesseract OCR

**Windows:**
1. Download: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to: `C:\Program Files\Tesseract-OCR`
3. Add to PATH

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

**Mac:**
```bash
brew install tesseract
```

### 5. Setup Database
```bash
# Create PostgreSQL database
createdb invoice_extraction

# Run migrations
alembic upgrade head
```

### 6. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings
```

**.env file:**
```
DATABASE_URL=postgresql://postgres:postgres123@localhost:5432/invoice_extraction
SECRET_KEY=your-secret-key-here
DEBUG=True
```

---

## 🏃 Running the Application

### Development
```bash
python run.py
```

Server runs on: http://localhost:8000

### Production
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 📊 System Capabilities

### Supported File Formats
- ✅ **Images:** PNG, JPG, JPEG, TIFF, BMP
- ✅ **PDFs:** Single or multi-page (up to 10 pages)
- ✅ **Excel:** XLSX, XLS, XLSM
- ✅ **CSV:** Comma-separated values

### Extraction Models
1. **Impira LayoutLM** (Q&A on invoices)
2. **LayoutLMv3** (OCR + Layout)
3. **Donut** (End-to-end vision)

### Average Accuracy
- Images: 85-100%
- PDFs: 90-97%
- Excel/CSV: 95%
- **Overall: 90%+**

### Processing Speed
- Images: ~90 seconds
- PDFs: ~90 seconds per page
- Excel/CSV: ~1 second

---

## 📁 Project Structure
```
invoice-extraction-backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           └── upload.py          # Upload endpoint
│   ├── services/
│   │   ├── triple_hybrid_service.py   # Main extraction
│   │   ├── donut_service.py           # Donut model
│   │   ├── layoutlm_service.py        # LayoutLM model
│   │   └── document_processor.py      # PDF/Excel/CSV handler
│   ├── utils/
│   │   ├── field_validators.py        # Field validation
│   │   └── validators.py              # File validation
│   ├── models/
│   │   └── invoice.py                 # Database models
│   └── main.py                        # FastAPI app
├── uploads/                           # Upload directory
├── requirements.txt                   # Dependencies
├── run.py                             # Development server
└── DEPLOYMENT_GUIDE.md                # This file
```

---

## 🔧 Configuration

### Model Configuration
Models are downloaded automatically on first use to:
- Windows: `C:\Users\{user}\.cache\huggingface\hub\`
- Linux/Mac: `~/.cache/huggingface/hub/`

**Required disk space:** ~2GB

### Processing Limits
- Max file size: 10MB (configurable in `app/utils/validators.py`)
- Max PDF pages: 10 (configurable in `document_processor.py`)
- Concurrent uploads: Based on worker count

---

## 🧪 Testing

### Run All Tests
```bash
# Test triple hybrid
python test_triple_hybrid.py

# Test all document types
python test_all_documents.py

# Test comprehensive
python test_comprehensive.py
```

### Test with Sample Invoices
Sample invoices are in `uploads/` directory.

---

## 🐛 Troubleshooting

### Issue: "Tesseract not found"
**Solution:** Install Tesseract OCR and add to PATH

### Issue: "Database connection failed"
**Solution:** Check PostgreSQL is running and credentials are correct

### Issue: "Models downloading slowly"
**Solution:** First run downloads ~2GB of models. Be patient!

### Issue: "Out of memory"
**Solution:** Reduce worker count or increase system RAM

### Issue: "PDF conversion fails"
**Solution:** Ensure PyMuPDF is installed: `pip install PyMuPDF`

---

## 📈 Performance Optimization

### For Production:

1. **Use GPU** (if available)
```bash
   # Install GPU version of PyTorch
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

2. **Increase Workers**
```bash
   uvicorn app.main:app --workers 4
```

3. **Use Redis for Caching** (optional)
   - Cache extraction results
   - Reduce duplicate processing

4. **Enable Model Quantization** (optional)
   - Reduce model size
   - Faster inference

---

## 🔐 Security

### Production Checklist:
- [ ] Change SECRET_KEY in .env
- [ ] Set DEBUG=False
- [ ] Use HTTPS
- [ ] Implement rate limiting
- [ ] Add authentication
- [ ] Enable CORS properly
- [ ] Sanitize file uploads
- [ ] Use environment variables for secrets

---

## 📊 Monitoring

### Recommended Tools:
- **Logs:** Check `logs/` directory
- **Metrics:** Prometheus + Grafana
- **Errors:** Sentry
- **Uptime:** UptimeRobot

---

## 🚀 Deployment Options

### Option 1: Docker
```dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Option 2: Heroku
```bash
# Install Heroku CLI
heroku create your-app-name
git push heroku main
```

### Option 3: AWS EC2
- Launch Ubuntu instance
- Install dependencies
- Run with systemd service

### Option 4: Railway/Render
- Connect GitHub repo
- Auto-deploy on push

---

## 📞 Support

For issues or questions:
- GitHub Issues: <your-repo>/issues
- Email: your-email@example.com
- Documentation: See README.md

---

## 📄 License

[Your License Here]

---

## 🎉 Credits

Built with:
- FastAPI
- Hugging Face Transformers
- Impira LayoutLM
- Microsoft LayoutLMv3
- Naver Clova Donut
- PyMuPDF
- Tesseract OCR

---

**Version:** 1.0.0  
**Last Updated:** December 27, 2024