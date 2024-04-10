##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    @api.model
    def _get_orderpoint_values(self, product, location):
        values = super()._get_orderpoint_values(product, location)
        product = self.env['product.product'].browse(product)
        if product.seller_ids:
            values['supplier_id'] = product.seller_ids[0].id
        return values

