##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.multi
    def _compute_qty_purchase(self):
        purchase_order_id = self._context.get('active_id', False)
        ProductUom = self.env['product.uom']
        if not purchase_order_id:
            self.update({'qty_purchase': 0})
            return

        purchase_order_lines = self.env['purchase.order'].browse(
            purchase_order_id).order_line

        for rec in self:
            lines = purchase_order_lines.filtered(
                lambda x: x.product_id == rec)
            value = sum([ProductUom._compute_quantity(
                line.product_qty,
                line.product_uom,
                rec.uom_po_id) for line in lines])
            rec.update({'qty_purchase': value})

    @api.multi
    def _inverse_qty_purchase(self):
        purchase_order_id = self._context.get('active_id', False)
        if not purchase_order_id:
            return
        purchase_order = self.env['purchase.order'].browse(purchase_order_id)
        purchase_order_lines = purchase_order.order_line
        for rec in self:
            qty = rec.qty_purchase
            lines = purchase_order_lines.filtered(
                lambda x: x.product_id == rec)
            if lines:
                (lines - lines[0]).unlink()
                lines[0].product_qty = qty
                lines[0]._onchange_quantity()
            else:
                purchase_order.add_products(rec, qty)

    qty_purchase = fields.Float(
        string='Quantity',
        compute='_compute_qty_purchase',
        inverse='_inverse_qty_purchase',
        help="Technical field. Used to compute the quantity of products"
        " related to a purchase order using the context")

    @api.multi
    def action_product_form(self):
        self.ensure_one()
        view_id = self.env['ir.model.data'].xmlid_to_res_id(
            'product.product_normal_form_view')
        return {
            'name': _('Product'),
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'product.product',
            'type': 'ir.actions.act_window',
            # 'domain': [('id', 'in', self.apps_product_ids.ids)],
            'res_id': self.id,
            'view_id': view_id,
        }
