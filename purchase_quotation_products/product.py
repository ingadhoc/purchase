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
            self.qty_purchase = sum([self.env['product.uom']._compute_qty_obj(
                line.product_uom,
                line.product_qty,
                self.uom_id) for line in lines])

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
                line_data = self.env[
                    'purchase.order.line'].onchange_product_id(
                        lines[0].order_id.pricelist_id.id,
                        self.id,
                        qty=qty,
                        uom_id=self.uom_id.id,
                        partner_id=lines[0].order_id.partner_id.id)
                lines[0].write({
                    'product_qty': qty,
                    'product_uom': self.uom_id.id,
                    'price_unit': line_data['value'].get('price_unit')
                })
            else:
                self.env['purchase.order'].browse(
                    purchase_order_id).add_products(
                        self.id, qty, self.uom_id.id)

    qty_purchase = fields.Integer(
        # TODO poner en ingles cuando el bug de odoo este resuelto
        'Cantidad',
        compute='_get_qty_purchase',
        inverse='_set_qty_purchase')
