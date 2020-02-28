##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api
from ast import literal_eval


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    purchase_order_ids = fields.Many2many(
        'purchase.order',
        compute='_compute_purchase_orders'
    )

    def _compute_purchase_orders(self):
        for rec in self:
            rec.purchase_order_ids = self.env['purchase.order.line'].search(
                [('invoice_lines', 'in', rec.invoice_line_ids.ids)]).mapped(
                'order_id')

    def add_purchase_line_moves(self):
        self.ensure_one()
        actions = self.env.ref(
            'purchase_ux.action_purchase_line_tree')
        if actions:
            action_read = actions.read()[0]
            context = literal_eval(action_read['context'])
            context.update(dict(
                force_line_edit=True,
                search_default_not_invoiced=True,
                search_default_invoice_qty=True,
            ))
            action_read.update(
                context=context,
                domain=[
                    ('partner_id.commercial_partner_id', '=',
                     self.partner_id.commercial_partner_id.id),
                ],
            )

        return action_read

    def update_prices_with_supplier_cost(self):
        net_price_installed = 'net_price' in self.env[
            'product.supplierinfo']._fields
        for rec in self.with_context(
                force_company=self.company_id.id).invoice_line_ids.filtered(lambda x: x.product_id and x.price_unit):
            seller = rec.product_id._select_seller(
                partner_id=rec.invoice_id.partner_id,
                # usamos minimo de cantidad 0 porque si no seria complicado
                # y generariamos registros para cada cantidad que se esta
                # comprando
                quantity=0.0,
                date=rec.invoice_id.date_invoice and
                rec.invoice_id.date_invoice.date(),
                # idem quantity, no lo necesitamos
                uom_id=False,
            )
            if not seller:
                seller = self.env['product.supplierinfo'].sudo().create({
                    'date_start': rec.invoice_id.date_invoice and
                    rec.invoice_id.date_invoice.date(),
                    'name': rec.invoice_id.partner_id.id,
                    'currency_id': rec.invoice_id.partner_id.property_purchase_currency_id.id or self.currency_id.id,
                    'product_tmpl_id': rec.product_id.product_tmpl_id.id,
                    'company_id': self.company_id.id,
                })
            price_unit = rec.price_unit
            if rec.uom_id and seller.product_uom != rec.uom_id:
                price_unit = rec.uom_id._compute_price(
                    price_unit, seller.product_uom)

            if net_price_installed:
                seller.net_price = rec.invoice_id.currency_id._convert(
                    price_unit, seller.currency_id, rec.invoice_id.company_id,
                    rec.invoice_id.date_invoice or fields.Date.today())
            else:
                seller.price = rec.invoice_id.currency_id._convert(
                    price_unit, seller.currency_id, rec.invoice_id.company_id,
                    rec.invoice_id.date_invoice or fields.Date.today())

    @api.onchange('purchase_id')
    def purchase_order_change(self):
        """ This fixes that odoo creates the PO without the fp and our patch
        of account._onchange_company compute wrong the taxes.
        TODO improve this. If a different fp is selected on the PO than the
        partner default one, then odoo changes the fp when calling super.
        """
        self.fiscal_position_id = self.purchase_id.fiscal_position_id
        return super().purchase_order_change()
