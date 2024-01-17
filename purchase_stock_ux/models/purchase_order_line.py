##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare
import json
from lxml import etree
import logging
_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    delivery_status = fields.Selection([
        ('no', 'Not purchased'),
        ('to receive', 'To Receive'),
        ('received', 'Received'),
    ],
        string='Delivery Status',
        compute='_compute_delivery_status',
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
        digits='Product Unit of Measure',
    )

    qty_returned = fields.Float(
        string='Returned',
        copy=False,
        default=0.0,
        readonly=True,
        compute='_compute_qty_returned'
    )

    @api.depends_context('voucher')
    def _compute_qty_on_voucher(self):
        # al calcular por voucher no tenemos en cuenta el metodo de facturacion
        # es decir, que calculamos como si fuese metodo segun lo recibido
        voucher = self._context.get('voucher', False)
        if not voucher:
            self.update({'qty_on_voucher': 0.0})
            return
        lines = self.filtered(
            lambda x: x.order_id.state in ['purchase', 'done'])
        moves = self.env['stock.move'].search([
            ('id', 'in', lines.mapped('move_ids').ids),
            ('state', '=', 'done'),
            ('picking_id.vouchers', 'ilike', voucher[0]),
        ])
        for line in lines:
            line.qty_on_voucher = sum(moves.filtered(
                lambda x: x.id in line.move_ids.ids).mapped('product_uom_qty'))

    def button_cancel_remaining(self):
        # la cancelación de kits no está bien resuelta ya que odoo
        # solo computa la cantidad entregada cuando todo el kit se entregó.
        # Cuestión que, por ahora, desactivamos la cancelación de kits.
        bom_enable = 'bom_ids' in self.env['product.template']._fields
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
            if bom_enable:
                bom = self.env['mrp.bom']._bom_find(
                    products=rec.product_id)[rec.product_id]
                if bom and bom.type == 'phantom':
                    raise UserError(_(
                        "Cancel remaining can't be called for Kit Products "
                        "(products with a bom of type kit)."))
            rec.with_context(cancel_from_order=True).product_qty = rec.qty_received
            # la realidad es que probablemente esto de acá no sea necesario. modificar product_qty ya hace que odoo,
            # apartir de 16 al menos, baje las cantidades de los moves. Justamente por esta razon es que ahora
            # pasamos contexto arriba de "cancel_from_order", porque ahora es odoo quien cancela los pickings
            to_cancel_moves = rec.move_ids.filtered(
                lambda x: x.state not in ['done', 'cancel'])
            to_cancel_moves._cancel_quantity()
            rec.order_id.message_post(
                body=_(
                    'Cancel remaining call for line "%s" (id %s), line '
                    'qty updated from %s to %s') % (
                        rec.name, rec.id, old_product_qty, rec.product_qty))

    def _compute_vouchers(self):
        for rec in self:
            rec.vouchers = ', '.join(rec.mapped(
                'move_ids.picking_id.voucher_ids.display_name'))

    @api.depends(
        'order_id.state', 'qty_received', 'qty_returned', 'product_qty',
        'order_id.force_delivered_status')
    def _compute_delivery_status(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for line in self:
            if line.state not in ('purchase', 'done'):
                line.delivery_status = 'no'
                continue
            if line.order_id.force_delivered_status:
                line.delivery_status = line.order_id.force_delivered_status
                continue
            if float_compare(
                    (line.qty_received + line.qty_returned), line.product_qty,
                    precision_digits=precision) == -1:
                line.delivery_status = 'to receive'
            elif float_compare(
                    (line.qty_received + line.qty_returned), line.product_qty,
                    precision_digits=precision) >= 0:
                line.delivery_status = 'received'
            else:
                line.delivery_status = 'no'

    @api.onchange('product_qty')
    def _onchange_product_qty(self):
        if (
                self.state == 'purchase' and
                self.product_id.type in ['product', 'consu'] and
                self.product_qty < self._origin.product_qty):
            warning_mess = {
                'title': _('Ordered quantity decreased!'),
                'message': (
                    '¡Está reduciendo la cantidad pedida! Recomendamos usar'
                    ' el botón para cancelar remanente y'
                    ' luego setear la cantidad deseada.'),
            }
            self.product_qty = self._origin.product_qty
            return {'warning': warning_mess}
        return {}

    @api.depends('order_id.state', 'move_ids.state')
    def _compute_qty_returned(self):
        for line in self:
            qty = 0.0
            for move in line.move_ids.filtered(
                    lambda m: m.state == 'done' and
                    m.location_id.usage != 'supplier' and m.to_refund):
                qty += move.product_uom._compute_quantity(
                    move.product_uom_qty,
                    line.product_uom)
            line.qty_returned = qty

    # Overwrite the origin method to introduce the qty_on_voucher
    def action_add_all_to_invoice(self):
        for rec in self:
            rec.invoice_qty = rec.qty_on_voucher or (
                rec.qty_to_invoice + rec.invoice_qty)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=False, submenu=False):
        """
        If we came from invoice, we send in context 'force_line_edit'
        and we change tree view to make editable and also field qty
        """
        res = super().fields_view_get(
            view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu)
        if self._context.get('force_line_edit') and view_type == 'tree':
            doc = etree.XML(res['arch'])
            placeholder = doc.xpath("//field[1]")[0]
            placeholder.addprevious(
            etree.Element('field', {
            'name': 'qty_on_voucher',
            }))

            # make all fields not editable
            node = doc.xpath("//field[1]")[0]
            node.set('readonly', '1')
            modifiers = json.loads(node.get("modifiers") or "{}")
            modifiers['readonly'] = True
            node.set("modifiers", json.dumps(modifiers))
            res['fields'].update(self.fields_get(['qty_on_voucher']))
            res['arch'] = etree.tostring(doc)

        return res
