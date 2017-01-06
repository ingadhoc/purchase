# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    purchase_ids = fields.Many2many(
        'purchase.order',
        # related='move_lines.purchase_line_id.order_id',
        compute='_compute_purchase_ids',
        string="Purchase Orders",
        readonly=True,
    )

    @api.multi
    @api.depends('move_lines.purchase_line_id.order_id')
    def _compute_purchase_ids(self):
        for rec in self:
            rec.purchase_ids = self.move_lines.mapped(
                'purchase_line_id.order_id')
