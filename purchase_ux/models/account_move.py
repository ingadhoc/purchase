##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api
from ast import literal_eval


class AccountMove(models.Model):
    _inherit = 'account.move'

    # dejamos este campo por si alguien lo usaba y ademas lo re usamos abajo
    purchase_order_ids = fields.Many2many(
        'purchase.order',
        compute='_compute_purchase_orders',
        string="Purchase Orders",
    )
    # en la ui agregamos este que seria mejor a nivel performance
    has_purchases = fields.Boolean(
        compute='_compute_has_purchases',
        string='Has Purchases?',
    )

    def _compute_purchase_orders(self):
        for rec in self:
            rec.purchase_order_ids = rec.invoice_line_ids.mapped(
                'purchase_line_id.order_id')

    def _compute_has_purchases(self):
        moves = self.filtered(lambda move: move.is_purchase_document())
        (self - moves).has_purchases = False
        for rec in moves:
            rec.has_purchases = any(line for line in rec.invoice_line_ids.mapped('purchase_line_id'))

    def add_purchase_line_moves(self):
        self.ensure_one()
        action_read = self.env["ir.actions.actions"]._for_xml_id(
            'purchase_ux.action_purchase_line_tree')
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
        for rec in self.get_product_lines_to_update():
            seller = rec.product_id._select_seller(
                partner_id=rec.move_id.partner_id,
                # usamos minimo de cantidad 0 porque si no seria complicado
                # y generariamos registros para cada cantidad que se esta
                # comprando
                quantity=0.0,
                date=rec.move_id.invoice_date,
                # idem quantity, no lo necesitamos
                uom_id=False,
            )
            if not seller:
                seller = self.env['product.supplierinfo'].sudo().create({
                    'date_start': rec.move_id.invoice_date,
                    'partner_id': rec.move_id.partner_id.id,
                    'currency_id': rec.move_id.partner_id.property_purchase_currency_id.id or self.currency_id.id,
                    'product_tmpl_id': rec.product_id.product_tmpl_id.id,
                    'company_id': self.company_id.id,
                })
            price_unit = rec.price_unit
            if rec.product_uom_id and seller.product_uom != rec.product_uom_id:
                price_unit = rec.product_uom_id._compute_price(
                    price_unit, seller.product_uom)

            if net_price_installed:
                seller.net_price = rec.move_id.currency_id._convert(
                    price_unit, seller.currency_id, rec.move_id.company_id,
                    rec.move_id.invoice_date or fields.Date.today())
            else:
                seller.price = rec.move_id.currency_id._convert(
                    price_unit, seller.currency_id, rec.move_id.company_id,
                    rec.move_id.invoice_date or fields.Date.today())

    def get_product_lines_to_update(self):
        return self.with_context(force_company=self.company_id.id).invoice_line_ids.filtered(
                lambda x: x.product_id and x.price_unit)
