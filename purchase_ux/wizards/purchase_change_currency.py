##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class PurchaseChangeCurrency(models.TransientModel):
    _name = 'purchase.change.currency'
    _description = 'Change Currency Purchase Order'

    currency_id = fields.Many2one(
        'res.currency',
        string='Change to',
        required=True,
        help="Select a currency to apply on the purchase order",
    )
    currency_rate = fields.Float(
        required=True,
        help="Select a currency rate to apply on the purchase order",
    )

    @api.multi
    def get_purchase(self):
        self.ensure_one()
        purchase_order = self.env['purchase.order'].browse(
            self._context.get('active_id', False))
        if not purchase_order:
            raise UserError(
                _('No Purchase Order on context as "active_id"'))
        return purchase_order

    @api.onchange('currency_id')
    def onchange_currency(self):
        purchase_order = self.get_purchase()
        if not self.currency_id:
            self.currency_rate = False
        else:
            if self.currency_id == purchase_order.currency_id:
                raise UserError(_(
                    'Old Currency And New Currency can not be the same'))
            currency = purchase_order.currency_id.with_context(
                date=purchase_order.
                date_order or fields.Date.context_today(self))
            self.currency_rate = currency.compute(
                1.0, self.currency_id)

    @api.multi
    def change_currency(self):
        self.ensure_one()
        purchase_order = self.get_purchase()
        for line in purchase_order.order_line:
            line.price_unit = self.currency_id.round(
                line.price_unit * self.currency_rate),
        purchase_order.currency_id = self.currency_id.id
