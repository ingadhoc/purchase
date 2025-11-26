##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    taxes_id = fields.Many2many(check_company=False)

    @api.depends("qty_invoiced", "qty_received", "order_id.state", "qty_returned", "order_id.order_type")
    def _compute_qty_invoiced(self):
        super()._compute_qty_invoiced()
        for line in self:
            if line.order_id.state in ["purchase", "done"] and line.order_id.order_type.purchase_method:
                if line.order_id.order_type.purchase_method == "purchase":
                    line.qty_to_invoice = line.product_qty - line.qty_invoiced - line.qty_returned
                else:
                    line.qty_to_invoice = line.qty_received - line.qty_invoiced

    def _prepare_account_move_line(self, move=False):
        """
        Forzamos compania de diario de purchase type
        """
        res = super()._prepare_account_move_line(move=move)
        downpayment_lines = self.invoice_lines.filtered("is_downpayment")
        account_id = self.env["account.account"].browse(res["account_id"]) if res.get("account_id") else None
        if (
            self.is_downpayment
            and downpayment_lines
            and account_id
            and self.company_id.id not in account_id.company_ids.ids
        ):
            account_id = self.env["account.change.company"]._get_change_downpayment_account(
                self.company_id, self.invoice_lines, self.order_id.fiscal_position_id
            )
            res["account_id"] = account_id.id
        return res
