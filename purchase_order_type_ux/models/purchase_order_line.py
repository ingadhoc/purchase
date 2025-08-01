##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.depends("qty_invoiced", "qty_received", "order_id.state", "qty_returned", "order_id.order_type")
    def _compute_qty_invoiced(self):
        super()._compute_qty_invoiced()
        for line in self:
            if line.order_id.state in ["purchase", "done"] and line.order_id.order_type.purchase_method:
                if line.order_id.order_type.purchase_method == "purchase":
                    line.qty_to_invoice = line.product_qty - line.qty_invoiced - line.qty_returned
                else:
                    line.qty_to_invoice = line.qty_received - line.qty_invoiced
