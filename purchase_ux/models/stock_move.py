##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    purchase_id = fields.Many2one(
        related='purchase_line_id.order_id',
    )
