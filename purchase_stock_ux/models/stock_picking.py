##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.ondelete(at_uninstall=False)
    def _check_block_picking_deletion(self):
        pickings = self
        if self.env.context.get("purchase_drop_empty_receipt"):
            pickings = self.filtered(lambda p: p.state != "draft" or p.move_ids)
        return super(StockPicking, pickings)._check_block_picking_deletion()
