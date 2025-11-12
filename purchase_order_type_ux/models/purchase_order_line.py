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
        if not self.order_id.order_type.journal_id:
            return super()._prepare_account_move_line(move=move)
        company = self.order_id.order_type.journal_id.company_id
        self = self.with_company(company.id)
        res = super()._prepare_account_move_line(move=move)

        if company != self.company_id:
            # Because we not have the access to the invoice, we obtain the fiscal position who
            # has the invoice really
            partner_invoice = self.env["res.partner"].browse(self.partner_id.address_get(["invoice"])["invoice"])
            fpos = self.env["account.fiscal.position"].with_company(company.id)._get_fiscal_position(partner_invoice)
            taxes = self.product_id.supplier_taxes_id.filtered(lambda r: company == r.company_id)
            taxes = fpos.map_tax(taxes) if fpos else taxes

            res["tax_ids"] = [(6, 0, taxes.ids)]
        return res
