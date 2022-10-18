##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, _
from ast import literal_eval


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def add_products_to_quotation(self):
        """ In order to filter the products of the partner the "product supplier
        search" module need to be installed
        """
        self.ensure_one()
        action_read = False
        actions = self.env.ref(
            'product.product_normal_action_sell')
        if actions:
            action_read = actions.sudo().read()[0]
            context = literal_eval(action_read['context'])
            if 'search_default_filter_to_sell' in context:
                context.pop('search_default_filter_to_sell')
            context.update(dict(
                search_default_filter_to_purchase=True,
                search_default_seller_ids=self.partner_id.name,
                purchase_quotation_products=True,
                # we send company in context so it filters taxes
                company_id=self.company_id.id,
                # pricelist=self.pricelist_id.display_name,
                partner_id=self.partner_id.id,
            ))
            action_read.update(dict(
                context=context,
                name=_('Quotation Products'),
                display_name=_('Quotation Products'),
            ))
        return action_read

    def add_products(self, product, qty):
        """This method create line in cache to prepare the order line that
        it's added to purchase order
        """
        self.ensure_one()
        vals = {
            'order_id': self.id,
            'product_id': product.id or False,
            'partner_id': self.partner_id.id,
        }
        purchase_line = self.env['purchase.order.line'].new(vals)
        purchase_line.onchange_product_id()
        # we set qty (if we set it on create odoo overwrite it to 1)
        purchase_line.product_qty = qty
        purchase_line._onchange_quantity()
        vals = purchase_line._convert_to_write(purchase_line._cache)
        self.env['purchase.order.line'].create(vals)
