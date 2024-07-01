##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class PurchaseOrderLine(models.Model):

    _inherit = 'purchase.order.line'

    number = fields.Integer(
        compute='_compute_get_number',
    )

    def _compute_get_number(self):
        self.number = False
        if self and not isinstance(self[0].id, int):
            return
        for order in self.mapped('order_id'):
            number = 1
            for line in order.order_line.sorted("sequence"):
                line.number = number
                number += 1

