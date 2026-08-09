cat > Summary.md <<'EOF'

# Invoice Extraction Backend — Full Summary & Command Reference

## 1) Environment Setup (Windows / Git Bash)

### 1.1) Navigate to project

```bash
cd /c/Users/nagar/invoice-extraction-backend
```

### 1.2) Activate virtual environment

```bash
source venv/Scripts/activate
```

---

## 2) Database Access (PostgreSQL)

### 2.1) Confirm service running (PowerShell)

```powershell
Get-Service postgresql*
```

### 2.2) Connect to DB

```bash
psql -U postgres -d invoice_extraction
# password: postgres123
```

### 2.3) Common DB queries

```sql
SELECT COUNT(*) FROM invoices;
SELECT COUNT(*) FROM corrections;
SELECT COUNT(*) FROM vendors;
```

Example focused invoice query (replace `upload_id`):

```sql
SELECT upload_id, vendor_id, used_template,
       extracted_data->>'invoice_date' AS invoice_date,
       extracted_data->>'due_date' AS due_date,
       extracted_data->>'vendor_name' AS vendor_name,
       ocr_tokens IS NOT NULL AS has_tokens
FROM invoices
WHERE upload_id = 'upload_20260104_154658_5be7e88a';
```

---

## 3) Key Flags / Env Variables (Controls what runs)

### Core flags

```bash
export USE_BBOX_OVERRIDE=1
export DEBUG=1
export DETERMINISTIC=1
export OCR_ENGINE=quadruple_hybrid
export MODELS=impira,layoutlm,donut,docling
export OCR_VARIANTS=rapid,tesseract,matrix
export IMAGE_ENHANCEMENT=1
export VALIDATION_LEVEL=strict
export TEMPLATE_CREATION=1
```

### Meaning / effect

- **USE_BBOX_OVERRIDE**: uses template bounding boxes for known vendors
- **DEBUG**: verbose logs
- **DETERMINISTIC**: fixed seeds (reproducible results)
- **OCR_ENGINE**: extraction pipeline (`quadruple_hybrid` = full)
- **MODELS**: ML extractors (Impira, LayoutLM, Donut, Docling)
- **OCR_VARIANTS**: OCR engines (rapid, tesseract, matrix)
- **IMAGE_ENHANCEMENT**: pre-OCR scaling + brightness/contrast fixes
- **VALIDATION_LEVEL**: how strict validation/heuristics are
- **TEMPLATE_CREATION**: auto-create template from corrections

---

## 4) Running the Backend

### 4.1) Start server

```bash
python run.py
```

### 4.2) API endpoints

- Swagger UI: `http://localhost:8000/api/docs`
- Upload invoice:
  ```bash
  curl -X POST "http://localhost:8000/api/v1/invoices/upload" -F "file=@/path/to/invoice.png"
  ```
- Check status:
  ```bash
  curl "http://localhost:8000/api/v1/invoices/{upload_id}/status"
  ```
- Fetch results:
  ```bash
  curl "http://localhost:8000/api/v1/invoices/{upload_id}"
  ```

---

## 5) What’s Running / What the System Uses

### Models / Engines used in `quadruple_hybrid` (from logs)

- **Impira**
- **LayoutLM**
- **Donut**
- **Docling** (PDF only; skipped for images)
- **OCR**:
  - Rapid
  - Tesseract
  - Matrix variants (TrOCR, Paddle OCR variants, etc.)
  - Fused OCR for fields (po_number, invoice_number, etc.)

---

## 6) Common Issue: Wrong Field Values (e.g., PO number “Cust0mer”)

### Why it happens

- OCR misread “Customer” as “Cust0mer”
- The system uses “OCR-fused override” for some fields when models disagree
- Flagged for review (`needs_review=true`)

### Fix (manual correction)

- Apply correction via API or update DB directly
- After correction, templates can be built (if `TEMPLATE_CREATION=1`) and `USE_BBOX_OVERRIDE=1` helps accuracy

---

## 7) Useful Commands for Re-running / Debugging

### Re-run with high accuracy (full pipeline + max logging)

```bash
export USE_BBOX_OVERRIDE=1
export DEBUG=1
export DETERMINISTIC=1
export OCR_ENGINE=quadruple_hybrid
export MODELS=impira,layoutlm,donut,docling
export OCR_VARIANTS=rapid,tesseract,matrix
export IMAGE_ENHANCEMENT=1
export VALIDATION_LEVEL=strict
export TEMPLATE_CREATION=1
python run.py
```

### If PaddleOCR fails (common error in logs)

- `module 'pkgutil' has no attribute 'ImpImporter'`
- Fix by updating or reinstalling Paddle/PaddleOCR

---

## 8) How to Use This File

- File created in repo: `Summary.md`
- Open it in your editor (VS Code) or view via:
  ```bash
  cat Summary.md
  ```
  EOF

