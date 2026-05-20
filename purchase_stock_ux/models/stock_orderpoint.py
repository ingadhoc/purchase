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
        product = self.env["product.product"].browse(product)
        location = self.env["stock.location"].browse(location)
        seller = product.with_company(location.company_id)._select_seller()
        if seller:
            values["supplier_id"] = seller.id
        return values
