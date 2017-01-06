# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    merge_incoming_picking = fields.Boolean(
        help='If set true, when confirming a purchase order, if an open '
        'picking exists for same partner and picking type, incoming moves will'
        'be merged into that picking'
    )
