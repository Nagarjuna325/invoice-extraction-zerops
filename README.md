# Invoice Extraction

Upload an invoice — PDF, scan, photo, Excel or CSV — and get structured data back:
invoice number, dates, vendor, totals, line items. Each field carries a confidence
score, and every number is cross-checked before it is returned.

Four document-understanding models read each page independently and vote. Where they
disagree, the disagreement is visible in the response rather than hidden behind a
single guess.

**Live:** https://api-2ea1-8000.prg1.zerops.app
**API docs:** https://api-2ea1-8000.prg1.zerops.app/api/docs

---

## Why four models

Single-model invoice extraction fails in predictable ways. Layout-aware models lose
track of which total belongs to which table. OCR-free models hallucinate plausible
numbers. Structure-aware parsers do well on digital PDFs and poorly on phone photos.

Running four and comparing them turns those individual failure modes into a signal:

| Model | What it contributes |
| --- | --- |
| **Docling** (IBM) | Structure-aware PDF parsing — layout regions and table structure |
| **Impira LayoutLM** | Document question-answering over the page image |
| **LayoutLMv3** (Microsoft) | Token classification over combined layout + OCR |
| **Donut** (Naver Clova) | OCR-free end-to-end parsing |

A consensus layer normalises each model's answer per field, weights the votes by
confidence, and records the agreement level — unanimous, strong, moderate, weak, or
conflict. Fields where the models disagree get flagged for review instead of being
silently resolved.

## What happens to an upload

```
POST /api/v1/invoices/upload
        │
        ├── file saved, invoice row created (status=UPLOADED)
        │
        ▼
   background extraction
        │
        ├── Excel / CSV ──────────────► structured parse (no ML needed)
        │
        └── PDF / image
                ├── pre-OCR: DPI normalisation, deskew, contrast
                ├── four models extract independently
                ├── consensus merge + confidence calibration
                ├── validation: totals, dates, currency, cross-field checks
                └── vendor recognition + template learning
        │
        ▼
   status=EXTRACTED, results in Postgres
```

The client polls `GET /api/v1/invoices/{upload_id}/status`, then fetches the result.

### Validation is not an afterthought

Extraction produces candidates; validation decides what ships. It repairs impossible
dates, normalises US vs EU decimal formats (`1,234.56` vs `1.234,56`), infers missing
currency, checks that line items actually sum to the stated total, and distinguishes
vendor from customer. Anything it cannot reconcile becomes a warning on the response
with `needs_review` set.

### It learns from corrections

`POST /api/v1/invoices/correct` records a fix against the vendor. The next invoice
from that vendor uses the correction as an additional voter, with bounding-box
anchoring where the coordinates are known. Accuracy on repeat vendors improves without
retraining anything.

---

## How Zerops is used

The interesting part of this project was never the models — it was that a
five-model pipeline with a 6 GB memory footprint had only ever run on a laptop.
Zerops is what made it a URL.

**Three services on one private network:**

| Service | Type | Role |
| --- | --- | --- |
| `api` | Python 3.12 runtime | FastAPI + the full model pipeline |
| `db` | PostgreSQL 16 (managed) | invoices, vendors, corrections |
| `app` | static | React 19 + Vite frontend |

**What the platform does that mattered here:**

- **Managed Postgres, zero setup.** `db` is provisioned by the platform. The API
  reaches it over the project's private network — no public exposure, no connection
  string to manage by hand. Credentials are injected as service variables and composed
  in [`zerops.yml`](zerops.yml):
  ```yaml
  DATABASE_URL: postgresql://${db_user}:${db_password}@${db_hostname}:${db_port}/${db_dbName}
  ```
  The schema builds itself on first boot via `app/db/bootstrap.py`.

- **A build container that isn't the runtime container.** The build installs
  CPU-only torch, apt-installs Tesseract and the OpenCV system libraries, and
  **bakes all four models into the deploy artifact**. Without that, every cold
  start would stall on a ~4 GB HuggingFace download before serving a request.
  The runtime image ships with `HF_HUB_OFFLINE=1`.

- **Cross-service variable references.** The frontend's API base URL is
  `${api_zeropsSubdomain}` — resolved at build time, so nothing is hardcoded and
  the two services stay decoupled.

- **Vertical autoscaling.** RAM and disk ranges are set per service, which matters
  when four transformer models are resident simultaneously.

- **`zcli push --no-git`.** Deploys straight from a working directory. This turned
  out to matter: the git-based pipeline hit a DNS resolution failure inside the build
  network, and having a second, fully-supported deploy path meant it was a detour
  rather than a dead end.

Everything about how this is built, deployed and run lives in one file —
[`zerops.yml`](zerops.yml).

---

## Stack

**Backend** — FastAPI, SQLAlchemy, PostgreSQL 16, PyMuPDF, OpenCV, Tesseract,
RapidOCR, PaddleOCR, transformers, torch (CPU), Docling

**Frontend** — React 19, Vite, MUI, Redux Toolkit

**Platform** — Zerops

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/invoices/upload` | upload a document |
| `GET` | `/api/v1/invoices/{upload_id}/status` | poll progress |
| `GET` | `/api/v1/invoices/{upload_id}` | fetch extracted data |
| `POST` | `/api/v1/invoices/correct` | submit a correction |

```bash
curl -X POST https://<api-subdomain>/api/v1/invoices/upload \
  -F "file=@invoice.pdf"
```

Accepts `.pdf`, `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, `.xlsx`, `.xls`, `.csv`
up to 10 MB.

## Running locally

```bash
cd backend
python -m venv venv && venv\Scripts\activate     # Windows
pip install -r requirements.txt
pip install rapidocr

# needs PostgreSQL and Tesseract installed
echo DATABASE_URL=postgresql://postgres:PASSWORD@localhost:5432/invoice_extraction > .env
python run.py
```

Deep documentation — every configuration flag, the OCR matrix, template learning
internals, and the research papers behind each model — is in
[backend/README.md](backend/README.md).

## Deploying

```bash
zcli push --no-git --project-id <id> --service-id <id>
```

Or connect the repository in the Zerops GUI and push to `main`.

---

## Notes for reviewers

**Timeline.** The extraction pipeline was built over several months before this
event. What was built during the challenge weekend is the deployment: containerising
a five-model ML stack, wiring managed Postgres over the private network, sizing the
runtime, baking models into the build artifact, and getting the whole thing to a live
URL. The project had never run anywhere but a laptop before this.

**Known limits.**
- Extraction runs in-process via FastAPI `BackgroundTasks`. A container restart
  abandons in-flight jobs. A queue worker is the correct fix and is not done.
- Container RAM is capped at 6 GB on this account, which is tight for four models
  plus the OCR matrix layer.
- Three frontend pages (dashboard, invoice detail, review) are unimplemented. Upload
  and the API are complete.

**AI assistance.** Claude Code was used for deployment configuration, debugging, and
documentation. Model selection, the consensus and validation logic, and the
architecture are the author's own work and predate this event.
