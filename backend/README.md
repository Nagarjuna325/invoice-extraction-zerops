# Invoice Extraction Backend

FastAPI service for multi-format invoice extraction using a quadruple-hybrid pipeline (Docling + Impira + LayoutLMv3 + Donut), validation heuristics, and template learning.

## What this service does
- Accepts PDFs, images, Excel, and CSV files via REST API
- Runs multi-model extraction with deterministic seeding and consensus voting
- Validates and auto-corrects totals, dates, and IDs (including US/EU decimal formats)
- Recognizes vendors and learns templates from human corrections
- Persists results, confidences, and optional OCR metadata in PostgreSQL

## Architecture and Flow

High-level request flow:
```
Client
  |
  v
POST /api/v1/invoices/upload
  |
  v
StorageService -> uploads/{upload_id}/{filename}
  |
  v
Invoice row created (status=UPLOADED)
  |
  v
Background task (process_invoice_background)
  |
  v
DocumentProcessor -> type detection -> PDF->images or Excel/CSV parse
  |
  v
QuadrupleHybridService -> IntelligentMerger -> ValidationService
  |
  v
VendorService -> TemplateService (optional)
  |
  v
Invoice row updated (status=EXTRACTED or FAILED)
  |
  v
Client polls GET /api/v1/invoices/{upload_id}/status
  |
  v
GET /api/v1/invoices/{upload_id} -> final data
```

Extraction pipeline detail:
```
Input file
  |
  +-- Excel/CSV -> structured parsing -> extracted_data
  |
  +-- Image/PDF
        |
        +-- Image quality check (default) OR Pre-OCR pipeline (ENABLE_ADVANCED_OCR_PIPELINE)
        |
        +-- QuadrupleHybridService
              - Docling (PDF only, structure-aware)
              - Impira (Q&A)
              - LayoutLMv3 (layout + OCR)
              - Donut (end-to-end)
              - Optional OCR voters (RapidOCR, Docling text, Tesseract)
              - Optional OCR Matrix + Fusion (label-anchored fields)
        |
        +-- IntelligentMerger (consensus + confidence calibration)
        |
        +-- ValidationService (field + heuristic + cross-field checks)
        |
        +-- Vendor recognition + template voter + template application
```

Multi-page PDF behavior:
```
PDF -> page images -> per-page extraction
  |
  +-- Same invoice_number across pages -> merge line_items, keep page 1 headers
  |
  +-- Different invoice_number / missing -> return page 1 as primary
       and populate _other_pages metadata + warning
```

Template learning loop:
```
1) First invoice -> extraction -> user fixes fields
2) POST /api/v1/invoices/correct -> corrections table
3) Template updated for vendor (examples + optional bbox anchors)
4) Next invoice -> template voter/apply_template -> higher confidence
```

Additional architecture diagrams:

Service and data topology:
```
               +------------------------------+
               |          Client UI           |
               +--------------+---------------+
                              |
                              v
               +--------------+---------------+
               |          FastAPI API         |
               |  /api/v1/invoices/* endpoints|
               +--------------+---------------+
                              |
          +-------------------+--------------------+
          |                                        |
          v                                        v
+---------------------+                 +---------------------+
|  StorageService     |                 |   Postgres DB       |
|  uploads/{id}/      |                 | invoices/vendors/   |
|  saved files        |                 | corrections tables  |
+---------------------+                 +---------------------+
          |
          v
+---------------------+     +---------------------+     +---------------------+
| DocumentProcessor   | --> | QuadrupleHybridSvc  | --> | ValidationService   |
| PDF->images, CSV    |     | Docling/Impira/     |     | heuristics + cross  |
| Excel parsing       |     | LayoutLM/Donut      |     | field checks        |
+---------------------+     +---------------------+     +---------------------+
                                                           |
                                                           v
                                            +------------------------------+
                                            | VendorService + TemplateSvc  |
                                            | template voter + apply       |
                                            +------------------------------+
```

Data flow (what gets written where):
```
Upload file
  |
  +-- uploads/{upload_id}/{filename} (disk)
  |
  +-- invoices row (DB):
      - status: UPLOADED -> PROCESSING -> EXTRACTED/FAILED
      - extracted_data, field_confidences, overall_confidence
      - raw_ocr_text, validation_metadata, ocr_tokens (optional)
  |
  +-- vendors row (DB):
      - fingerprint, template_data, stats
  |
  +-- corrections rows (DB):
      - one row per corrected field (with bbox/page when available)
```

OCR matrix internals (deep view):
```
Pre-OCR Pipeline (optional)
  |
  +-- base image (possibly scaled/deskewed)
  |
  +-- Variants (PRE_OCR_GENERATE_VARIANTS):
  |     v1_gray              -> grayscale
  |     v2_clahe             -> contrast-enhanced
  |     v3_binarized         -> adaptive threshold
  |     v4_superres_clahe    -> upscaled + CLAHE
  |
  +-- OCR Matrix (ENABLE_OCR_MATRIX):
        |
        +-- PaddleOCR (if OCR_MATRIX_ENABLE_PADDLE):
        |     - run on v1_gray, v2_clahe, v4_superres_clahe
        |     - yields tokens + raw text per variant
        |
        +-- Tesseract (if OCR_MATRIX_ENABLE_TESSERACT):
        |     - run on v3_binarized
        |     - yields tokens + raw text
        |
        +-- TrOCR (if OCR_MATRIX_ENABLE_TROCR):
        |     - run on v1_gray
        |     - yields raw text (no token boxes)
        |
        +-- OcrMatrixResult:
              outputs: {engine_variant: OcrOutput(text, tokens)}
              raw_texts: {engine_variant: text}
              tokens: {engine_variant: [OcrToken]}
  |
  +-- OCR Fusion (ENABLE_OCR_FUSION):
        |
        +-- label matcher (rule/semantic)
        +-- field candidates from tokens/text
        +-- weighted scoring per engine (OCR_FUSION_WEIGHT_*)
        +-- fused_fields + confidence + debug
  |
  +-- Optional consumers:
        - IntelligentMerger adds OCR voters
        - LineItemParser uses tokens for table rows
        - FooterTotalExtractor uses targeted OCR region
```

