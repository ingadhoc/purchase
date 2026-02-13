##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class PurchaseBillLineMatch(models.Model):
    _inherit = "purchase.bill.line.match"

    reference_description = fields.Char(
        string="Description",
        compute="_compute_reference_description",
    )

    qty_received = fields.Float(
        string="Received",
        related="pol_id.qty_received",
        readonly=True,
    )

    @api.depends("pol_id", "product_id", "display_name")
    def _compute_reference_description(self):
        for rec in self:
            if rec.pol_id and rec.product_id:
                pol_name = rec.pol_id.name or ""
                product_name = rec.product_id.display_name or ""
                if pol_name.startswith(product_name):
                    remaining = pol_name[len(product_name) :].strip()
                    if remaining:
                        rec.reference_description = f"{product_name} - {remaining}"
                    else:
                        rec.reference_description = product_name
                else:
                    rec.reference_description = pol_name
            elif rec.pol_id:
                rec.reference_description = rec.pol_id.name
            else:
                rec.reference_description = rec.display_name
