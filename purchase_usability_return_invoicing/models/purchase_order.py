# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    with_returns = fields.Boolean(
        compute='_compute_with_returns',
        store=True,
    )

    @api.multi
    @api.depends('order_line.qty_returned')
    def _compute_with_returns(self):
        for order in self:
            if any(line.qty_returned for line in order.order_line):
                order.with_returns = True
            else:
                order.with_returns = False
