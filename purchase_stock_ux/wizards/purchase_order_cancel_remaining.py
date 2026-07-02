from odoo import api, fields, models


class PurchaseOrderCancelRemaining(models.TransientModel):
    _name = "purchase.order.cancel.remaining"
    _description = "Purchase Order Cancel Remaining"

    purchase_order_line_ids = fields.Many2many(
        "purchase.order.line", required=True, default=lambda self: self.default_purchase_order_line_ids()
    )

    @api.model
    def default_purchase_order_line_ids(self):
        return self.env["purchase.order"].browse(self.env.context.get("active_ids", [])).mapped("order_line")

    def action_confirm(self):
        self.purchase_order_line_ids.filtered(lambda x: x.receipt_status in ("pending", "partial")).with_context(
            cancel_from_order=True
        ).button_cancel_remaining()
