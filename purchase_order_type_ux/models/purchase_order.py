# Copyright 2015 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model_create_multi
    def create(self, vals):
        res = super().create(vals)
        if res.order_type and res.order_type.fiscal_position_id:
            res.fiscal_position_id = res.order_type.fiscal_position_id
        return res

    @api.onchange("order_type")
    def onchange_order_type(self):
        super().onchange_order_type()
        for order in self:
            if order.order_type.picking_type_id:
                order.picking_type_id = order.order_type.picking_type_id
            if order.order_type.fiscal_position_id:
                order.fiscal_position_id = order.order_type.fiscal_position_id

    def _prepare_invoice(self):
        if not self.order_type.journal_id:
            return super()._prepare_invoice()
        res = super()._prepare_invoice()
        company = self.order_type.journal_id.company_id
        journal = self.env["account.journal"].browse(res.get("journal_id")) if res.get("journal_id") else False
        if company != self.company_id:
            # En purchase, partner_bank_id es del proveedor, no de la compañía
            partner_bank_id = self.partner_id.commercial_partner_id.bank_ids.filtered_domain(
                ["|", ("company_id", "=", False), ("company_id", "=", company.id)]
            )[:1]
            res["partner_bank_id"] = partner_bank_id.id
            # agregamos para que recompute term y cond si la nueva compañia los tiene por defecto
            if "narration" in res and not res["narration"]:
                del res["narration"]
            if journal and journal.company_id.id != self.company_id.id:
                res.pop("journal_id")

        return res

    def action_create_invoice(self):
        """
        Overrides the `action_create_invoice` method to ensure that taxes are correctly computed
        for the company of the invoice. In cases where the company has a localization
        (e.g., l10n_ar), this ensures that the taxes from `l10n_ar_tax_ids` are applied.
        """
        if len(self.mapped("order_type")) > 1:
            raise ValueError("This method only works for purchase orders of the same type")
        action = super().action_create_invoice()
        order_type = self[:1].order_type
        if order_type.journal_id and order_type.journal_id.company_id != self.company_id:
            invoices = self.mapped("invoice_ids").filtered(lambda m: m.state == "draft")
            company = order_type.journal_id.company_id
            for invoice in invoices:
                acc = self.env["account.change.company"].create(
                    {
                        "move_id": invoice.id,
                        "company_ids": [invoice.company_id.id, company.id],
                        "company_id": company.id,
                        "journal_id": order_type.journal_id.id,
                    }
                )
                acc.change_company()
                invoice.partner_bank_id = company.partner_id.bank_ids[:1].id
        return action
