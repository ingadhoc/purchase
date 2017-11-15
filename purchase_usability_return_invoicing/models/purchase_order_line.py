# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qty_returned = fields.Float(
        string='Returned',
        copy=False,
        default=0.0,
        # digits=dp.get_precision('Product Unit of Measure'),
        readonly=True,
        compute='_compute_qty_returned'
    )

    @api.depends(
        'order_id.state', 'move_ids.state', 'move_ids.product_uom_qty')
    def _compute_qty_received(self):
        """
        Modificamos un poco segun esta en v11
        """
        super(PurchaseOrderLine, self)._compute_qty_received()
        productuom = self.env['product.uom']
        for line in self:
            if line.order_id.state not in ['purchase', 'done']:
                line.qty_received = 0.0
                continue
            if line.product_id.type not in ['consu', 'product']:
                line.qty_received = line.product_qty
                continue
            bom_delivered = self.sudo()._get_bom_delivered(line.sudo())
            if bom_delivered and any(bom_delivered.values()):
                total = line.product_qty
            elif bom_delivered:
                total = 0.0
            else:
                total = 0.0
                for move in line.move_ids:
                    if move.state == 'done':
                        # MODIFICADO ACA
                        if move.product_uom != line.product_uom:
                            qty = productuom._compute_qty_obj(
                                move.product_uom, move.product_uom_qty,
                                line.product_uom)
                        else:
                            qty = move.product_uom_qty
                        if move.location_dest_id.usage == "supplier":
                            if move.to_refund_so:
                                total -= qty
                        else:
                            total += qty
            line.qty_received = total

    @api.multi
    @api.depends('order_id.state', 'move_ids.state')
    def _compute_qty_returned(self):
        for line in self:
            line.qty_returned = 0.0
            bom_delivered = self.sudo()._get_bom_delivered(line.sudo())
            qty = 0.0
            if not bom_delivered:
                for move in line.move_ids:
                    if move.state == 'done' and move.location_id.usage != \
                            'supplier':
                        qty += move.product_uom._compute_qty_obj(
                            move.product_uom, move.product_uom_qty,
                            line.product_uom)
            line.qty_returned = qty

    @api.depends('qty_returned')
    def _get_to_invoice_qty(self):
        """
        Modificamos la funcion original para que si el producto es segun lo
        pedido, para que funcione el reembolo hacemos que la cantidad a
        facturar reste la cantidad devuelta.
        NOTA: solo lo hacemos si policy "order" porque en policy "delivered"
        odoo ya lo descuenta a la cantidad entregada y automáticamente lo
        termina facturando
        """
        super(PurchaseOrderLine, self)._get_to_invoice_qty()
        for line in self:
            # igual que por defecto, si no en estos estados, no hay a facturar
            if line.order_id.state not in ['sale', 'done']:
                continue
            if line.product_id.invoice_policy == 'order':
                line.qty_to_invoice = (
                    line.product_uom_qty - line.qty_returned -
                    line.qty_invoiced)