````# filepath: c:\Users\nagar\invoice-extraction-backend\Summary.md
cat > Summary.md <<'EOF'
# Invoice Extraction Backend — Full Summary & Command Reference

## 1) Environment Setup (Windows / Git Bash)

### 1.1) Navigate to project
```bash
cd /c/Users/nagar/invoice-extraction-backend
````

### 1.2) Activate virtual environment

```bash
source venv/Scripts/activate
```

---

## 2) Database Access (PostgreSQL)

### 2.1) Confirm service running (PowerShell)

```powershell
Get-Service postgresql*
```

### 2.2) Connect to DB

```bash
psql -U postgres -d invoice_extraction
# password: postgres123
```

### 2.3) Common DB queries

```sql
SELECT COUNT(*) FROM invoices;
SELECT COUNT(*) FROM corrections;
SELECT COUNT(*) FROM vendors;
```

Example focused invoice query (replace `upload_id`):

```sql
SELECT upload_id, vendor_id, used_template,
       extracted_data->>'invoice_date' AS invoice_date,
       extracted_data->>'due_date' AS due_date,
       extracted_data->>'vendor_name' AS vendor_name,
       ocr_tokens IS NOT NULL AS has_tokens
FROM invoices
WHERE upload_id = 'upload_20260104_154658_5be7e88a';
```

---

## 3) Key Flags / Env Variables (Controls what runs)

### Core flags

```bash
export USE_BBOX_OVERRIDE=1
export DEBUG=1
export DETERMINISTIC=1
export OCR_ENGINE=quadruple_hybrid
export MODELS=impira,layoutlm,donut,docling
export OCR_VARIANTS=rapid,tesseract,matrix
export IMAGE_ENHANCEMENT=1
export VALIDATION_LEVEL=strict
export TEMPLATE_CREATION=1
```

### Meaning / effect

- **USE_BBOX_OVERRIDE**: uses template bounding boxes for known vendors
- **DEBUG**: verbose logs
- **DETERMINISTIC**: fixed seeds (reproducible results)
- **OCR_ENGINE**: extraction pipeline (`quadruple_hybrid` = full)
- **MODELS**: ML extractors (Impira, LayoutLM, Donut, Docling)
- **OCR_VARIANTS**: OCR engines (rapid, tesseract, matrix)
- **IMAGE_ENHANCEMENT**: pre-OCR scaling + brightness/contrast fixes
- **VALIDATION_LEVEL**: how strict validation/heuristics are
- **TEMPLATE_CREATION**: auto-create template from corrections

---

## 4) Running the Backend

### 4.1) Start server

```bash
python run.py
```

### 4.2) API endpoints

- Swagger UI: `http://localhost:8000/api/docs`
- Upload invoice:
  ```bash
  curl -X POST "http://localhost:8000/api/v1/invoices/upload" -F "file=@/path/to/invoice.png"
  ```
- Check status:
  ```bash
  curl "http://localhost:8000/api/v1/invoices/{upload_id}/status"
  ```
- Fetch results:
  ```bash
  curl "http://localhost:8000/api/v1/invoices/{upload_id}"
  ```

---

## 5) What’s Running / What the System Uses

### Models / Engines used in `quadruple_hybrid` (from logs)

- **Impira**
- **LayoutLM**
- **Donut**
- **Docling** (PDF only; skipped for images)
- **OCR**:
  - Rapid
  - Tesseract
  - Matrix variants (TrOCR, Paddle OCR variants, etc.)
  - Fused OCR for fields (po_number, invoice_number, etc.)

---

## 6) Common Issue: Wrong Field Values (e.g., PO number “Cust0mer”)

### Why it happens

- OCR misread “Customer” as “Cust0mer”
- The system uses “OCR-fused override” for some fields when models disagree
- Flagged for review (`needs_review=true`)

### Fix (manual correction)

- Apply correction via API or update DB directly
- After correction, templates can be built (if `TEMPLATE_CREATION=1`) and `USE_BBOX_OVERRIDE=1` helps accuracy

---

## 7) Useful Commands for Re-running / Debugging

### Re-run with high accuracy (full pipeline + max logging)

```bash
export USE_BBOX_OVERRIDE=1
export DEBUG=1
export DETERMINISTIC=1
export OCR_ENGINE=quadruple_hybrid
export MODELS=impira,layoutlm,donut,docling
export OCR_VARIANTS=rapid,tesseract,matrix
export IMAGE_ENHANCEMENT=1
export VALIDATION_LEVEL=strict
export TEMPLATE_CREATION=1
python run.py
```

### If PaddleOCR fails (common error in logs)

- `module 'pkgutil' has no attribute 'ImpImporter'`
- Fix by updating or reinstalling Paddle/PaddleOCR

---

## 8) How to Use This File

- File created in repo: `Summary.md`
- Open it in your editor (VS Code) or view via:
  ```bash
  cat Summary.md
  ```
  EOF
