# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Copyright 2020 Tecnativa - Pedro M. Baeza

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    purchase_type_id = fields.Many2one(
        comodel_name="purchase.order.type",
        string="Purchase Type",
        compute="_compute_purchase_type_id",
        store=True,
        readonly=False,
        ondelete="restrict",
        copy=True,
        precompute=True,
    )

    @api.depends("partner_id", "company_id", "move_type")
    def _compute_purchase_type_id(self):
        purchase_type = self.env["purchase.order.type"].browse()
        for record in self:
            if record.move_type not in ["in_invoice", "in_refund"]:
                record.purchase_type_id = purchase_type
                continue
            else:
                record.purchase_type_id = record._origin.purchase_type_id
            if not record.partner_id:
                record.purchase_type_id = self.env["purchase.order.type"].search(
                    [("company_id", "in", [self.env.company.id, False])], limit=1
                )
            else:
                purchase_type = (
                    record.partner_id.with_company(record.company_id).purchase_type
                    or record.partner_id.commercial_partner_id.with_company(record.company_id).purchase_type
                )
                if purchase_type:
                    record.purchase_type_id = purchase_type

    @api.depends("purchase_type_id")
    def _compute_invoice_payment_term_id(self):
        res = super()._compute_invoice_payment_term_id()
        for move in self.filtered("purchase_type_id.payment_term_id"):
            move.invoice_payment_term_id = move.purchase_type_id.payment_term_id
        return res

    @api.depends("purchase_type_id")
    def _compute_journal_id(self):
        res = super()._compute_journal_id()
        for move in self.filtered("purchase_type_id.journal_id"):
            move.journal_id = move.purchase_type_id.journal_id
        return res
