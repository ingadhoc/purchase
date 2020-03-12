##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from lxml import etree
from odoo.addons.base.models.ir_ui_view import (
    transfer_field_to_modifiers,
    transfer_node_to_modifiers,
    transfer_modifiers_to_node)


class ProductProduct(models.Model):
    _inherit = "product.product"

    qty_purchase = fields.Float(
        string='Quantity to Purchase',
        compute='_compute_qty_purchase',
        help="Technical field. Used to compute the quantity of products"
        " related to a purchase order using the context",
    )

    @api.depends_context('active_id')
    def _compute_qty_purchase(self):
        purchase_order_id = self._context.get('active_id', False)
        if not purchase_order_id:
            self.qty_purchase = 0
            return

        purchase_order_lines = self.env['purchase.order'].browse(
            purchase_order_id).order_line

        for rec in self:
            lines = purchase_order_lines.filtered(
                lambda x: x.product_id == rec)
            value = sum([line.product_uom._compute_quantity(
                line.product_qty,
                rec.uom_po_id) for line in lines])
            rec.qty_purchase = value

    def _set_qty_purchase(self, qty):
        self.ensure_one()
        purchase_order_id = self._context.get('active_id', False)
        if purchase_order_id:
            lines = self.env['purchase.order.line'].search([
                ('order_id', '=', purchase_order_id),
                ('product_id', '=', self.id)])
            if lines:
                (lines - lines[0]).unlink()
                lines[0].product_qty = qty
                lines[0]._onchange_quantity()
            else:
                self.env['purchase.order'].browse(
                    purchase_order_id).add_products(self, qty)

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

    # TODO we should make this module inherits from sale one, value on context
    # should be the same and then we should use same computed field
    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=False, submenu=False):
        """
        If we came from sale order, we send in context 'force_product_edit'
        and we change tree view to make editable and also field qty
        """
        res = super().fields_view_get(
            view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu)
        purchase_quotation_products = self._context.get(
            'purchase_quotation_products')
        if purchase_quotation_products and view_type == 'tree':
            doc = etree.XML(res['arch'])

            # replace uom_id to uom_po_id field
            node = doc.xpath("//field[@name='uom_id']")[0]
            replacement_xml = """
                <field name="uom_po_id"/>
                """
            uom_po_id_node = etree.fromstring(replacement_xml)
            node.getparent().replace(node, uom_po_id_node)
            res['fields'].update(self.fields_get(['uom_po_id']))

            # make all fields not editable
            for node in doc.xpath("//field"):
                node.set('readonly', 'True')
                field = res['fields']
                modifiers = {}
                if field is not None:
                    transfer_field_to_modifiers(field, modifiers)
                transfer_node_to_modifiers(node, modifiers, in_tree_view=True)
                transfer_modifiers_to_node(modifiers, node)

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
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    def write(self, vals):
        """
        Si en vals solo viene qty y purchase_quotation_products entonces es un
        dummy write y hacemos esto para que usuarios sin permiso de escribir
        en productos puedan modificar la cantidad
        """
        # usamos 'qty_purchase' in vals y no vals.get('qty_purchase') porque
        # se podria estar pasando qty_purchase = 0 y queremos que igal entre
        if self._context.get('purchase_quotation_products') and \
                len(vals) == 1 and 'qty_purchase' in vals:
            # en vez de hacerlo con sudo lo hacemos asi para que se guarde
            # bien el usuario creador y ademas porque SUPERADMIN podria no
            # tener el permiso de editar productos
            # self = self.sudo()
            qty = vals.get('qty_purchase')
            for rec in self:
                rec._set_qty_purchase(qty)
            return True
        return super().write(vals)
