# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api
from ast import literal_eval


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def add_purchase_line_moves(self):
        self.ensure_one()
        actions = self.env.ref(
            'purchase_usability.action_purchase_line_tree')
        if actions:
            action_read = actions.read()[0]
            context = literal_eval(action_read['context'])
            context['force_line_edit'] = True
            context['search_default_not_invoiced'] = True
            context['search_default_invoice_qty'] = True
            action_read['context'] = context
            action_read['domain'] = [
                ('partner_id.commercial_partner_id', '=',
                    self.partner_id.commercial_partner_id.id),
            ]
        return action_read

    @api.multi
    def update_purchase_invoice_prices(self):
        for line in self.invoice_line_ids:
            price_unit = line.product_id.standard_price
            if (
                price_unit and
                    self.currency_id != line.product_id.currency_id):
                price_unit = line.product_id.currency_id.compute(
                    price_unit, self.currency_id)
            if (
                    price_unit and line.uom_id and
                    line.product_id.uom_id != line.uom_id):
                price_unit = self.env['product.uom']._compute_price(
                    line.product_id.uom_id.id, price_unit,
                    to_uom_id=line.uom_id.id)
            line.update({'price_unit': price_unit})
