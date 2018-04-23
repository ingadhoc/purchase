# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from openerp import models, api


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def _prepare_purchase_order_line(self, po, supplier):
        self.ensure_one()
        res = super(ProcurementOrder, self)._prepare_purchase_order_line(
            po=po, supplier=supplier)
        # if price was not computed (not seller or seller price = 0.0), then
        # use standar price
        if not res['price_unit']:
            price_unit = self.product_id.standard_price
            if (
                    price_unit and
                    po.currency_id != self.product_id.currency_id):
                price_unit = self.product_id.currency_id.compute(
                    price_unit, po.currency_id)
            if (
                    price_unit and res['product_uom'] and
                    self.product_id.uom_id.id != res['product_uom']):
                price_unit = self.env['product.uom']._compute_price(
                    self.product_id.uom_id.id, price_unit,
                    to_uom_id=res['product_uom'])
            res['price_unit'] = price_unit
        return res
