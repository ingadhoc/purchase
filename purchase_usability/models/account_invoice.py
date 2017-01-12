# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    picking_id = fields.Many2one(
        'stock.picking',
        string='Add Picking',
        help='Encoding help. When selected, the associated picking, all '
        'related purchase order lines are added to the vendor bill. '
        'Several Pickings can be selected.'
    )

    # Load all unsold PO lines related to this picking
    @api.onchange('picking_id')
    def picking_order_change(self):
        if not self.picking_id:
            return {}
        if not self.partner_id:
            self.partner_id = self.picking_id.partner_id.id
        # for purchase in self.picking_id.purchase_ids:
        #     self.purchase_id = purchase
        new_lines = self.env['account.invoice.line']
        for line in self.picking_id.mapped('move_lines.purchase_line_id'):
            # Load a PO line only once
            if line in self.invoice_line_ids.mapped('purchase_line_id'):
                continue
            data = self._prepare_invoice_line_from_po_line(line)
            new_line = new_lines.new(data)
            new_line._set_additional_fields(self)
            new_lines += new_line

        self.invoice_line_ids += new_lines
        self.picking_id = False
        return {}

    @api.onchange('state', 'partner_id', 'invoice_line_ids')
    def _onchange_allowed_picking_ids(self):
        '''
        The purpose of the method is to define a domain for the available
        pickings.
        '''
        result = {}

        # A PO can be selected only if at least one PO line is not already in
        # the invoice
        purchase_line_ids = self.invoice_line_ids.mapped('purchase_line_id')
        already_purchases = self.invoice_line_ids.mapped(
            'purchase_id').filtered(
                lambda r: r.order_line <= purchase_line_ids)
        purchases = self.env['purchase.order'].search([
            ('partner_id', 'child_of', self.partner_id.id),
            ('invoice_status', '=', 'to invoice'),
            ('id', 'not in', already_purchases.ids),
        ])

        result['domain'] = {'picking_id': [
            ('id', 'in', purchases.mapped('picking_ids').ids),
        ]}
        return result
