# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
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

    qty_on_voucher = fields.Float(
        compute="_compute_qty_on_voucher",
        string="On Voucher",
        digits=dp.get_precision('Product Unit of Measure'),
    )

    @api.multi
    def _compute_qty_on_voucher(self):
        # al calcular por voucher no tenemos en cuenta el metodo de facturacion
        # es decir, que calculamos como si fuese metodo segun lo recibido
        voucher = self._context.get('voucher', False)
        if voucher:
            lines = self.filtered(
                lambda x: x.order_id.state in ['purchase', 'done'])
            moves = self.env['stock.move'].search([
                ('id', 'in', lines.mapped('move_ids').ids),
                ('state', '=', 'done'),
                ('picking_id.voucher_ids.name', 'ilike', voucher),
            ])
            for line in lines:
                line.qty_on_voucher = sum(
                    moves.filtered(
                        lambda x: x.id in line.move_ids.ids).mapped(
                        'product_uom_qty'))

    # backport of fix made on odoo v10, on odoo v9 refunds are also summed
    @api.depends('invoice_lines.invoice_id.state')
    def _compute_qty_invoiced(self):
        for line in self:
            qty = 0.0
            for inv_line in line.invoice_lines:
                if inv_line.invoice_id.state not in ['cancel']:
                    if inv_line.invoice_id.type == 'in_invoice':
                        qty += inv_line.uom_id._compute_qty_obj(
                            inv_line.uom_id, inv_line.quantity,
                            line.product_uom)
                    elif inv_line.invoice_id.type == 'in_refund':
                        qty -= inv_line.uom_id._compute_qty_obj(
                            inv_line.uom_id, inv_line.quantity,
                            line.product_uom)
            line.qty_invoiced = qty

    @api.multi
    def button_cancel_remaining(self):
        # TODO faltaría proteger cancel remaining de kits (analogo a en ventas)
        # si es que se da el mismo error de que no se cancela bien. No pudimos
        # ni testearlo porque en realidad no se puede confirmar compra con kit.
        # Cargada incidencia a odoo con id 808056
        for rec in self:
            old_product_qty = rec.product_qty
            # TODO tal vez cambiar en v10
            # en este caso si lo bloqueamos ya que si llegan a querer generar
            # nc lo pueden hacer con el buscar líneas de las facturas
            # y luego lo pueden terminar cancelando
            if rec.qty_invoiced > rec.qty_received:
                raise UserError(_(
                    'You can not cancel remianing qty to receive because '
                    'there are more product invoiced than the received. '
                    'You should correct invoice or ask for a refund'))
            rec.product_qty = rec.qty_received

            # si fue generado por procurements usamos el cancel de procurements
            if rec.procurement_ids:
                rec.procurement_ids.button_cancel_remaining()
            else:
                to_cancel_moves = rec.move_ids.filtered(
                    lambda x: x.state != 'done')
                to_cancel_moves.action_cancel()

            rec.order_id.message_post(
                body=_(
                    'Cancel remaining call for line "%s" (id %s), line '
                    'qty updated from %s to %s') % (
                        rec.name, rec.id, old_product_qty, rec.product_qty))

    @api.multi
    def _compute_vouchers(self):
        for rec in self:
            rec.vouchers = ', '.join(rec.mapped(
                'move_ids.picking_id.voucher_ids.display_name'))

    @api.depends(
        'order_id.state', 'qty_received', 'product_qty',
        'order_id.manually_set_received')
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
            if line.order_id.manually_set_received:
                line.delivery_status = 'received'
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

    @api.depends(
        'order_id.state', 'qty_invoiced', 'product_qty', 'qty_to_invoice',
        'order_id.manually_set_invoiced')
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
            if line.order_id.manually_set_invoiced:
                line.invoice_status = 'invoiced'
                continue

            # usamos qty_to_invoice para compatibilidad con el de return
            # y ademas que tenga en cuenta si el producto es lo recibido o lo
            # pedido
            # if float_compare(
            #         line.qty_invoiced, line.product_qty,
            #         precision_digits=precision) == -1:
            #     line.invoice_status = 'to invoice'
            # elif float_compare(
            #         line.qty_invoiced, line.product_qty,
            #         precision_digits=precision) >= 0:
            #     line.invoice_status = 'invoiced'
            # else:
            #     line.invoice_status = 'no'

            # this code was from an OCA module but it seams to be wrong
            # TODO remove this
            # if line.product_id.purchase_method == 'receive' and not \
            #         line.move_ids.filtered(lambda x: x.state == 'done'):
            #     line.invoice_status = 'to invoice'
            #     # We would like to put 'no', but that would break standard
            #     # odoo tests.
            #     continue

            if abs(float_compare(line.qty_to_invoice, 0.0,
                                 precision_digits=precision)) == 1:
                line.invoice_status = 'to invoice'
            elif float_compare(line.qty_to_invoice, 0.0,
                               precision_digits=precision) == 0:
                line.invoice_status = 'invoiced'
            else:
                line.invoice_status = 'no'


