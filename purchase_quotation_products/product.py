# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


class product_product(models.Model):
    _inherit = "product.product"

    @api.one
    def _get_qty_purchase(self):
        self.qty_purchase = 0
        purchase_order_id = self._context.get('active_id', False)
        if purchase_order_id:
            lines = self.env['purchase.order.line'].search([
                ('order_id', '=', purchase_order_id),
                ('product_id', '=', self.id)])
            self.qty_purchase = \
                sum([self.env['product.uom']._compute_qty_obj(
                    line.product_uom,
                    line.product_qty,
                    self.uom_po_id) for line in lines])

    @api.one
    def _set_qty_purchase(self):
        purchase_order_id = self._context.get('active_id', False)
        qty = self.qty_purchase
        if purchase_order_id:
            lines = self.env['purchase.order.line'].search([
                ('order_id', '=', purchase_order_id),
                ('product_id', '=', self.id)])
            if lines:
                (lines - lines[0]).unlink()
                lines[0].product_qty = qty
                lines[0]._onchange_quantity()
            else:
                self.env['purchase.order'].browse(
                    purchase_order_id).add_products(self, qty)

    qty_purchase = fields.Integer(
        string='Quantity',
        compute='_get_qty_purchase',
        inverse='_set_qty_purchase')
