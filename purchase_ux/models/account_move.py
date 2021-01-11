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
        'sale.order',
        compute='_compute_has_purchases'
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

    def action_view_purchase_orders(self):
        self.ensure_one()
        if len(self.purchase_order_ids) > 1:
            action_read = self.env.ref('purchase.purchase_form_action').read()[0]
            action_read['domain'] = "[('id', 'in', %s)]" % self.purchase_order_ids.ids
            return action_read
        else:
            return self.purchase_order_ids.get_formview_action()

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
                force_company=self.company_id.id).invoice_line_ids.filtered(
                lambda x: x.product_id and x.price_unit):
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
                    'name': rec.move_id.partner_id.id,
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

    @api.onchange('purchase_vendor_bill_id', 'purchase_id')
    def _onchange_purchase_auto_complete(self):
        """
        We need to use replacing and calling super function because, super func
        delete purchase_id link
        """
        if not self.purchase_id:
            return {}
        narration = self.purchase_id.notes
        internal_notes = self.purchase_id.internal_notes
        if self.narration:
            narration = '%s\n%s' % (self.narration, narration)
        if self.internal_notes:
            internal_notes = '%s\n%s' % (self.internal_notes, internal_notes)
        self.narration = narration
        self.internal_notes = internal_notes
        return super()._onchange_purchase_auto_complete()
