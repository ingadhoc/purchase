# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, _
from ast import literal_eval


class purchase_order(models.Model):
    _inherit = "purchase.order"

    @api.multi
    def add_products_to_quotation(self):
        self.ensure_one()
        action_read = False
        actions = self.env.ref(
            'product.product_normal_action_sell')
        if actions:
            action_read = actions.read()[0]
            context = literal_eval(action_read['context'])
            if 'search_default_filter_to_sell' in context:
                context.pop('search_default_filter_to_sell')
            context['search_default_filter_to_purchase'] = True
            # para que este funcione requiere modulo product_supplier_search
            context['search_default_seller_ids'] = self.partner_id.name
            # {"search_default_filter_to_sell":1}
            context['purchase_quotation_products'] = True
            # context['pricelist'] = self.pricelist_id.display_name
            # we send company in context so it filters taxes
            context['company_id'] = self.company_id.id
            context['partner_id'] = self.partner_id.id
            action_read['context'] = context
            # action_read['view_mode'] = 'tree,form'
            action_read['name'] = _('Quotation Products')
        return action_read

    @api.multi
    def add_products(self, product, qty):
        self.ensure_one()
        vals = {
            'order_id': self.id,
            'product_id': product.id or False,
        }
        # we create line in cache
        purchase_line = self.env['purchase.order.line'].new(vals)
        # we call onchange product to get required fields
        purchase_line.onchange_product_id()
        # we set qty (if we set it on create odoo overwrite it to 1)
        purchase_line.product_qty = qty
        # we call onchange qty)
        purchase_line._onchange_quantity()
        # we convert to write
        vals = purchase_line._convert_to_write(purchase_line._cache)
        self.env['purchase.order.line'].create(vals)
