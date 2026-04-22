##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class PurchaseBillLineMatch(models.Model):
    _inherit = "purchase.bill.line.match"
    _order = "state, product_id, aml_id, pol_id"

    reference_description = fields.Char(
        string="Description",
        compute="_compute_reference_description",
    )

    qty_received = fields.Float(
        string="Received",
        related="pol_id.qty_received",
        readonly=True,
    )

    date_order = fields.Datetime(related="pol_id.order_id.date_order", readonly=True)

    @api.depends("pol_id", "product_id", "display_name")
    def _compute_reference_description(self):
        lang = self.env.user.lang
        for rec in self:
            if rec.pol_id:
                pol_name = rec.pol_id.name or ""
                # pol.name format: "[ref] Product Name\nExtra description"
                # Use only the extra description if present, otherwise translated product name
                parts = pol_name.split("\n", 1)
                extra = parts[1].strip() if len(parts) > 1 else ""
                rec.reference_description = extra or rec.pol_id.product_id.with_context(lang=lang).display_name
            else:
                rec.reference_description = rec.display_name

    def action_match_lines(self):
        """When opened from an existing draft bill and only PO lines are selected
        (no aml_id), add the POLs to the current bill instead of creating a new one.
        """
        account_move_id = self.env.context.get("default_account_move_id")
        if account_move_id and not self.aml_id and self.pol_id:
            bill = self.env["account.move"].browse(account_move_id)
            if bill.exists() and bill.state == "draft":
                bill._add_purchase_order_lines(self.pol_id)
                return bill._get_records_action()
        return super().action_match_lines()

    def _compute_product_uom_qty(self):
        # Only apply the incompatibility filter when the view was opened
        # via the purchase matching action (context flag set by the action).
        if self.env.context.get("purchase_matching_from_button"):
            for rec in self:
                if rec.line_uom_id.category_id.id != rec.product_uom_id.category_id.id:
                    # incompatible categories: ignore this line for matching
                    rec.product_uom_qty = 0.0
                else:
                    rec.product_uom_qty = rec.line_uom_id._compute_quantity(rec.line_qty, rec.product_uom_id)
        else:
            return super()._compute_product_uom_qty()