Validation stages (deep view):
```
ValidationService.validate_and_correct
  |
  +-- Stage 1: Document type detection
  |     - invoice vs credit_note vs quote
  |     - uses OCR text + total amount heuristics
  |
  +-- Stage 2: Field-level validation
  |     - invoice_number pattern validation
  |     - invoice_date parsing + impossible date repair
  |     - due_date parsing + repair
  |     - total_amount normalization (US/EU decimal formats)
  |     - currency inference when missing
  |     - vendor vs customer heuristics
  |
  +-- Stage 3: Advanced heuristics
  |     - round-number suspicion
  |     - vendor consistency against known vendor (if provided)
  |
  +-- Stage 4: Cross-field validation
  |     - line_items sum vs total_amount
  |     - date consistency (invoice_date vs due_date)
  |     - decimal-format mismatch detection from OCR text
  |
  +-- Stage 5: Final scoring + review decision
        - overall_confidence from field confidences
        - warnings -> needs_review
        - corrections recorded in metadata
```

Validation stages pseudocode (exact paths):
```
app/services/validation_service.py::ValidationService.validate_and_correct

def validate_and_correct(extracted_data, field_confidences, line_items, raw_ocr_text, known_vendor, vendor_id):
    doc_type, doc_conf, doc_reason = heuristics.detect_document_type(...)
    field_results = _validate_fields_with_heuristics(extracted_data, raw_ocr_text, doc_type)
    updated_confidences = _adjust_confidences_from_field_validation(field_confidences, field_results.metadata)
    heuristic_results = _apply_advanced_heuristics(validated_data, updated_confidences, line_items, raw_ocr_text, known_vendor, vendor_id)
    cross_results = cross_validator.validate_all_cross_fields(validated_data, line_items, known_vendor, vendor_id, raw_ocr_text)
    apply cross_results.suggested_corrections if any
    overall_confidence = _calculate_overall_confidence(updated_confidences, warnings)
    needs_review = _determine_needs_review(warnings, overall_confidence, corrections_applied, doc_type)
    return validated_data, updated_confidences, warnings, corrections_applied, metadata, needs_review
```

Label matching layers (used in OCR fusion):
```
LabelMatcher
  |
  +-- Rule matching (default):
  |     - regex label patterns per field
  |     - negative-term suppression (e.g., "subtotal" for total)
  |
  +-- Semantic matching (optional):
        - sentence-transformers embeddings
        - cosine similarity vs label synonyms
        - enabled with ENABLE_LABEL_SEMANTIC_MATCH
```

OCR fusion pseudocode (exact paths):
```
app/services/ocr_fusion_service.py::OcrFusionService.fuse

def fuse(matrix_result):
    candidates = {}
    for source_name, output in matrix_result.outputs:
        weight = _engine_weight(source_name)
        extracted = _extract_from_output(output, source_name, weight)
        candidates[field].append(FieldCandidate(value, score, source))
    for field, items in candidates:
        best = _pick_best_candidate(field, items)
        fused_fields[field] = best.value
    overall_confidence = average(scores) -> clipped 50-95
    return fused_fields, overall_confidence, debug

app/services/ocr_fusion_service.py::_extract_from_output

if output.tokens:
    lines = _group_tokens_by_line(tokens)
    if ENABLE_LABEL_ANCHORED_DATES:
        anchored_dates = _extract_label_anchored_dates(lines)
    if ENABLE_LABEL_ANCHORED_DATES_TEXT:
        anchored_dates_text = _extract_label_anchored_dates_text(output.text)
    for each FieldSpec:
        cand = _extract_from_lines(lines, spec)
    if OCR_FUSION_TOTAL_FALLBACK and "total_amount" missing:
        cand = _extract_total_fallback(lines)
else:
    for each FieldSpec:
        cand = _extract_from_text(output.text, spec)
```

Flag to function cross-reference (key toggles)

Pre-OCR and quality:
- ENABLE_ADVANCED_OCR_PIPELINE -> app/services/pre_ocr_pipeline.py::PreOcrPipeline.preprocess_image
- PRE_OCR_TARGET_DPI, PRE_OCR_SMALL_FONT_DPI -> PreOcrPipeline._estimate_dpi, _detect_small_font
- PRE_OCR_ENABLE_DESKEW -> PreOcrPipeline._deskew_image
- PRE_OCR_GENERATE_VARIANTS -> app/services/ocr_variant_generator.py::OcrVariantGenerator.generate
- PRE_OCR_VARIANT_SUPERRES_SCALE -> OcrVariantGenerator._build_superres_variant

OCR matrix and fusion:
- ENABLE_OCR_MATRIX -> app/services/ocr_matrix.py::OcrMatrixRunner.run
- OCR_MATRIX_ENABLE_PADDLE -> OcrMatrixRunner._run_paddle
- OCR_MATRIX_ENABLE_TESSERACT -> OcrMatrixRunner._run_tesseract
- OCR_MATRIX_ENABLE_TROCR -> OcrMatrixRunner._run_trocr
- ENABLE_OCR_FUSION -> app/services/ocr_fusion_service.py::OcrFusionService.fuse
- OCR_FUSION_FORCE_FIELDS -> app/services/intelligent_merger.py::_ocr_fusion_force_fields
- OCR_FUSION_TOTAL_FALLBACK -> OcrFusionService._extract_total_fallback
- OCR_FUSION_WEIGHT_* -> OcrFusionService._engine_weight

