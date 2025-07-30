from odoo import models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def allocate(self):
        """Calling super running parent logic but force mt_comment instead of mt_note subtype for message posting."""
        return super(StockMoveLine, self.with_context(force_subtype_id="mail.mt_comment")).allocate()
