##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseChangeCurrency(models.TransientModel):
    _name = "purchase.change.currency"
    _description = "Change Currency Purchase Order"

    currency_id = fields.Many2one(
        "res.currency",
        string="Change to",
        required=True,
        help="Select a currency to apply on the purchase order",
    )
    currency_rate = fields.Float(
        required=True,
        digits=(16, 6),
        help="Select a currency rate to apply on the purchase order",
    )

    def get_purchase(self):
        self.ensure_one()
        purchase_order = self.env["purchase.order"].browse(self.env.context.get("active_id", False))
        if not purchase_order:
            raise UserError(_('No Purchase Order on context as "active_id"'))
        return purchase_order

    @api.onchange("currency_id")
    def onchange_currency(self):
        purchase_order = self.get_purchase()
        if not self.currency_id:
            self.currency_rate = False
        else:
            if self.currency_id == purchase_order.currency_id:
                raise UserError(_("Old Currency And New Currency can not be the same"))
            self.currency_rate = self.env["res.currency"]._get_conversion_rate(
                from_currency=purchase_order.currency_id,
                to_currency=self.currency_id,
                company=purchase_order.company_id,
                date=purchase_order.date_order or fields.Date.context_today(self),
            )

    def change_currency(self):
        self.ensure_one()
        purchase_order = self.get_purchase()
        for line in purchase_order.order_line:
            line.price_unit = self.currency_id.round(line.price_unit * self.currency_rate)
        purchase_order.currency_id = self.currency_id.id
