##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from lxml import etree
import json


class ProductProduct(models.Model):
    _inherit = "product.product"

    qty_purchase = fields.Float(
        string='Quantity to Purchase',
        compute='_compute_qty_purchase',
        help="Technical field. Used to compute the quantity of products"
        " related to a purchase order using the context",
    )

    @api.depends_context('order_id')
    def _compute_qty_purchase(self):
        purchase_order_id = self._context.get('order_id')
        if not purchase_order_id:
            self.qty_purchase = 0
            return

        purchase_order_lines = self.env['purchase.order'].browse(purchase_order_id).order_line
        for rec in self:
            lines = purchase_order_lines.filtered(lambda x: x.product_id == rec)
            value = sum([line.product_uom._compute_quantity(line.product_qty, rec.uom_po_id) for line in lines])
            rec.qty_purchase = value

    def _set_qty_purchase(self, qty):
        self.ensure_one()
        purchase_order_id = self._context.get('order_id', False)
        if purchase_order_id:
            lines = self.env['purchase.order.line'].search([
                ('order_id', '=', purchase_order_id),
                ('product_id', '=', self.id)])
            if lines:
                (lines - lines[0]).unlink()
                lines[0].product_qty = qty
            else:
                self.env['purchase.order'].browse(purchase_order_id).add_products(self, qty)

    def action_product_form(self):
        self.ensure_one()
        view_id = self.env.ref('product.product_normal_form_view').id
        return {
            'name': _('Product'),
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'product.product',
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'view_id': view_id,
        }

    def write(self, vals):
        """
        Si en vals solo viene qty y purchase_catalog_tree entonces es un
        dummy write y hacemos esto para que usuarios sin permiso de escribir
        en productos puedan modificar la cantidad
        """
        if self._context.get('purchase_catalog_tree') and len(vals) == 1 and 'qty_purchase' in vals:
            qty = vals.get('qty_purchase')
            for rec in self:
                rec._set_qty_purchase(qty)
            return True
        return super().write(vals)
