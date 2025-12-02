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
        res = super()._prepare_invoice()
        if self.order_type.journal_id:
            res["journal_id"] = self.order_type.journal_id.id
        if self.order_type.invoice_company_id and self.order_type.invoice_company_id != self.company_id:
            res["company_id"] = self.order_type.invoice_company_id.id
        return res
