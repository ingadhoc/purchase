##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, _
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _get_bom_delivered(self, bom=False):
        self.ensure_one()
        if bom and any([move.to_refund for move in self.move_ids]):
            raise UserError(_(
                "You can't return products to refund if they are components of"
                " a product kit. You can return them without 'to refund' "
                "option and make refund manually.\n"
                "* Product kit: '%s'\n"
                "* Components: %s") % (
                    self.product_id.name,
                    ", ".join(self.move_ids.filtered(
                        lambda x: x.to_refund).mapped('product_id.name')),
                    ))
        return super(PurchaseOrderLine, self)._get_bom_delivered(bom=bom)