# modificaciones para facilitar creacion de factura
    # este campo no existe en POL, robamos de SOL
    qty_to_invoice = fields.Float(
        compute='_get_to_invoice_qty',
        string='To Invoice',
        store=True,
        readonly=True,
        digits=dp.get_precision('Product Unit of Measure'),
        default=0.0
    )

    @api.depends(
        'qty_invoiced', 'qty_received', 'order_id.state')
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
                    'name': 'qty_on_voucher',
                    'readonly': '1',
                    # on enterprise view is not refres
                    # 'invisible': "not context.get('voucher', False)",
                }))
            placeholder = doc.xpath("//field[2]")[0]
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
                ['invoice_qty', 'qty_to_invoice',
                 'qty_on_voucher']))

            # add button to add all
            placeholder.addprevious(
                etree.Element('button', {
                    'name': 'action_add_all_to_invoice',
                    'type': 'object',
                    'icon': 'fa-plus-square',
                    'string': _('Add all to invoice'),
                }))

            # add button tu open form
            placeholder = doc.xpath("//tree")[0]
            placeholder.append(
                etree.Element('button', {
                    'name': 'action_line_form',
                    'type': 'object',
                    'icon': 'fa-external-link',
                    'string': _('Open Purchase Line Form View'),
                }))

            # make tree view editable
            for node in doc.xpath("/tree"):
                node.set('edit', 'true')
                node.set('create', 'false')
                node.set('editable', 'top')
            res['arch'] = etree.tostring(doc)
        return res

    @api.multi
    def action_line_form(self):
        self.ensure_one()
        # view_id = self.env['ir.model.data'].xmlid_to_res_id(
        #     'product.product_normal_form_view')
        return {
            'name': _('Purchase Line'),
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'purchase.order.line',
            'type': 'ir.actions.act_window',
            # 'domain': [('id', 'in', self.apps_product_ids.ids)],
            'res_id': self.id,
            # 'view_id': view_id,
        }

    @api.multi
    def _compute_invoice_qty(self):
        invoice_id = self._context.get('active_id', False)
        if not invoice_id:
            return True
        for rec in self:
            lines = rec.env['account.invoice.line'].search([
                ('invoice_id', '=', invoice_id),
                ('purchase_line_id', '=', rec.id)])
            if self.env['account.invoice'].browse(invoice_id)\
                    .type == 'in_refund':
                rec.invoice_qty = -1.0 * sum(lines.mapped('quantity'))
            else:
                rec.invoice_qty = sum(lines.mapped('quantity'))

    @api.multi
    def _inverse_invoice_qty(self):
        invoice_id = self._context.get('active_id', False)
        active_model = self._context.get('active_model', False)
        if not invoice_id or active_model != 'account.invoice':
            return True
        invoice = self.env['account.invoice'].browse(invoice_id)
        sign = invoice.type == 'in_refund' and -1.0 or 1.0
        purchase_lines = self.env['account.invoice.line']
        do_not_compute = self._context.get('do_not_compute')
        for rec in self:
            lines = rec.env['account.invoice.line'].search([
                ('invoice_id', '=', invoice_id),
                ('purchase_line_id', '=', rec.id)])
            # TODO ver como agregamos esta validacion de otra manera
            # no funciona bien si, por ej, agregamos una cantidad y luego
            # la aumentamos, en realidad tal vez no hace falta esta validacion
            # y se controla quedando enc antidades negativas. se podria
            # controlar directamente desde el qty_to_invoice con contraint
            # si se necesta
            # if rec.invoice_qty > rec.qty_to_invoice:
            #     raise UserError(_(
            #         'No puede facturar más de lo pendiente a facturar. '
            #         'Verifique la configuración de facturación de sus '
            #         'productos y/o la receipción de la mercadería.'))
            if lines:
                # si existitan lineas y la cantidad es zero borramos
                if not rec.invoice_qty:
                    lines.unlink()
                else:
                    (lines - lines[0]).unlink()
                    lines[0].quantity = sign * rec.invoice_qty
            else:
                # si no hay lineas y no se puso cantidad entonces no hacemos
                # nada
                if not rec.invoice_qty:
                    continue
                data = invoice._prepare_invoice_line_from_po_line(rec)
                data['quantity'] = sign * rec.invoice_qty
                data['invoice_id'] = invoice_id
                new_line = purchase_lines.new(data)
                new_line._set_additional_fields(invoice)
                # we force cache update of company_id value on invoice lines
                # this fix right tax choose
                # prevent price and name being overwrited
                if self.company_id != invoice.company_id:
                    price_unit = new_line.price_unit
                    name = new_line.name
                    new_line.company_id = invoice.company_id
                    new_line._onchange_product_id()
                    new_line.name = name
                    new_line.price_unit = price_unit
                vals = new_line._convert_to_write(new_line._cache)
                purchase_lines.create(vals)
            # recomputamos impuestos
            if do_not_compute:
                continue
            invoice.compute_taxes()
            # el depends de esta funcion no lo hace ejecutar desde aca pero si
            # si se edita en la factura (no estoy seguro porque), lo forzamos
            # aca
            rec._compute_qty_invoiced()

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
            # si filtramos por un voucher, mandamos esa cantidad
            rec.invoice_qty = rec.qty_on_voucher or (
                rec.qty_to_invoice + rec.invoice_qty)

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        res = super(PurchaseOrderLine, self)._onchange_quantity()
        if not self.product_id:
            return

        # if price was not computed (not seller or seller price = 0.0), then
        # use standar price
        if not self.price_unit:
            price_unit = self.product_id.standard_price
            if (
                    price_unit and
                    self.order_id.currency_id != self.product_id.currency_id):
                price_unit = self.product_id.currency_id.compute(
                    price_unit, self.order_id.currency_id)
            if (
                    price_unit and self.product_uom and
                    self.product_id.uom_id != self.product_uom):
                price_unit = self.env['product.uom']._compute_price(
                    self.product_id.uom_id.id, price_unit,
                    to_uom_id=self.product_uom.id)
            self.price_unit = price_unit
        return res
