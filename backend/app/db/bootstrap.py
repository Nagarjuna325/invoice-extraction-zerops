"""
Lightweight, idempotent schema upgrades for deployments that rely on
Base.metadata.create_all but still need incremental columns/tables.
"""
from sqlalchemy import text
from sqlalchemy.engine import Engine


def apply_schema_upgrades(engine: Engine) -> None:
    """Ensure new tables/columns exist without dropping anything."""
    with engine.begin() as conn:
        # New columns on invoices
        conn.execute(
            text(
                """
                ALTER TABLE invoices
                ADD COLUMN IF NOT EXISTS ground_truth_locked BOOLEAN DEFAULT FALSE;
                """
            )
        )
        conn.execute(
            text(
                """
                ALTER TABLE invoices
                ADD COLUMN IF NOT EXISTS validation_metadata JSONB DEFAULT '{}'::jsonb;
                """
            )
        )
        conn.execute(
            text(
                """
                ALTER TABLE invoices
                ADD COLUMN IF NOT EXISTS ocr_tokens JSONB DEFAULT '{}'::jsonb;
                """
            )
        )

        # New columns on vendors
        conn.execute(
            text(
                """
                ALTER TABLE vendors
                ADD COLUMN IF NOT EXISTS template_version INTEGER DEFAULT 0;
                """
            )
        )
        conn.execute(
            text(
                """
                ALTER TABLE vendors
                ADD COLUMN IF NOT EXISTS last_template_applied_at TIMESTAMPTZ NULL;
                """
            )
        )

        # New corrections table (stores human/auto corrections for learning)
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS corrections (
                    id SERIAL PRIMARY KEY,
                    invoice_id UUID NULL REFERENCES invoices(id) ON DELETE SET NULL,
                    upload_id VARCHAR(100),
                    vendor_id INTEGER REFERENCES vendors(id) ON DELETE SET NULL,
                    field_name VARCHAR(100) NOT NULL,
                    corrected_value JSONB,
                    page_number INTEGER,
                    bbox JSONB,
                    source VARCHAR(50),
                    correction_reason TEXT,
                    reviewer VARCHAR(100),
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
        )