Template learning and corrections:
- ENABLE_TEMPLATE_VOTER -> app/api/v1/endpoints/upload.py::process_invoice_background
- TEMPLATE_VOTER_CONFIDENCE -> app/services/intelligent_merger.py::_add_template_voter
- AUTO_REFRESH_TEMPLATE_FROM_CORRECTIONS -> app/services/template_service.py::update_template_from_corrections
- AUTO_ANCHOR_CORRECTIONS -> app/api/v1/endpoints/corrections.py::correct_invoice
- USE_BBOX_OVERRIDE -> app/services/intelligent_merger.py::merge_4way

Line items and totals:
- ENABLE_LINE_ITEM_PARSER -> app/services/quadruple_hybrid_service.py::extract_invoice
- ENABLE_AMOUNT_COLUMN_REOCR -> app/services/line_item_parser.py::_reocr_amount_column
- ENABLE_SUPERRES_CROPS -> app/services/line_item_parser.py::_superres_crop
- ENABLE_FOOTER_TOTAL_EXTRACT -> app/services/footer_total_extractor.py::extract
- TOTAL_PREFER_FOOTER, TOTAL_FOOTER_MIN_CONF -> app/services/intelligent_merger.py::_prefer_ocr_fused

OCR text/token storage:
- STORE_OCR_TOKENS -> app/services/quadruple_hybrid_service.py::_build_ocr_tokens
- STORE_OCR_TEXTS -> app/services/quadruple_hybrid_service.py::extract_invoice

Label matching:
- LABEL_MATCH_MODE, ENABLE_LABEL_SEMANTIC_MATCH -> app/utils/label_matcher.py::LabelMatcher.match_line
- LABEL_MATCH_MIN_SCORE -> LabelMatcher._semantic_match
- LABEL_MATCH_DEBUG -> LabelMatcher._log_label_matches
- ENABLE_LABEL_ANCHORED_DATES -> app/services/ocr_fusion_service.py::_extract_label_anchored_dates
- ENABLE_LABEL_ANCHORED_DATES_TEXT -> app/services/ocr_fusion_service.py::_extract_label_anchored_dates_text

Consensus merger (deep view):
```
IntelligentMerger.merge_4way
  |
  +-- Inputs:
  |     docling_result, impira_result, layoutlm_result, donut_result
  |     optional OCR voters (raw OCR text -> field heuristics)
  |     optional OCR fusion fields
  |     optional template voter fields
  |
  +-- Build model_results:
  |     - each model -> extracted_data + confidence
  |     - OCR voters -> extracted_data + fixed confidence
  |
  +-- For each field:
  |     - if USE_BBOX_OVERRIDE and template has bbox value: force template
  |     - else if OCR fusion override valid: prefer OCR fusion
  |     - else run consensus voting:
  |         * normalize values
  |         * count votes + weighted confidences
  |         * tie-break (Docling priority, then weighted score)
  |         * agreement level (unanimous/strong/moderate/weak/conflict)
  |         * calibrated confidence
  |
  +-- Output:
        merged extracted_data
        field_confidences
        voting_details (all values + selection)
        overall_confidence (avg)
```

Consensus merger pseudocode (exact paths):
```
app/services/intelligent_merger.py::IntelligentMerger.merge_4way

def merge_4way(docling_result, impira_result, layoutlm_result, donut_result,
               raw_ocr_text="", extra_ocr_texts=None, extra_ocr_fields=None,
               extra_template_fields=None, template_confidence=85.0):
    model_results = {
        "docling": docling_result,
        "impira": impira_result,
        "layoutlm": layoutlm_result,
        "donut": donut_result,
    }
    if extra_ocr_texts:
        _add_ocr_voters(model_results, extra_ocr_texts)
    if extra_ocr_fields:
        _add_ocr_field_voter(model_results, extra_ocr_fields)
    if extra_template_fields:
        _add_template_voter(model_results, extra_template_fields, template_confidence)

    for field in all_fields(model_results):
        if USE_BBOX_OVERRIDE and template has value:
            choose template value (forced)
            continue
        if _prefer_ocr_fused(field, model_results, raw_ocr_text):
            choose OCR fused value
            continue
        vote_result = consensus_algorithm.vote_on_field(field, model_results)
        choose vote_result.consensus_value

    overall_confidence = avg(field_confidences)
    return merged_data, field_confidences, voting_details, model_outputs, overall_confidence
```

Template voter flow (deep view):
```
Template voter (ENABLE_TEMPLATE_VOTER)
  |
  +-- Pre-vendor match:
  |     - extract vendor from raw extraction
  |     - match existing vendor (no create)
  |
  +-- Template refresh (AUTO_REFRESH_TEMPLATE_FROM_CORRECTIONS):
  |     - rebuild template from corrections table
  |
  +-- build_template_voter_fields:
  |     - for each field, pick example value
  |     - if bbox + image path: re-OCR anchored region
  |
  +-- Merge with template voter:
  |     - IntelligentMerger.merge_4way with extra_template_fields
  |     - TEMPLATE_VOTER_CONFIDENCE applied to template votes
  |
  +-- After validation:
        - apply_template (bbox re-OCR or corruption detection)
        - boost confidence or flag for review
```

