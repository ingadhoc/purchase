# Copyright (C) 2015 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class PurchaseOrderType(models.Model):
    _inherit = "purchase.order.type"

    report_partner_id = fields.Many2one(
        "res.partner",
        help="For the Sale Report, The information of the partner will be used to fill the report header.",
    )
    # los comentamos en vista, los dejamos por ahora en python, los deprecamos en 19
    partner_id = fields.Many2many(
        "res.partner",
        "Supplier",
    )
    journal_id = fields.Many2one(
        "account.journal",
        domain="[('type', '=', 'purchase')]",
        string="Billing Journal",
        check_company=False,
    )
    purchase_method = fields.Selection(
        [
            ("purchase", "On ordered quantities"),
            ("receive", "On received quantities"),
        ],
        string="Bill Control",
    )
    payment_term_id = fields.Many2one(comodel_name="account.payment.term", string="Payment Term", check_company=True)
    picking_type_id = fields.Many2one(
        "stock.picking.type",
        "Deliver To",
        domain="['|', ('warehouse_id', '=', False), ('warehouse_id.company_id', '=', company_id)]",
        help="This will determine operation type of incoming shipment",
    )
    fiscal_position_id = fields.Many2one(
        "account.fiscal.position",
        string="Fiscal Position",
        check_company=True,
        help="If you choose a fiscal position then this fiscal positioon would be used as default instead of the "
        "automatically detected or setted on the partner",
    )
    set_locked_on_confirmation = fields.Boolean(
        string="Lock on Confirmation",
        help="If enabled, purchase orders of this type are automatically locked when they are approved,"
        " preventing further edits. This is additive to the global 'Lock Confirmed Orders' setting: when that"
        " setting is on, every confirmed order is locked regardless of this flag, and the global setting prevails.",
    )
    lock_confirmed_po_setting = fields.Boolean(
        compute="_compute_lock_confirmed_po_setting",
        help="Technical field: True when the global 'Lock Confirmed Orders' setting is enabled for this type's"
        " company. Analogous to sale_order_type_automation's 'auto_done_setting', it hides the per-type"
        " 'Lock on Confirmation' flag while the global setting prevails, since the flag would then be irrelevant.",
    )

    @api.depends("company_id")
    def _compute_lock_confirmed_po_setting(self):
        for rec in self:
            company = rec.company_id or self.env.company
            rec.lock_confirmed_po_setting = company.sudo().po_lock == "lock"
