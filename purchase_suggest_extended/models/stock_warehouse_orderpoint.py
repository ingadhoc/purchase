# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from openerp import models, fields, api
from datetime import timedelta, datetime
import openerp.addons.decimal_precision as dp
# from openerp.tools import float_compare, float_is_zero
# from openerp.exceptions import UserError
import logging

logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    rotation = fields.Float(
        help='Sum of invoiced quantity on las 30 days, converted to product '
        'uom',
        compute='_compute_rotation',
        digits=dp.get_precision('Product Unit of Measure'),
    )

    @api.multi
    @api.depends('product_id')
    def _compute_rotation(self):
        for rec in self:
            if not rec.product_uom:
                continue
            date_invoice = fields.Datetime.to_string(
                datetime.now() + timedelta(-30))
            rec.rotation = sum(rec.env['account.invoice.line'].search([
                ('product_id', '=', rec.product_id.id),
                ('invoice_id.date_invoice', '>=', date_invoice),
                ('invoice_id.state', 'not in', ['draft', 'cancel']),
            ]).mapped(
                lambda x: x.uom_id and rec.env['product.uom']._compute_qty_obj(
                    x.uom_id, x.quantity, rec.product_uom) or 0.0))
