# Copyright (C) 2015 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class PurchaseOrderType(models.Model):
    _inherit = "purchase.order.type"

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
        help="This will determine operation type of incoming shipment",
        check_company=True,
    )
    fiscal_position_id = fields.Many2one(
        "account.fiscal.position",
        string="Fiscal Position",
        check_company=True,
        help="If you choose a fiscal position then this fiscal positioon would be used as default instead of the "
        "automatically detected or setted on the partner",
    )
    invoice_company_id = fields.Many2one(
        "res.company",
        string="Invoice Company",
        domain="[('id', 'child_of', company_id)]",
        compute="_compute_invoice_company_id",
        store=True,
        readonly=False,
        precompute=True,
    )
    journal_domain = fields.Binary(compute="_compute_journal_domain")
    # en este caso no hace falta definir "check_company=False" porque el modulo original no tiene este campo
    # pero lo dejamos definido al argumento para que quede más parecido a sale_order_type_ux
    journal_id = fields.Many2one(
        "account.journal",
        domain="journal_domain",
        check_company=False,
        string="Billing Journal",
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
    def _compute_invoice_company_id(self):
        for rec in self:
            rec.invoice_company_id = rec.company_id

    @api.depends("invoice_company_id")
    def _compute_journal_domain(self):
        for rec in self:
            rec.journal_domain = Domain(
                rec.env["account.journal"]._check_company_domain(rec.invoice_company_id)
            ) & Domain("type", "=", "purchase")

    @api.constrains("invoice_company_id", "journal_id")
    def _check_journal_company(self):
        for rec in self:
            if rec.journal_id and rec.journal_id not in rec.env["account.journal"].search(rec.journal_domain):
                raise ValidationError("The selected 'Billing Journal' does not belong to the selected invoice company.")

    @api.depends("company_id")
    def _compute_lock_confirmed_po_setting(self):
        for rec in self:
            company = rec.company_id or self.env.company
            rec.lock_confirmed_po_setting = company.sudo().po_lock == "lock"
