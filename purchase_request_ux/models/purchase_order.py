from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _purchase_request_confirm_message(self):
        """Calling super running parent logic but force mt_comment instead of mt_note subtype for message posting."""
        return super(
            PurchaseOrder, self.with_context(force_subtype_id="mail.mt_comment")
        )._purchase_request_confirm_message()
