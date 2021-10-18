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
            account_analytic = self.account_analytic_id
            analytic_tags = self.analytic_tag_ids
            if account_analytic:
                rec['analytic_account_id'] = account_analytic.id
            if analytic_tags:
                rec['analytic_tag_ids'] = [(6, 0, self.analytic_tag_ids.ids)]
        return res
