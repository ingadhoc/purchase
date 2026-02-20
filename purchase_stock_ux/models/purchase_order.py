##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


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

    def button_cancel(self):
        self = self.with_context(cancel_from_order=True)
        return super().button_cancel()

    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        res["note"] = self.internal_notes
        return res
