# -*- encoding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api


class purchase_order(models.Model):
    _inherit = 'purchase.order'

    @api.one
    def update_prices(self):
        # for line in self.order_line:
        #     price = self.pricelist_id.with_context(
        #         uom=line.product_uom.id,
        #         date=self.date_order).price_get(
        #             line.product_id.id,
        #             line.product_qty or 1.0,
        #             self.partner_id.id)[self.pricelist_id.id]
        #     line.price_unit = price

        for line in self.order_line:
            price = line.product_id.price
            item = line.product_id.item_ids.search(['&',
                                                    ('date_start', '<=', self.date_order),
                                                    ('date_end', '>=', self.date_order)])
            if item:
                price = item[0].fixed_price
            line.price_unit = price
        return True