Template voter pseudocode (exact paths):
```
app/api/v1/endpoints/upload.py::process_invoice_background

if settings.ENABLE_TEMPLATE_VOTER:
    template_vendor_info = vendor_service.extract_vendor_info(extracted_data, field_confidences)
    pre_vendor = vendor_service.match_vendor(db, template_vendor_info)
    if pre_vendor and pre_vendor.has_template and result.get("model_results_raw"):
        if settings.AUTO_REFRESH_TEMPLATE_FROM_CORRECTIONS:
            template_service.update_template_from_corrections(db, pre_vendor.id)
        template_fields = template_service.build_template_voter_fields(
            pre_vendor.template_data,
            image_path=template_image_path,
        )
        merged = intelligent_merger.merge_4way(
            docling_result=mr.get("docling", {}),
            impira_result=mr.get("impira", {}),
            layoutlm_result=mr.get("layoutlm", {}),
            donut_result=mr.get("donut", {}),
            raw_ocr_text=mr.get("extra_ocr_texts", {}).get("ocr_rapid", ""),
            extra_ocr_texts=mr.get("extra_ocr_texts", {}),
            extra_template_fields=template_fields,
            template_confidence=settings.TEMPLATE_VOTER_CONFIDENCE,
        )
        extracted_data = merged["extracted_data"]
        field_confidences = merged["field_confidences"]

app/services/template_service.py::build_template_voter_fields

for each field in template_data.field_patterns:
    if bbox + image_path:
        candidate = _extract_field_from_bbox(field, pattern, image_path)
    else:
        candidate = first example value
    add candidate to voter_fields
```

## Supported files and formats

Accepted input types (validator rules live in app/utils/validators.py):
- Images: .png, .jpg, .jpeg, .tiff, .bmp
- PDFs: .pdf
- Excel: .xlsx, .xls, .xlsm
- CSV: .csv

Content types accepted:
- image/jpeg, image/jpg, image/png, image/tiff, image/bmp
- application/pdf
- application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
- application/vnd.ms-excel
- text/csv, application/csv

## Processing time estimates

Actual time depends on model downloads, CPU/GPU, file size, and enabled flags.

- Excel/CSV: typically < 1s (parsed without ML models)
- Images (single page): ~30-120s with full quadruple hybrid
- PDF (single page): ~45-150s (Docling + triple hybrid)
- PDF (multi-page): scales roughly linearly per page

Performance tips:
- Enable only the features you need (OCR matrix/fusion adds extra runtime).
- Pre-download models with the helper scripts to avoid first-run latency.

## Image enhancement and OCR variants

This codebase uses multiple image enhancement techniques to improve OCR and extraction reliability on low-quality scans.

### Why these techniques were added
- Real invoices often arrive as scans or photos with low DPI, blur, skew, and uneven lighting.
- OCR models are sensitive to contrast, sharpness, and deskew; minor changes can shift token boundaries.
- Line-item totals are usually in dense tables, where tiny text and low contrast cause frequent errors.
- Template anchoring needs stable coordinates, which improves when text is cleaner and less skewed.

### Default image quality check (images only)
When ENABLE_ADVANCED_OCR_PIPELINE is false, image files (PNG/JPG) run through the quality checker:
- Resolution and DPI checks
- Blur detection (Laplacian variance)
- Contrast and brightness checks
- Optional auto-enhancement

Auto-enhancement steps (app/utils/image_quality_checker.py):
- Denoising (fastNlMeansDenoisingColored) when blurry
- CLAHE contrast enhancement when low contrast
- Brightness adjustment when too dark or too bright
- Sharpening (3x3 kernel)

Output:
- Enhanced image saved next to the original with suffix `_enhanced`
- Quality metrics attached in extracted_data._image_quality

### Advanced pre-OCR pipeline (ENABLE_ADVANCED_OCR_PIPELINE)
When enabled, the pre-ocr pipeline replaces the default quality check:
- Estimate DPI from image metadata or page size
- Scale to a target DPI (PRE_OCR_TARGET_DPI or PRE_OCR_SMALL_FONT_DPI)
- Deskew if rotation is detected
- Re-run quality checks on the processed image
- Optional variant generation for OCR matrix

Outputs:
- Temporary processed image (scaled/deskewed)
- Optional enhanced image from the quality checker
- Metadata stored in result pre_ocr_metadata and merged into extracted_data._image_quality

### OCR variants and matrix (PRE_OCR_GENERATE_VARIANTS + ENABLE_OCR_MATRIX)
Variants are generated to give OCR engines multiple views of the same page:
- v1_gray: grayscale
- v2_clahe: contrast-enhanced (CLAHE)
- v3_binarized: adaptive threshold for crisp text
- v4_superres_clahe: upscaled + CLAHE for small fonts

OCR matrix runs multiple OCR engines on variants:
- PaddleOCR (paddle_* outputs)
- Tesseract (tesseract_v3_binarized)
- TrOCR (trocr_v1_gray)

OCR fusion (ENABLE_OCR_FUSION) then labels and anchors fields using these outputs.

### Line-item re-OCR and super-res crops
Line item parsing can re-OCR the amount column:
- Crops the amount column region
- Optionally super-resolves crops (LINEITEM_SUPERRES_SCALE)
- Re-reads with Tesseract for higher-confidence amounts

### Outputs gathered from enhancement and OCR
These are visible in responses when the related flags are enabled:
- extracted_data._image_quality: resolution, DPI, blur_score, contrast, brightness, issues, enhancement flags
- extracted_data._ocr_texts: raw text from RapidOCR/Docling/Tesseract/Matrix (STORE_OCR_TEXTS)
- extracted_data._ocr_fused_fields: label-anchored OCR fusion results (ENABLE_OCR_FUSION)
- extracted_data._line_items: parsed line items (ENABLE_LINE_ITEM_PARSER)
- extracted_data._validation_metadata: validation and heuristic details

