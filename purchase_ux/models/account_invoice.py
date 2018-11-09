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

    @api.multi
    def _compute_purchase_orders(self):
        for rec in self:
            rec.purchase_order_ids = self.env['purchase.order.line'].search(
                [('invoice_lines', 'in', rec.invoice_line_ids.ids)]).mapped(
                'order_id')

    @api.multi
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

    @api.multi
    def update_prices_with_supplier_cost(self):
        net_price_installed = 'net_price' in self.env[
            'product.supplierinfo']._fields
        for rec in self.invoice_line_ids.filtered('price_unit'):
            seller = rec.product_id._select_seller(
                partner_id=rec.invoice_id.partner_id,
                # usamos minimo de cantidad 0 porque si no seria complicado
                # y generariamos registros para cada cantidad que se esta
                # comprando
                quantity=0.0,
                date=rec.invoice_id.date_invoice and
                rec.invoice_id.date_invoice[:10],
                # idem quantity, no lo necesitamos
                uom_id=False,
            )
            if not seller:
                seller = self.env['product.supplierinfo'].create({
                    'date_start': rec.invoice_id.date_invoice and
                    rec.invoice_id.date_invoice[:10],
                    'name': rec.invoice_id.partner_id.id,
                    'product_tmpl_id': rec.product_id.product_tmpl_id.id,
                })
            price_unit = rec.price_unit
            if rec.uom_id and seller.product_uom != rec.uom_id:
                price_unit = rec.uom_id._compute_price(
                    price_unit, seller.product_uom)

            if net_price_installed:
                seller.net_price = rec.invoice_id.currency_id.compute(
                    price_unit, seller.currency_id)
            else:
                seller.price = rec.invoice_id.currency_id.compute(
                    price_unit, seller.currency_id)
