import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Create and populate invoice_company_id for existing purchase order types.

    This migration creates the invoice_company_id column and populates it for
    existing purchase order types to avoid a full recomputation on large databases.

    The value is copied from company_id, which matches the compute logic.
    """
    _logger.info("Creating and populating invoice_company_id on purchase_order_type")

    # Check if the column already exists.
    cr.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'purchase_order_type'
          AND column_name = 'invoice_company_id'
          AND table_schema = current_schema()
        """
    )

    if not cr.fetchone():
        _logger.info("Creating invoice_company_id column")
        cr.execute(
            """
            ALTER TABLE purchase_order_type
            ADD COLUMN invoice_company_id INTEGER
            REFERENCES res_company(id) ON DELETE SET NULL
            """
        )
    else:
        _logger.info("Column invoice_company_id already exists, skipping creation")

    # Populate only missing values from company_id (same logic as compute method).
    cr.execute(
        """
        UPDATE purchase_order_type pot
        SET invoice_company_id = aj.company_id
        FROM account_journal aj
        WHERE aj.id = pot.journal_id
        AND pot.invoice_company_id IS NULL
        AND pot.journal_id IS NOT NULL
        """
    )

    rows_updated = cr.rowcount
    _logger.info("Updated %s purchase order types with invoice company", rows_updated)
