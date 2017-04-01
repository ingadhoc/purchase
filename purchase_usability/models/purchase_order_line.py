# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import UserError
from openerp.tools.float_utils import float_compare, float_round
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

    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=False, submenu=False):
        """
        If we came from sale order, we send in context 'force_product_edit'
        and we change tree view to make editable and also field qty
        """
        res = super(PurchaseOrderLine, self).fields_view_get(
            view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu)
        purchase_line_moves = self._context.get(
            'purchase_line_moves')
        if purchase_line_moves and view_type == 'tree':
            doc = etree.XML(res['arch'])

            # make all fields not editable
            for node in doc.xpath("//field"):
                node.set('readonly', '1')
                setup_modifiers(node, res['fields'], in_tree_view=True)

            # add qty field
            placeholder = doc.xpath("//field[1]")[0]
            placeholder.addprevious(
                etree.Element('field', {
                    'name': 'picking_qty',
                    # we force editable no matter user rights
                    'readonly': '0',
                }))
            res['fields'].update(self.fields_get(['picking_qty']))

            # add button to add all
            placeholder.addprevious(
                etree.Element('button', {
                    'name': 'action_add_all_to_picking',
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
    def _compute_picking_qty(self):
        picking_id = self._context.get('active_id', False)
        if not picking_id:
            return True
        for rec in self:
            moves = rec.env['stock.move'].search([
                ('picking_id', '=', picking_id),
                ('purchase_line_id', '=', rec.id)])
            rec.picking_qty = sum(moves.mapped('product_uom_qty'))

    @api.multi
    def _inverse_picking_qty(self):
        picking_id = self._context.get('active_id', False)
        active_model = self._context.get('active_model', False)
        if not picking_id or active_model != 'stock.picking':
            return True
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for rec in self:
            new_qty = rec.picking_qty
            if new_qty < 0.0:
                raise UserError(_('Quantity must be positive'))

            # base domain for moves used on all moves searches
            base_moves_domain = [
                # just to ensure we dont break any advance rule
                ('procure_method', '=', 'make_to_stock'),
                ('purchase_line_id', '=', rec.id),
                ('state', 'not in', ['done', 'cancel', 'draft']),
            ]

            # moves actuales en el picking
            actual_moves = rec.env['stock.move'].search(
                base_moves_domain + [('picking_id', '=', picking_id)])
            actual_qty = sum(actual_moves.mapped('product_uom_qty'))

            # cantidad agregada o restada a la cantidad actual del picking
            diff_qty = float_round(
                new_qty - actual_qty, precision_digits=precision)

            # TODo podriamos unificar los metodos de los dos if
            # pero puede complicar la lectura del codigo

            # si agregamos mas cantidad tenemos que agregar moves
            if diff_qty > 0.0:
                # las condiciones las define mayormente el pol
                # (partner, company, etc)
                new_moves = rec.env['stock.move'].search(
                    # opcion si generamos moves sin picking
                    # base_moves_domain + [('picking_id', '=', False)])
                    # opcion robando de otro picking
                    base_moves_domain + [('picking_id', '!=', picking_id)])

                for move in new_moves:
                    if not diff_qty:
                        break
                    # si le pedimos mas cantidad nos devuelve el mismo move
                    new_move = rec.env['stock.move'].browse(
                        move.split(move, diff_qty))
                    # por ahora no cambiamos picking type ni nada porque
                    # solo mostramos purchase lines de mismo picking type

                    old_picking = new_move.picking_id
                    new_move.write({'picking_id': picking_id})
                    # force assign to recompute operations
                    new_move.force_assign()

                    # # si las cantidades son iguales se devolvio el mismo
                    # # tenemos que re computar las operations del picking
                    # # viejo
                    # if move != new_move:
                    #     move.force_assign()

                    # si son iguales quiere decir que se fue el move
                    # entero y tenemos entonces que forzar recomputar
                    # operations en picking viejo
                    # si son distintos forzamos recomputar a traves de los
                    # moves para no recomputar todo el picking
                    if move == new_move:
                        # forzamos desde los moves y no desde el picking
                        # porque el picking filtra moves no en avialble
                        old_picking.move_lines.force_assign()
                    else:
                        move.force_assign()

                    # si no quedan move lines en el picking viejo, lo borramos
                    if not old_picking.move_lines:
                        # como nos quedamos sin moves el force_assign
                        # no limpio las pack operatons, las borramos a mano
                        old_picking.pack_operation_product_ids.unlink()
                        old_picking.unlink()

                    # TODO si queremos marcar las pack operations con las
                    # cantidades deberiamos probar algo de estos dos
                    # pack.write({'qty_done': pack.product_qty})
                    # new_move.action_assign()
                    diff_qty -= new_move.product_qty
            # si sacamos cantidad sacamos moves del picking
            elif diff_qty < 0.0:
                # cambiamos signo para ser mas facil de interpretar
                diff_qty = -diff_qty
                for move in actual_moves:
                    if not diff_qty:
                        break
                    # si le pedimos mas cantidad nos devuelve el mismo move
                    del_move = rec.env['stock.move'].browse(
                        move.split(move, diff_qty))
                    # lo sacamos del picking

                    # opcion si generamos moves sin picking
                    # del_move.write({'picking_id': False})

                    # opcion robando de otro picking: tenemos que buscar o
                    # crear un picking
                    pickings = rec.order_id.picking_ids.filtered(
                        lambda x: (
                            x.state not in [
                                'draft', 'cancel', 'waiting', 'done'] and
                            x.id != picking_id))
                    if pickings:
                        new_picking = pickings[0]
                    else:
                        new_picking = rec.env['stock.picking'].create(
                            rec.order_id._prepare_picking())
                    del_move.write({'picking_id': new_picking.id})
                    del_move.force_assign()

                    # si son iguales quiere decir que se fue el move
                    # entero y tenemos entonces que forzar recomputar
                    # operations en picking de contexto
                    # si son distintos forzamos recomputar a traves de los
                    # moves para no recomputar todo el picking
                    if move == del_move:
                        # forzamos desde los moves y no desde el picking
                        # porque el picking filtra moves no en avialble
                        rec.env['stock.picking'].browse(
                            picking_id).move_lines.force_assign()
                    else:
                        move.force_assign()

                    diff_qty -= del_move.product_qty
            if diff_qty:
                raise UserError(_(
                    "We haven't found any move that we can add to this "
                    "picking."))

    picking_qty = fields.Float(
        string='Quantity',
        compute='_compute_picking_qty',
        inverse='_inverse_picking_qty',
        search='_search_picking_qty',
    )

    @api.model
    def _search_picking_qty(self, operator, operand):
        """
        implementamos solo el caso "('picking_qty', '!=', False)" que es el que
        usamos en la vista y unico que nos interesa por ahora
        """
        picking_id = self._context.get('active_id', False)
        active_model = self._context.get('active_model', False)
        if active_model != 'stock.picking':
            return []
        return [('move_ids.picking_id', 'in', [picking_id])]

    @api.multi
    def action_add_all_to_picking(self):
        for rec in self:
            rec.picking_qty = rec.product_qty - rec.qty_received
