##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.osv.orm import setup_modifiers
from lxml import etree


class ProductProduct(models.Model):
    _inherit = "product.product"

    # TODO we should make this module inherits from sale one, value on context
    # should be the same and then we should use same computed field
    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=False, submenu=False):
        """
        If we came from sale order, we send in context 'force_product_edit'
        and we change tree view to make editable and also field qty
        """
        res = super(ProductProduct, self).fields_view_get(
            view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu)
        purchase_quotation_products = self._context.get(
            'purchase_quotation_products')
        if purchase_quotation_products and view_type == 'tree':
            doc = etree.XML(res['arch'])

            # make all fields not editable
            for node in doc.xpath("//field"):
                node.set('readonly', '1')
                setup_modifiers(node, res['fields'], in_tree_view=True)

            # add qty field
            placeholder = doc.xpath("//field[1]")[0]
            placeholder.addprevious(
                etree.Element('field', {
                    'name': 'qty_purchase',
                    # we force editable no matter user rights
                    'readonly': '0',
                }))
            res['fields'].update(self.fields_get(['qty_purchase']))

            # add button tu open form
            placeholder = doc.xpath("//tree")[0]
            placeholder.append(
                etree.Element('button', {
                    'name': 'action_product_form',
                    'type': 'object',
                    'icon': 'fa-external-link',
                    'string': _('Open Product Form View'),
                }))

            # make tree view editable
            for node in doc.xpath("/tree"):
                node.set('edit', 'true')
                node.set('create', 'false')
                node.set('editable', 'top')
            res['arch'] = etree.tostring(doc)
        return res

    @api.multi
    def _compute_qty_purchase(self):
        purchase_order_id = self._context.get('active_id', False)
        for rec in self:
            rec.qty_purchase = 0
            if purchase_order_id:
                lines = self.env['purchase.order.line'].search([
                    ('order_id', '=', purchase_order_id),
                    ('product_id', '=', rec.id)])
                rec.qty_purchase = \
                    sum([self.env['product.uom']._compute_quantity(
                        line.product_qty,
                        line.product_uom,
                        rec.uom_po_id) for line in lines])

    @api.multi
    def _inverse_qty_purchase(self):
        purchase_order_id = self._context.get('active_id', False)
        for rec in self:
            qty = rec.qty_purchase
            if purchase_order_id:
                lines = self.env['purchase.order.line'].search([
                    ('order_id', '=', purchase_order_id),
                    ('product_id', '=', rec.id)])
                if lines:
                    (lines - lines[0]).unlink()
                    lines[0].product_qty = qty
                    lines[0]._onchange_quantity()
                else:
                    self.env['purchase.order'].browse(
                        purchase_order_id).add_products(rec, qty)

    qty_purchase = fields.Float(
        string='Quantity',
        compute='_compute_qty_purchase',
        inverse='_inverse_qty_purchase')

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
