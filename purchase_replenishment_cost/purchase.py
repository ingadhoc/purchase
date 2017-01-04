# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        res = super(PurchaseOrderLine, self)._onchange_quantity()
        if not self.product_id:
            return

        seller = self.product_id._select_seller(
            self.product_id,
            partner_id=self.partner_id,
            quantity=self.product_qty,
            date=self.order_id.date_order and self.order_id.date_order[:10],
            uom_id=self.product_uom)
        if not seller:
            price_unit = self.product_id.replenishment_cost
            if (
                    price_unit and
                    self.order_id.currency_id != self.product_id.currency_id):
                price_unit = self.product_id.currency_id.compute(
                    price_unit, self.order_id.currency_id)
            if (
                    price_unit and self.product_uom and
                    self.product_id.uom_id != self.product_uom):
                price_unit = self.env['product.uom']._compute_price(
                    self.product_id.uom_id.id, price_unit,
                    to_uom_id=self.product_uom.id)
            self.price_unit = price_unit
        return res
