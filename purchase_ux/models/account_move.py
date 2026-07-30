##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models
from odoo.tools import float_compare


class AccountMove(models.Model):
    _inherit = "account.move"

    # dejamos este campo por si alguien lo usaba y ademas lo re usamos abajo
    purchase_order_ids = fields.Many2many(
        "purchase.order",
        compute="_compute_purchase_orders",
        string="Purchase Orders",
    )
    # en la ui agregamos este que seria mejor a nivel performance
    has_purchases = fields.Boolean(
        compute="_compute_has_purchases",
        string="Has Purchases?",
    )

    def _compute_purchase_orders(self):
        for rec in self:
            rec.purchase_order_ids = rec.invoice_line_ids.mapped("purchase_line_id.order_id")

    def _compute_has_purchases(self):
        moves = self.filtered(lambda move: move.is_purchase_document())
        (self - moves).has_purchases = False
        for rec in moves:
            rec.has_purchases = any(line for line in rec.invoice_line_ids.mapped("purchase_line_id"))

    def update_prices_with_supplier_cost(self):
        net_price_installed = "net_price" in self.env["product.supplierinfo"]._fields
        for rec in self.get_product_lines_to_update():
            seller = (
                self.env["product.supplierinfo"]
                .sudo()
                .search(
                    [
                        ("partner_id", "=", rec.move_id.partner_id.id),
                        ("product_tmpl_id", "=", rec.product_id.product_tmpl_id.id),
                        ("company_id", "=", self.company_id.id),
                    ],
                    limit=1,
                )
            )

            if not seller:
                seller = (
                    self.env["product.supplierinfo"]
                    .sudo()
                    .create(
                        {
                            "date_start": rec.move_id.invoice_date,
                            "partner_id": rec.move_id.partner_id.id,
                            "currency_id": rec.move_id.partner_id.property_purchase_currency_id.id
                            or self.currency_id.id,
                            "product_tmpl_id": rec.product_id.product_tmpl_id.id,
                            "company_id": self.company_id.id,
                        }
                    )
                )
            price_unit = rec.price_unit
            if rec.product_uom_id and seller.product_uom != rec.product_uom_id:
                price_unit = rec.product_uom_id._compute_price(price_unit, seller.product_uom)

            if net_price_installed:
                seller.net_price = rec.move_id.currency_id._convert(
                    price_unit,
                    seller.currency_id,
                    rec.move_id.company_id,
                    rec.move_id.invoice_date or fields.Date.today(),
                )
            else:
                seller.price = rec.move_id.currency_id._convert(
                    price_unit,
                    seller.currency_id,
                    rec.move_id.company_id,
                    rec.move_id.invoice_date or fields.Date.today(),
                )

    def get_product_lines_to_update(self):
        return self.with_company(self.company_id.id).invoice_line_ids.filtered(lambda x: x.product_id and x.price_unit)

    def action_purchase_matching(self):
        res = super().action_purchase_matching()
        # mark the action so compute method in the view can apply special filtering
        # also pass the current move id so matching adds POLs to this bill instead of creating a new one
        if isinstance(res, dict):
            ctx = dict(res.get("context") or {})
            ctx["purchase_matching_from_button"] = True
            ctx["default_account_move_id"] = self.id
            res["context"] = ctx
            # Show POLs with a pending amount to invoice, using qty_to_invoice so that
            # returns are handled: on a bill (in_invoice) we want lines still to bill
            # (qty_to_invoice > 0), on a credit note (in_refund) we want lines with a
            # pending refund left by a return (qty_to_invoice < 0). The previous check
            # (product_qty > qty_invoiced) ignored returns, since product_qty does not
            # drop with a return, and hid those lines from the matcher.
            all_pols = self.env["purchase.order.line"].search(
                [
                    ("partner_id", "in", (self.partner_id | self.partner_id.commercial_partner_id).ids),
                    ("state", "in", ["purchase", "done"]),
                ]
            )
            # exclude POLs already matched to a line in this bill (qty_invoiced ignores drafts)
            already_matched = set(self.invoice_line_ids.filtered("purchase_line_id").mapped("purchase_line_id").ids)
            is_refund = self.move_type == "in_refund"
            uom_precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")

            def _pending(pol):
                if pol.id in already_matched:
                    return False
                sign = float_compare(pol.qty_to_invoice, 0.0, precision_digits=uom_precision)
                return sign < 0 if is_refund else sign > 0

            pending_pol_ids = all_pols.filtered(_pending).ids
            domain = list(res.get("domain") or [])
            domain += ["|", ("pol_id", "=", False), ("pol_id", "in", pending_pol_ids)]
            res["domain"] = domain
        return res
