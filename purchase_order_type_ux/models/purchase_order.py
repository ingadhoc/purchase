# Copyright 2015 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.constrains("order_type")
    def onchange_order_type(self):
        super().onchange_order_type()
        for order in self:
            if order.order_type.project_id:
                order.project_id = order.order_type.project_id
            if order.order_type.picking_type_id:
                order.picking_type_id = order.order_type.picking_type_id

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        if self.order_type.journal_id:
            res["journal_id"] = self.order_type.journal_id.id
        if self.order_type:
            res["purchase_type_id"] = self.order_type.id
        return res
