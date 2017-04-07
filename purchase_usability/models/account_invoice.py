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
                ('company_id', '=', self.company_id.id),
            ]
        return action_read
