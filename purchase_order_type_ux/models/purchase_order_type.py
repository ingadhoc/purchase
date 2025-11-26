# Copyright (C) 2015 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class PurchaseOrderType(models.Model):
    _inherit = "purchase.order.type"

    report_partner_id = fields.Many2one(
        "res.partner",
        help="For the Sale Report, The information of the partner will be used to fill the report header.",
    )
    partner_id = fields.Many2many(
        "res.partner",
        "Supplier",
    )
    project_id = fields.Many2one(
        "project.project",
        help="Select to define the analytics account",
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

    @api.constrains("partner_id")
    def _compute_partner_purchase_order_type(self):
        for rec in self:
            if rec.partner_id:
                rec.partner_id.purchase_type = rec.id
