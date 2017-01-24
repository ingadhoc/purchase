# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
# from openerp.tools import float_compare, float_is_zero
# from openerp.exceptions import UserError
import logging

logger = logging.getLogger(__name__)


class PurchaseSuggest(models.TransientModel):
    _inherit = 'purchase.suggest'

    replenishment_cost = fields.Float(
        related='product_id.replenishment_cost',
        store=True,
    )
    order_amount = fields.Monetary(
        string='Order Amount',
        compute='_compute_order_amount',
        store=True,
    )
    currency_id = fields.Many2one(
        related='product_id.currency_id',
        store=True,
    )
    virtual_available = fields.Float(
        string='Forecasted Quantity',
        compute='_compute_virtual_available',
        store=True,
        digits=dp.get_precision('Product Unit of Measure'),
        help="in the unit of measure of the product"
    )
    rotation = fields.Float(
        related='orderpoint_id.rotation',
        store=True,
    )

    @api.multi
    @api.depends('qty_to_order', 'replenishment_cost')
    def _compute_order_amount(self):
        for rec in self:
            rec.order_amount = rec.replenishment_cost * rec.qty_to_order

    @api.multi
    @api.depends(
        'qty_available',
        'outgoing_qty',
        'incoming_qty',
        'draft_po_qty',
    )
    def _compute_virtual_available(self):
        for rec in self:
            rec.qty_available = rec.qty_available - rec.outgoing_qty \
                + rec.incoming_qty + rec.draft_po_qty
