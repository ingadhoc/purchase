# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
from odoo.tools import float_compare
# from ast import literal_eval
# from odoo.exceptions import UserError
import logging

logger = logging.getLogger(__name__)


class PurchaseSuggestGenerate(models.TransientModel):
    _inherit = 'purchase.suggest.generate'

    # Without this module, when we use orderpoints, if there are no orderpoints
    # for a consu product, Odoo will not suggest to re-order it.
    # But, with this module, Odoo will also suggest to re-order the consu
    # products, which may not be what the user wants
    add_products_without_order_point = fields.Boolean(
        help='Sugerir tambien para productos sin punto de pedido, se va a '
        'utilizar cantidad mínima y máxima 0.0. NO se tienen en cuenta '
        'productos consumibles',
        default=True,
    )

    @api.model
    def _prepare_suggest_line(self, product_id, qty_dict):
        sline = super(PurchaseSuggestGenerate, self)._prepare_suggest_line(
            product_id, qty_dict)
        # for thos lines with "add_products_without_order_point" we
        # force user company
        if not sline['company_id']:
            sline['company_id'] = self.env.user.company_id.id

        # use mutliple quantity if set
        op = qty_dict['orderpoint']
        qty = sline['qty_to_order']
        if op:
            reste = op.qty_multiple > 0 and qty % op.qty_multiple or 0.0
            if float_compare(
                    reste, 0.0,
                    precision_rounding=op.product_uom.rounding) > 0:
                qty += op.qty_multiple - reste
                sline['qty_to_order'] = qty
        return sline

    @api.model
    def generate_products_dict(self):
        '''
        inherit the native method to
        '''
        products = super(
            PurchaseSuggestGenerate, self).generate_products_dict()
        product_ids = products.keys()
        product_domain = self._prepare_product_domain()
        # TODO tal vez querramos agregar parametro para setear si solo product
        # o tambien consumibles
        if self.add_products_without_order_point:
            product_domain += [
                ('type', '=', 'product'),
                ('id', 'not in', product_ids)]
            new_products = self.env['product.product'].search(product_domain)
            for product in new_products:
                # We also want the missing product that have min_qty = 0
                # So we remove "if product.z_stock_min > 0"
                products[product.id] = {
                    'min_qty': 0.0,
                    'max_qty': 0.0,
                    'draft_po_qty': 0.0,  # This value is set later on
                    'orderpoint': False,
                    'product': product,
                }
        return products


class PurchaseSuggest(models.TransientModel):
    _inherit = 'purchase.suggest'

    replenishment_cost = fields.Float(
        related='product_id.replenishment_cost',
        store=True,
        readonly=True,
    )
    order_amount = fields.Monetary(
        string='Order Amount',
        compute='_compute_order_amount',
        store=True,
    )
    currency_id = fields.Many2one(
        related='product_id.currency_id',
        store=True,
        readonly=True,
    )
    virtual_available = fields.Float(
        string='Forecasted Quantity',
        compute='_compute_virtual_available',
        store=True,
        digits=dp.get_precision('Product Unit of Measure'),
        # help="in the unit of measure of the product",
        help="Forecast quantity in the unit of measure of the product "
        "(computed as Quantity On Hand - Outgoing + Incoming + Draft PO "
        "quantity)"
    )
    rotation = fields.Float(
        related='orderpoint_id.rotation',
        store=True,
        readonly=True,
    )
    location_rotation = fields.Float(
        related='orderpoint_id.location_rotation',
        store=True,
        readonly=True,
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
            rec.virtual_available = rec.product_id.with_context(
                location=rec.location_id.id
            ).virtual_available
            # + rec.draft_po_qty
            # rec.virtual_available = rec.qty_available - rec.outgoing_qty \
            #     + rec.incoming_qty + rec.draft_po_qty

    @api.multi
    def action_traceability(self):
        self.ensure_one()
        action = self.env.ref('stock.act_product_stock_move_open')
        if action:
            action_read = action.read()[0]
            # nos da error al querer leerlo como dict
            # context = literal_eval(action_read['context'])
            # context['search_default_product_id'] = self.product_id.id
            # context['default_product_id'] = self.product_id.id
            context = {
                'search_default_future': 1,
                'search_default_picking_type': 1,
                'search_default_product_id': self.product_id.id,
                'default_product_id': self.product_id.id}
            action_read['context'] = context
            return action_read
