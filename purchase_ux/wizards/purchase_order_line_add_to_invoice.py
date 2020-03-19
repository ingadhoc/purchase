##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

logger = logging.getLogger(__name__)


class PurchaseOrderLineAddToInvoice(models.TransientModel):
    _name = 'purchase.order.line.add_to_invoice'
    _description = 'purchase.order.line.add_to_invoice'

    # we need to make this wizard because we loose in context the invoice from
    # where we have come. It is also usefull if you are on purchase lines

    @api.model
    def get_partner_id(self):
        pol = self.get_purchase_lines()
        partner = pol.mapped('partner_id.commercial_partner_id')
        if len(partner) != 1:
            raise UserError(_(
                'Selected lines must be from the same partner'))
        return partner[0].id

    partner_id = fields.Many2one(
        'res.partner',
        default=lambda self: self.get_partner_id(),
        required=True,
    )
    invoice_id = fields.Many2one(
        'account.move',
        'Invoice',
        required=True,
        domain="[('partner_id.commercial_partner_id', '=', partner_id), "
        "('state', '=', 'draft'), "
        "('type', 'in', ['in_invoice', 'in_refund'])]",
    )
    voucher = fields.Char(
    )

    @api.model
    def get_purchase_lines(self):
        active_ids = self._context.get('active_ids', [])
        active_model = self._context.get('active_model', False)
        if active_model != 'purchase.order.line':
            raise UserError(_(
                'This wizard must be called from purchase lines'))
        return self.env[active_model].browse(active_ids)

    def confirm(self):
        self.ensure_one()
        pol = self.get_purchase_lines()
        # send to not compute to compute everything on one time
        pol.with_context(
            do_not_compute=True,
            voucher=self.voucher,
            active_id=self.invoice_id.id,
            active_model='account.move').action_add_all_to_invoice()
        pol._compute_qty_invoiced()