### Advantages
- Better OCR on low DPI or low contrast scans
- Improved stability for label anchoring and template bboxes
- Higher recall on totals and line items, especially in dense tables
- More explainability via stored OCR text and quality metrics

### Drawbacks
- Higher CPU and memory usage (especially with OCR matrix and fusion)
- Longer processing time (variants multiply OCR passes)
- More dependencies (OpenCV, PaddleOCR, TrOCR)
- Risk of over-processing: sharpening/CLAHE can amplify noise or distort faint text
- More temporary files (ensure disk cleanup and monitoring)

### DPI guidance (why 300 DPI is a common target)
OCR engines generally perform best when the effective DPI is around 300:
- Below ~150 DPI: characters are too few pixels tall, which hurts token shapes and spacing.
- 200-300 DPI: usually the best balance between clarity and processing cost.
- Above ~350 DPI: accuracy often improves for tiny fonts, but runtime and memory usage rise.

How this repo uses DPI:
- ImageQualityChecker flags low-DPI scans (MIN_DPI = 150) as quality issues.
- Pre-OCR pipeline scales toward PRE_OCR_TARGET_DPI (default 300).
- If small font is detected, it targets PRE_OCR_SMALL_FONT_DPI (default 350).

Practical guidance:
- If you control scanning, aim for 300 DPI, grayscale or color.
- If inputs are low DPI, enable ENABLE_ADVANCED_OCR_PIPELINE to rescale and deskew.
- If inputs are already high DPI, scaling is skipped to avoid extra processing.

## API

Base URL: http://localhost:8000
Docs: /api/docs

Endpoints:
- POST /api/v1/invoices/upload
  - multipart/form-data with file
  - optional form field ocr_engine (stored on invoice but not used to choose a pipeline)
- GET /api/v1/invoices/{upload_id}/status
- GET /api/v1/invoices/{upload_id}
- POST /api/v1/invoices/correct

Upload example:
```
curl -X POST \
  http://localhost:8000/api/v1/invoices/upload \
  -H "Content-Type: multipart/form-data" \
  -F "file=@invoice.pdf" \
  -F "ocr_engine=quadruple_hybrid"
```

Status example:
```
curl http://localhost:8000/api/v1/invoices/{upload_id}/status
```

Get results example:
```
curl http://localhost:8000/api/v1/invoices/{upload_id}
```

Correction example:
```
curl -X POST http://localhost:8000/api/v1/invoices/correct \
  -H "Content-Type: application/json" \
  -d '{
    "upload_id": "upload_20251228_182116_5902e947",
    "corrected_data": {
      "invoice_number": "INV-2023-001",
      "total_amount": 1250.00
    }
  }'
```

Response shape (trimmed):
```
{
  "upload_id": "upload_20251228_182116_5902e947",
  "status": "EXTRACTED",
  "invoice_type": "pdf",
  "vendor_name": "Acme Corp",
  "extracted_data": {
    "invoice_number": "INV-2023-001",
    "invoice_date": "2023-10-15",
    "total_amount": 1250.00
  },
  "field_confidences": { ... },
  "overall_confidence": 92.4,
  "validation_warnings": [ ... ],
  "needs_review": false,
  "line_items": [ ... ],
  "model_outputs": { ... },
  "voting_details": { ... },
  "image_quality": { ... }
}
```

Notes:
- Internal fields stored in extracted_data with a leading underscore are removed from the API response.
- If STORE_OCR_TEXTS is enabled, the response includes ocr_texts.
- If ENABLE_OCR_FUSION is enabled, the response includes ocr_fused_fields.

## Data model

Invoices:
- id (UUID), upload_id (string), file metadata, status
- extracted_data (JSONB), field_confidences (JSONB)
- overall_confidence, processing_time_ms
- vendor_id, used_template, template_match_confidence
- validation_metadata (JSONB), ocr_tokens (JSONB)

Vendors:
- vendor_name, vendor_fingerprint, vendor_name_normalized
- has_template, template_data, template_version
- invoice_count, last_seen

Corrections:
- one row per corrected field
- stores page_number and bbox when available
- used to rebuild vendor templates

Schema upgrades:
- app/db/bootstrap.py runs at startup and applies idempotent ALTER TABLE/CREATE TABLE statements
- Base.metadata.create_all creates missing tables

## Configuration

Settings are defined in app/config.py and loaded from .env via pydantic_settings.
The upload validator uses constants in app/utils/validators.py (not app/config.py).

### Application and server
- APP_NAME (Invoice Extraction System) - name shown in docs and logs
- APP_VERSION (1.0.0) - API version string
- DEBUG (True) - enables debug logs and uvicorn reload in run.py
- ENVIRONMENT (development) - informational
- HOST (0.0.0.0) and PORT (8000) - bind address

