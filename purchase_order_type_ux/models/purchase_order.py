# Copyright 2015 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.onchange("order_type")
    def onchange_order_type(self):
        super().onchange_order_type()
        for order in self:
            if order.order_type.project_id:
                order.project_id = order.order_type.project_id
            if order.order_type.picking_type_id:
                order.picking_type_id = order.order_type.picking_type_id

    def _prepare_invoice(self):
        if not self.order_type.journal_id:
            return super()._prepare_invoice()
        res = super()._prepare_invoice()
        company = self.order_type.journal_id.company_id
        self = self.with_company(company.id)
        if company != self.company_id:
            res["company_id"] = company.id
            # En purchase, partner_bank_id es del proveedor, no de la compañía
            partner_bank_id = self.partner_id.commercial_partner_id.bank_ids.filtered_domain(
                ["|", ("company_id", "=", False), ("company_id", "=", company.id)]
            )[:1]
            res["partner_bank_id"] = partner_bank_id.id
            # agregamos para que recompute term y cond si la nueva compañia los tiene por defecto
            if "narration" in res and not res["narration"]:
                del res["narration"]
            po_fiscal_position = self.env["account.fiscal.position"].browse(res["fiscal_position_id"])
            if not po_fiscal_position or (po_fiscal_position.company_id and po_fiscal_position.company_id != company):
                partner_invoice = self.env["res.partner"].browse(self.partner_id.address_get(["invoice"])["invoice"])
                res["fiscal_position_id"] = (
                    self.env["account.fiscal.position"]
                    .with_company(company.id)
                    ._get_fiscal_position(partner_invoice)
                    .id
                )
        if self.order_type:
            res["purchase_type_id"] = self.order_type.id
        return res

    def action_create_invoice(self):
        """
        Overrides the `action_create_invoice` method to ensure that taxes are correctly computed
        for the company of the invoice. In cases where the company has a localization
        (e.g., l10n_ar), this ensures that the taxes from `l10n_ar_tax_ids` are applied.
        """
        action = super().action_create_invoice()
        invoices = self.invoice_ids.filtered(lambda m: m.state == "draft")
        for line in invoices.invoice_line_ids:
            purchase_line = line.purchase_line_id
            if purchase_line and line.move_id.company_id != purchase_line.order_id.company_id:
                line.tax_ids = line._get_computed_taxes()
        return action
