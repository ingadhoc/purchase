##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_stock_moves(self, picking):
        res = super()._prepare_stock_moves(picking)
        for rec in res:
            rec['analytic_tag_ids'] = [(6, 0, self.analytic_tag_ids.ids)]
        return res