### Database
- DATABASE_URL (postgresql://postgres:password@localhost:5432/invoice_extraction)
- DB_POOL_SIZE (5) and DB_MAX_OVERFLOW (10)
- SQL echo is enabled when DEBUG is true

### CORS
- ALLOWED_ORIGINS (http://localhost:3000, http://localhost:5173)

### Upload validation (app/utils/validators.py)
- MAX_FILE_SIZE = 10MB
- ALLOWED_CONTENT_TYPES: image/*, application/pdf, Excel, CSV
- ALLOWED_EXTENSIONS: .png, .jpg, .pdf, .xlsx, .xls, .csv

### OCR basics
- DEFAULT_OCR_ENGINE (tesseract) - not used to branch pipelines
- TESSERACT_PATH (empty) - set if tesseract is not on PATH
- TESSERACT_LANG (eng) - used by tesseract and line-item re-OCR
- STORE_OCR_TOKENS (False) - stores token boxes in invoices.ocr_tokens
- STORE_OCR_TEXTS (False) - stores raw OCR text in extracted_data._ocr_texts

Environment-only flags:
- USE_TESSERACT_OCR (0/1) - in triple_hybrid_service, forces Tesseract instead of RapidOCR
- USE_TESSERACT_OCR_VOTER (0/1) - in quadruple_hybrid_service, adds a Tesseract text voter

### Template learning and correction flags
- ENABLE_TEMPLATE_VOTER (False) - injects template fields into consensus voting before validation
- TEMPLATE_VOTER_CONFIDENCE (85.0) - confidence used for template voter fields
- AUTO_REFRESH_TEMPLATE_FROM_CORRECTIONS (True) - rebuild template from corrections before voting
- AUTO_ANCHOR_CORRECTIONS (False) - uses stored OCR tokens to auto-attach bboxes on corrections
- USE_BBOX_OVERRIDE (False) - forces template OCR values to override model votes when bbox exists

### Advanced pre-OCR pipeline (ENABLE_ADVANCED_OCR_PIPELINE)
- ENABLE_ADVANCED_OCR_PIPELINE (False) - enables pre-ocr scaling, deskew, quality checks
- PRE_OCR_TARGET_DPI (300) - target DPI for scaling
- PRE_OCR_SMALL_FONT_DPI (350) - higher target when small font detected
- PRE_OCR_AUTO_DETECT_PAGE_SIZE (True) - guesses letter vs A4
- PRE_OCR_PAGE_SIZE_FALLBACK (letter)
- PRE_OCR_ENABLE_DESKEW (True) - deskew if angle detected
- PRE_OCR_GENERATE_VARIANTS (False) - generates multiple variants for OCR matrix
- PRE_OCR_VARIANT_SUPERRES_SCALE (2.0) and PRE_OCR_VARIANT_MAX_DIM (5000)

### OCR matrix (requires PRE_OCR_GENERATE_VARIANTS)
- ENABLE_OCR_MATRIX (False) - runs PaddleOCR, Tesseract, TrOCR on variants
- OCR_MATRIX_ENABLE_PADDLE (True), OCR_MATRIX_ENABLE_TESSERACT (True), OCR_MATRIX_ENABLE_TROCR (True)
- OCR_MATRIX_PADDLE_LANG (en)
- OCR_MATRIX_PADDLE_TABLE (True) - reserved, not used by current code

### OCR fusion and label matching (requires OCR matrix outputs)
- ENABLE_OCR_FUSION (False) - label-anchored fusion of OCR outputs
- OCR_FUSION_FORCE_FIELDS (invoice_number,po_number,invoice_date) - always prefer OCR fusion values
- OCR_FUSION_TOTAL_FALLBACK (False) - infer totals from bottom-right region
- OCR_FUSION_TOTAL_REGION_Y (0.4), OCR_FUSION_TOTAL_REGION_X (0.6)
- OCR_FUSION_WEIGHT_PADDLE (1.0), OCR_FUSION_WEIGHT_TESSERACT (0.9), OCR_FUSION_WEIGHT_TROCR (0.7)

Label matching controls:
- ENABLE_LABEL_ANCHORED_DATES (False) - uses token positions to anchor dates
- LABEL_DATE_PREFER_ANCHORED (True) - prefer anchored dates over regex
- LABEL_DATE_MAX_Y_GAP_PX (24), LABEL_DATE_MAX_X_DIST_PX (420), LABEL_DATE_MIN_CONF (0.6)
- ENABLE_LABEL_ANCHORED_DATES_TEXT (False) - text-based anchor fallback
- LABEL_DATE_TEXT_LOOKAHEAD_LINES (4), LABEL_DATE_TEXT_SCORE (0.45)
- LABEL_MATCH_MODE (rule) - rule, semantic, or hybrid
- ENABLE_LABEL_SEMANTIC_MATCH (False) - enables semantic embeddings
- LABEL_SEMANTIC_MODEL (all-MiniLM-L6-v2) - local embedding model
- LABEL_MATCH_MIN_SCORE (0.65)
- LABEL_MATCH_DEBUG (False)
- LABEL_EMBED_PROVIDER (local) - local or anthropic
- LABEL_EMBED_MODEL (all-MiniLM-L6-v2)
- LABEL_EMBED_API_KEY, LABEL_EMBED_API_URL, LABEL_EMBED_API_VERSION, LABEL_EMBED_TIMEOUT_S
- LABEL_EMBED_CACHE_SIZE (256)

### Footer total extraction
- ENABLE_FOOTER_TOTAL_EXTRACT (False) - targeted OCR in bottom-right
- FOOTER_REGION_Y_MIN (0.7), FOOTER_REGION_X_MIN (0.55)
- FOOTER_TOTAL_REQUIRE_DECIMAL (True)
- FOOTER_TOTAL_SUPERRES_SCALE (2.0)
- FOOTER_TOTAL_WHITELIST (0123456789.,$)
- TOTAL_PREFER_FOOTER (True), TOTAL_FOOTER_MIN_CONF (60.0)
- STORE_TOTAL_DEBUG (False) - adds footer debug data to extracted_data

### Line item parsing
- ENABLE_LINE_ITEM_PARSER (True) - parse table rows from OCR tokens
- ENABLE_AMOUNT_COLUMN_REOCR (True) - re-OCR amount column
- ENABLE_SUPERRES_CROPS (True) - super-res crops before re-OCR
- LINEITEM_REQUIRE_HEADER (True) - skip if header not detected
- LINEITEM_MIN_VALID_ROWS (2)
- LINEITEM_REQUIRE_DECIMAL (True)
- LINEITEM_ALLOW_NO_DECIMAL_WITH_CURRENCY (True)
- LINEITEM_SKIP_NONE_AMOUNT (True)
- LINEITEM_MERGE_MULTILINE (True)
- LINEITEM_MERGE_MAX_GAP_PX (12)
- LINEITEM_MERGE_REQUIRE_AMOUNT (True)
- LINEITEM_REOCR_MIN_CONF (0.6)
- LINEITEM_SUPERRES_MIN_CONF (0.5)
- LINEITEM_SUPERRES_SCALE (2.0)
- LINEITEM_SUPERRES_METHOD (opencv)
- STORE_LINEITEM_DEBUG (False)

### Logging and placeholders
- LOG_LEVEL (INFO), LOG_FILE (./logs/app.log)
- PROCESSING_TIMEOUT (300) and CONFIDENCE_THRESHOLD (85) exist in config but are not enforced in code

### Bash commands (VS Code on Windows)
Use these in a bash terminal (Git Bash or WSL). They set environment variables for the current shell.

Load .env into the current shell:
```
set -a
source .env
set +a
```

Enable/disable common flags (session-only):
```
export ENABLE_ADVANCED_OCR_PIPELINE=true
export PRE_OCR_GENERATE_VARIANTS=true
export ENABLE_OCR_MATRIX=true
export ENABLE_OCR_FUSION=true
export ENABLE_TEMPLATE_VOTER=true
export STORE_OCR_TOKENS=true
export STORE_OCR_TEXTS=true
export ENABLE_FOOTER_TOTAL_EXTRACT=true
export ENABLE_LINE_ITEM_PARSER=true
```

Disable the same flags:
```
export ENABLE_ADVANCED_OCR_PIPELINE=false
export PRE_OCR_GENERATE_VARIANTS=false
export ENABLE_OCR_MATRIX=false
export ENABLE_OCR_FUSION=false
export ENABLE_TEMPLATE_VOTER=false
export STORE_OCR_TOKENS=false
export STORE_OCR_TEXTS=false
export ENABLE_FOOTER_TOTAL_EXTRACT=false
export ENABLE_LINE_ITEM_PARSER=false
```

Flags read via os.getenv (expect 0/1):
```
export USE_TESSERACT_OCR=1
export USE_TESSERACT_OCR_VOTER=1
```

Disable those:
```
export USE_TESSERACT_OCR=0
export USE_TESSERACT_OCR_VOTER=0
```

Run the app with inline flags (one-off):
```
ENABLE_ADVANCED_OCR_PIPELINE=true ENABLE_OCR_MATRIX=true ENABLE_OCR_FUSION=true \
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Unset a flag (fallback to .env or defaults):
```
unset ENABLE_ADVANCED_OCR_PIPELINE
```

## Libraries and tools (what, why, where, versions)

Versions listed below come from `requirements.txt` (some are minimums, shown with >=).

Platform and server:
- Python 3.12+ - runtime requirement
- fastapi==0.109.0 - REST API framework; routes, dependency injection, OpenAPI docs
- uvicorn[standard]==0.27.0 - ASGI server; runs the FastAPI app in `run.py`
- python-multipart==0.0.6 - parses multipart form uploads for `/invoices/upload`

Database:
- sqlalchemy==2.0.25 - ORM; defines models and provides sessions
- psycopg2-binary==2.9.9 - PostgreSQL driver used by SQLAlchemy
- alembic==1.13.1 - migrations tooling (not used by default; schema upgrades run via `app/db/bootstrap.py`)

Config and validation:
- pydantic>=2.7.0 - schema validation for request/response models
- pydantic-settings>=2.3.0 - loads .env into `Settings` (`app/config.py`)
- python-dotenv==1.0.0 - local .env loading
- email-validator==2.1.0 - not used directly in current endpoints

Core ML and transformers:
- torch>=2.0.0, torchvision>=0.15.0 - model runtime for all DL models
- transformers>=4.47.0 - loads Impira, LayoutLMv3, Donut, TrOCR models
- timm==0.9.12 - vision backbones used by transformer models
- sentencepiece>=0.2.0 - tokenizer dependency for some model families
- accelerate>=0.20.0 - optional device placement/acceleration helpers
- protobuf==4.25.1, huggingface-hub>=0.16.4 - model configs and download cache

OCR and image processing:
- pytesseract==0.3.10 - calls the Tesseract binary and returns text + token boxes
- pillow>=10.0.0 - image IO, crop, resize, format conversion
- opencv-python>=4.8.0 - preprocessing (deskew, CLAHE, denoise, scaling)
- paddleocr>=2.7.0, paddlepaddle>=2.6.0 - OCR detection+recognition in the matrix runner
- scikit-image>=0.21.0 - not referenced directly in code; kept for image processing experiments

Document and table handling:
- PyMuPDF==1.26.7 - renders PDF pages into images for OCR
- pandas>=2.0.0, openpyxl==3.1.5 - read Excel/CSV into dataframes

Docling (structure-aware PDF extraction):
- docling>=1.16.0, docling-core>=2.0.0, docling-ibm-models>=2.0.0 - converts PDF to structured layout + tables

Label semantics:
- sentence-transformers==2.7.0 - embeddings for semantic label matching

Utilities:
- numpy>=1.24.0,<2.0 - arrays and numeric ops in pre-OCR and OCR matrix
- scipy>=1.11.0 - not referenced directly; common numeric helper dependency
- python-dateutil>=2.8.0, pytz>=2021.3 - not referenced directly; pulled by pandas
- langdetect>=1.0.9 - not referenced directly; reserved for language heuristics

Testing:
- pytest==7.4.3, pytest-asyncio==0.21.1, httpx==0.25.2 - test runner and HTTP client

Optional runtime extras (not pinned in requirements.txt):
- rapidocr (no pinned version) - default OCR text engine in triple hybrid; falls back to Tesseract if missing
  - install: `pip install rapidocr`
- Tesseract OCR (system install, version varies) - OCR engine used by pytesseract
- PostgreSQL 12+ (system install) - database server

Model artifacts (Hugging Face):
- impira/layoutlm-document-qa - Q&A extraction over invoice images
- microsoft/layoutlmv3-base - OCR + layout token classification
- naver-clova-ix/donut-base-finetuned-cord-v2 - end-to-end document parsing
- microsoft/trocr-base-printed - OCR matrix text extraction
- all-MiniLM-L6-v2 - label embedding model for semantic matching

## Research papers and references

This section maps the models, methods, and OCR techniques used in this repository to their primary papers.

Core document extraction and OCR models used in code:
- Docling (used by `app/services/docling_service.py`): Docling Technical Report
  - https://arxiv.org/abs/2408.09869
- DocLayNet (layout model family used by Docling): DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis
  - https://arxiv.org/abs/2206.01062
- TableFormer (table-structure model family used by Docling): TableFormer: Table Structure Understanding with Transformers
  - https://arxiv.org/abs/2203.01017
- LayoutLMv3 (used by `microsoft/layoutlmv3-base`): LayoutLMv3: Pre-training for Document AI with Unified Text and Image Masking
  - https://arxiv.org/abs/2204.08387
- Impira LayoutLM document QA checkpoint (`impira/layoutlm-document-qa`):
  - Model card: https://huggingface.co/impira/layoutlm-document-qa
  - Base paper (LayoutLM): LayoutLM: Pre-training of Text and Layout for Document Image Understanding
  - https://arxiv.org/abs/1912.13318  cat summary.md
- Donut (used by `naver-clova-ix/donut-base-finetuned-cord-v2`): OCR-free Document Understanding Transformer
  - https://arxiv.org/abs/2111.15664
- TrOCR (used by `microsoft/trocr-base-printed`): TrOCR: Transformer-based Optical Character Recognition with Pre-trained Models
  - https://arxiv.org/abs/2109.10282
- PaddleOCR/PP-OCR (used in OCR matrix): PP-OCR: A Practical Ultra Lightweight OCR System
  - https://arxiv.org/abs/2009.09941
- Tesseract OCR (used via `pytesseract`): An Overview of the Tesseract OCR Engine
  - https://research.google/pubs/an-overview-of-the-tesseract-ocr-engine/

Semantic label matching embeddings:
- Sentence-BERT (used by `sentence-transformers` style embedding flow): Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks
  - https://arxiv.org/abs/1908.10084
- MiniLM (base family behind `all-MiniLM-L6-v2`): MiniLM: Deep Self-Attention Distillation for Task-Agnostic Compression of Pre-Trained Transformers
  - https://www.microsoft.com/en-us/research/publication/minilm-deep-self-attention-distillation-for-task-agnostic-compression-of-pre-trained-transformers/
- MiniLMv2 (related distillation line): MiniLMv2: Multi-Head Self-Attention Relation Distillation for Compressing Pretrained Transformers
  - https://aclanthology.org/2021.findings-acl.188/

Image preprocessing techniques used in advanced OCR path:
- Otsu thresholding (used via OpenCV thresholding in pre-OCR and footer extraction):
  - N. Otsu, "A Threshold Selection Method from Gray-Level Histograms" (1979)
  - https://doi.org/10.1109/TSMC.1979.4310076
- CLAHE (used via OpenCV `createCLAHE`):
  - K. Zuiderveld, "Contrast Limited Adaptive Histogram Equalization" (1994)
  - https://doi.org/10.1016/B978-0-12-336156-1.50061-6

Notes:
- `rapidocr` is used as an OCR runtime fallback in this project; it is primarily an implementation or project dependency rather than a single canonical research paper.
- `consensus_voting`, template voter logic, OCR fusion rules, and line-item heuristics in this repository are custom engineering logic built on top of the above published methods.

## Tradeoffs and design choices

- Quadruple hybrid accuracy vs latency: running Docling + 3 models improves recall but increases CPU/GPU time and memory usage.
- Docling requires the original PDF: image-only uploads skip Docling and run the 3-model path.
- Pre-OCR pipeline improves low-quality scans but adds OpenCV dependency, extra compute, and temporary files.
- OCR matrix + fusion boosts label accuracy, but requires heavy dependencies (PaddleOCR, TrOCR) and more runtime.
- Template voter and bbox override can improve known vendors, but stale templates can overfit if not refreshed.
- Storing OCR tokens/texts helps explainability and correction anchoring, but increases DB size.
- BackgroundTasks are simple but run inside the web worker; high throughput should move processing to a queue worker.
- Multi-page PDFs are merged only when invoice numbers match; mixed invoices return page 1 with _other_pages metadata.

## Commands

Install and run:
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Alternative server run:
```
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Prefetch models (optional):
```
python download_impira.py
python download_layoutlm.py
python download_donut.py
```

Test scripts (manual):
```
python test_all_documents.py
python test_comprehensive.py
python test_vendor_recognition.py
python test_template_learning.py
```

## Troubleshooting

- Tesseract not found: set TESSERACT_PATH or add tesseract to PATH.
- Model downloads are large: first run pulls models from Hugging Face into the local cache.
- Low accuracy on scans: enable ENABLE_ADVANCED_OCR_PIPELINE and PRE_OCR_GENERATE_VARIANTS, then try OCR matrix and fusion.

## Deployment

See DEPLOYMENT.md and DEPLOYMENT_GUIDE.md for production details.
