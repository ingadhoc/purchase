# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import UserError
from openerp.tools.float_utils import float_compare
import openerp.addons.decimal_precision as dp
from openerp.osv.orm import setup_modifiers
from lxml import etree
import logging
_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # add context so show purchase data by default
    order_id = fields.Many2one(
        context={'show_purchase': True}
    )
    invoice_status = fields.Selection([
        ('no', 'Not purchased'),
        ('to invoice', 'Waiting Invoices'),
        ('invoiced', 'Invoice Received'),
    ],
        string='Invoice Status',
        compute='_get_invoiced',
        store=True,
        readonly=True,
        copy=False,
        default='no'
    )
    delivery_status = fields.Selection([
        ('no', 'Not purchased'),
        ('to receive', 'To Receive'),
        ('received', 'Received'),
    ],
        string='Delivery Status',
        compute='_get_received',
        store=True,
        readonly=True,
        copy=False,
        default='no'
    )
    vouchers = fields.Char(
        compute='_compute_vouchers'
    )

    @api.multi
    def _compute_vouchers(self):
        for rec in self:
            rec.vouchers = ', '.join(rec.mapped(
                'move_ids.picking_id.voucher_ids.display_name'))

    @api.depends('order_id.state', 'qty_received', 'product_qty')
    def _get_received(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for line in self:
            # on v9 odoo consider done with no more to purchase, PR has been
            # deny, if we change it here we should change odoo behaviour on
            # purchase orders
            # al final dejamos  nuestro criterio porque es confuso para
            # clientes y de hecho odoo, a diferencia de lo que dice el boton
            # si te deja crear las facturas en done
            # if line.state != 'purchase':
            if line.state not in ('purchase', 'done'):
                line.delivery_status = 'no'
                continue

            if float_compare(
                    line.qty_received, line.product_qty,
                    precision_digits=precision) == -1:
                line.delivery_status = 'to receive'
            elif float_compare(
                    line.qty_received, line.product_qty,
                    precision_digits=precision) >= 0:
                line.delivery_status = 'received'
            else:
                line.delivery_status = 'no'

    @api.depends('order_id.state', 'qty_invoiced', 'product_qty')
    def _get_invoiced(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for line in self:
            # on v9 odoo consider done with no more to purchase, PR has been
            # deny, if we change it here we should change odoo behaviour on
            # purchase orders
            # al final dejamos  nuestro criterio porque es confuso para
            # clientes y de hecho odoo, a diferencia de lo que dice el boton
            # si te deja crear las facturas en done
            # if order.state != 'purchase':
            if line.state not in ('purchase', 'done'):
                line.invoice_status = 'no'
                continue
            if float_compare(
                    line.qty_invoiced, line.product_qty,
                    precision_digits=precision) == -1:
                line.invoice_status = 'to invoice'
            elif float_compare(
                    line.qty_invoiced, line.product_qty,
                    precision_digits=precision) >= 0:
                line.invoice_status = 'invoiced'
            else:
                line.invoice_status = 'no'

# modificaciones para facilitar creacion de factura
    # este campo no existe en POL, robamos de SOL
    qty_to_invoice = fields.Float(
        compute='_get_to_invoice_qty',
        string='To Invoice',
        # store=True,
        readonly=True,
        # digits=dp.get_precision('Product Unit of Measure'),
        default=0.0
    )

    # @api.depends(
    #     'qty_invoiced', 'qty_delivered', 'product_uom_qty', 'order_id.state')
    def _get_to_invoice_qty(self):
        for line in self:
            if line.order_id.state in ['purchase', 'done']:
                if line.product_id.purchase_method == 'purchase':
                    line.qty_to_invoice = line.product_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_received - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=False, submenu=False):
        """
        If we came from invoice, we send in context 'force_line_edit'
        and we change tree view to make editable and also field qty
        """
        res = super(PurchaseOrderLine, self).fields_view_get(
            view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu)
        force_line_edit = self._context.get(
            'force_line_edit')
        if force_line_edit and view_type == 'tree':
            doc = etree.XML(res['arch'])
            # add to invoice qty field (before setupmodifis because if not
            # it remains editable)
            placeholder = doc.xpath("//field[1]")[0]
            placeholder.addprevious(
                etree.Element('field', {
                    'name': 'qty_to_invoice',
                    'readonly': '1',
                }))

            # make all fields not editable
            for node in doc.xpath("//field"):
                node.set('readonly', '1')
                setup_modifiers(node, res['fields'], in_tree_view=True)

            # add qty field
            placeholder.addprevious(
                etree.Element('field', {
                    'name': 'invoice_qty',
                    # we force editable no matter user rights
                    'readonly': '0',
                }))
            res['fields'].update(self.fields_get(
                ['invoice_qty', 'qty_to_invoice']))

            # add button to add all
            placeholder.addprevious(
                etree.Element('button', {
                    'name': 'action_add_all_to_invoice',
                    'type': 'object',
                    'icon': 'fa-plus-square',
                    'string': _('Add all to picking'),
                }))

            # make tree view editable
            for node in doc.xpath("/tree"):
                node.set('edit', 'true')
                node.set('create', 'false')
                node.set('editable', 'top')
            res['arch'] = etree.tostring(doc)
        return res

    @api.multi
    def _compute_invoice_qty(self):
        invoice_id = self._context.get('active_id', False)
        if not invoice_id:
            return True
        for rec in self:
            lines = rec.env['account.invoice.line'].search([
                ('invoice_id', '=', invoice_id),
                ('purchase_line_id', '=', rec.id)])
            rec.invoice_qty = sum(lines.mapped('quantity'))

    @api.multi
    def _inverse_invoice_qty(self):
        invoice_id = self._context.get('active_id', False)
        active_model = self._context.get('active_model', False)
        if not invoice_id or active_model != 'account.invoice':
            return True
        invoice = self.env['account.invoice'].browse(invoice_id)
        purchase_lines = self.env['account.invoice.line']
        for rec in self:
            lines = rec.env['account.invoice.line'].search([
                ('invoice_id', '=', invoice_id),
                ('purchase_line_id', '=', rec.id)])
            if rec.invoice_qty > rec.qty_to_invoice:
                raise UserError(_(
                    'No puede facturar más de lo pendiente a facturar. '
                    'Verifique la configuración de facturación de sus '
                    'productos y/o la receipción de la mercadería.'))
            if lines:
                # si existitan lineas y la cantidad es zero borramos
                if not rec.invoice_qty:
                    lines.unlink()
                else:
                    (lines - lines[0]).unlink()
                    lines[0].quantity = rec.invoice_qty
            else:
                # si no hay lineas y no se puso cantidad entonces no hacemos
                # nada
                if not rec.invoice_qty:
                    continue
                data = invoice._prepare_invoice_line_from_po_line(rec)
                data['quantity'] = rec.invoice_qty
                data['invoice_id'] = invoice_id
                new_line = purchase_lines.new(data)
                new_line._set_additional_fields(self)
                vals = new_line._convert_to_write(new_line._cache)
                purchase_lines.create(vals)

    invoice_qty = fields.Float(
        string='Quantity',
        compute='_compute_invoice_qty',
        inverse='_inverse_invoice_qty',
        search='_search_invoice_qty',
        digits=dp.get_precision('Product Unit of Measure'),
    )

    @api.model
    def _search_invoice_qty(self, operator, operand):
        """
        implementamos solo el caso "('invoice_qty', '!=', False)" que es el que
        usamos en la vista y unico que nos interesa por ahora
        """
        invoice_id = self._context.get('active_id', False)
        active_model = self._context.get('active_model', False)
        if active_model != 'account.invoice':
            return []
        return [('invoice_lines.invoice_id', 'in', [invoice_id])]

    @api.multi
    def action_add_all_to_invoice(self):
        for rec in self:
            rec.invoice_qty = rec.qty_to_invoice
