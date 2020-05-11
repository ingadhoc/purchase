##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class PurchaseGlobalDiscountWizard(models.TransientModel):
    _name = "purchase.order.global_discount.wizard"
    _description = "Transient model to apply global discounts on POs"

    amount = fields.Float(
        'Discount',
        required=True,
    )

    def confirm(self):
        self.ensure_one()
        order = self.env['purchase.order'].browse(
            self._context.get('active_id', False))
        order.order_line.write({'discount': self.amount})
        return True
