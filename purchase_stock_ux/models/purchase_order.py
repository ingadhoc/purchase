##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    force_delivered_status = fields.Selection(
        [
            ("pending", "Not Received"),
            ("partial", "Partially Received"),
            ("full", "Fully Received"),
        ],
        tracking=True,
        copy=False,
    )

    with_returns = fields.Boolean(
        compute="_compute_with_returns",
        store=True,
    )

    @api.depends("order_line.qty_returned")
    def _compute_with_returns(self):
        for order in self:
            if any(line.qty_returned for line in order.order_line):
                order.with_returns = True
            else:
                order.with_returns = False

    @api.depends("force_delivered_status")
    def _compute_receipt_status(self):
        super()._compute_receipt_status()

        for order in self.filtered("force_delivered_status"):
            order.receipt_status = order.force_delivered_status

    def write(self, values):
        self = self.with_context(cancel_from_order=True)
        self.check_force_delivered_status(values)
        return super().write(values)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self.check_force_delivered_status(vals)
        return super().create(vals_list)

    @api.model
    def check_force_delivered_status(self, vals):
        if vals.get("force_delivered_status") and not self.env.user.has_group("base.group_system"):
            group = self.env.ref("base.group_system").sudo()
            if group.privilege_id:
                raise UserError(
                    _('Only users with "%s / %s" can Set Received manually') % (group.privilege_id.name, group.name)
                )
            else:
                raise UserError(_('Only users with "%s" can Set Received manually') % (group.name))

    def action_create_invoice(self, attachment_ids=False):
        """Drop the zero-quantity lines Odoo 19 leaves on the draft vendor bill.

        Odoo 19's ``action_create_invoice`` iterates over every ``order_line``
        without filtering by ``qty_to_invoice`` (the old ``_get_invoiceable_lines``
        is gone). Our ``_compute_qty_invoiced`` subtracts ``qty_returned``, so a
        fully-returned line has ``qty_to_invoice = 0`` and core still adds it to
        the bill as a zero-quantity line.

        We let ``super`` build the invoice and clean it up afterwards instead of
        reimplementing the whole method, so we don't bypass other overrides of it
        in the MRO (e.g. ``purchase_force_invoiced``, which skips invoicing on
        force-invoiced orders). Sections, notes and down payment lines are kept.
        """
        invoices_before = self.invoice_ids
        action = super().action_create_invoice(attachment_ids=attachment_ids)
        precision = self.env["decimal.precision"].precision_get("Product Unit")
        new_invoices = self.invoice_ids - invoices_before
        new_invoices.invoice_line_ids.filtered(
            lambda aml: aml.display_type == "product"
            and not aml.is_downpayment
            and float_is_zero(aml.quantity, precision_digits=precision)
        ).unlink()
        return action

    def button_cancel(self):
        self = self.with_context(cancel_from_order=True)
        return super().button_cancel()

    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        res["note"] = self.internal_notes
        return res
