# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, _, SUPERUSER_ID
from ast import literal_eval
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class purchase_order(models.Model):
    _inherit = "purchase.order"

    @api.multi
    def add_products_to_quotation(self):
        self.ensure_one()
        action_read = False
        view_id = self.env['ir.model.data'].xmlid_to_res_id(
            'purchase_quotation_products.product_product_tree_view')
        search_view_id = self.env['ir.model.data'].xmlid_to_res_id(
            'purchase_quotation_products.product_product_search_view')
        actions = self.env.ref(
            'product.product_normal_action_sell')
        if actions:
            action_read = actions.read()[0]
            context = literal_eval(action_read['context'])
            # context['pricelist'] = self.pricelist_id.display_name
            # we send company in context so it filters taxes
            context['company_id'] = self.company_id.id
            action_read['context'] = context
            # this search view removes pricelist
            action_read.pop("search_view", None)
            action_read['search_view_id'] = (search_view_id, False)
            action_read['view_mode'] = 'tree,form'
            action_read['views'] = [
                (view_id, 'tree'), (False, 'form')]
            action_read['name'] = _('Quotation Products')
        return action_read

    @api.multi
    def add_products(self, product_ids, qty, uom):
        self.ensure_one()
        for product in self.env['product.product'].browse(
                product_ids):
            line_data = self.env['purchase.order.line'].\
                onchange_product_quotation(product, 1,  self)
            val = {
                'name': line_data['name'],
                'date_planned': line_data['date_planned'],
                'product_qty': qty,
                'order_id': self.id,
                'product_id': product.id or False,
                'product_uom': line_data['product_uom'].id,
                'price_unit': line_data['price_unit'],
                'taxes_id': [(6, 0, line_data['taxes_id'])],
            }

            self.env['purchase.order.line'].create(val)


class purchase_order_line(models.Model):
    _inherit = "purchase.order.line"

    def onchange_product_quotation(
            self,
            product_id,
            product_qty,
            order_id):
        result = {}
        if not product_id:
            return result

        # Reset date, price and quantity since
        #  _onchange_quantity will provide default values
        result['date_planned'] = \
            datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        result['price_unit'] = product_qty = 0.0
        result['product_uom'] = \
            product_id.uom_po_id or product_id.uom_id
        result['domain'] = \
            {'product_uom': [('category_id',
                              '=',
                              product_id.uom_id.category_id.id)]}

        product_lang = product_id.with_context({
            'lang': self.partner_id.lang,
            'partner_id': self.partner_id.id,
        })
        result['name'] = product_lang.display_name
        if product_lang.description_purchase:
            result['name'] += '\n' + product_lang.description_purchase

        fpos = order_id.fiscal_position_id
        if self.env.uid == SUPERUSER_ID:
            company_id = self.env.user.company_id.id
            result['taxes_id'] = fpos.map_tax(
                product_id.supplier_taxes_id.filtered(
                    lambda r: r.company_id.id == company_id))
        else:
            result['taxes_id'] = fpos.map_tax(
                product_id.supplier_taxes_id)

        self._suggest_quantity()
        self._onchange_quantity()

        return result
