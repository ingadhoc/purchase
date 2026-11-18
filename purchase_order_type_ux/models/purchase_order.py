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

    def button_approve(self, force=False):
        res = super().button_approve(force=force)
        # En compras el "bloqueo" es el booleano `locked` (en 19.0 ya no existe el
        # estado 'done'; el core lo setea acá cuando el lock global está activo).
        # Lo replicamos por tipo de forma aditiva: solo órdenes recién aprobadas.
        self.filtered(
            lambda o: o.order_type.set_locked_on_confirmation and o.state == "purchase" and not o.locked
        ).write({"locked": True})
        return res

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
<<<<<<< 489bee843a8516547391e75a3a5ea66d5c128d9b
        if self.order_type.journal_id:
            res["journal_id"] = self.order_type.journal_id.id
        if self.order_type.invoice_company_id and self.order_type.invoice_company_id != self.company_id:
            res["company_id"] = self.order_type.invoice_company_id.id
||||||| 395ee690fdbaa2ac42baa49742315ac7cbdcbc79
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

=======
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
        else:
            res["journal_id"] = self.order_type.journal_id.id

>>>>>>> baf4d510ebf6f4612b1d80462f673f27e8e0517d
        return res
