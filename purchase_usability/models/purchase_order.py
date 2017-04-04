# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api
from openerp.tools.float_utils import float_compare


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

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

    @api.depends('state', 'order_line.qty_received', 'order_line.product_qty')
    def _get_received(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for order in self:
            # on v9 odoo consider done with no more to purchase, PR has been
            # deny, if we change it here we should change odoo behaviour on
            # purchase orders
            # al final dejamos  nuestro criterio porque es confuso para
            # clientes y de hecho odoo, a diferencia de lo que dice el boton
            # si te deja crear las facturas en done
            # if order.state != 'purchase':
            if order.state not in ('purchase', 'done'):
                order.delivery_status = 'no'
                continue

            if any(float_compare(
                    line.qty_received, line.product_qty,
                    precision_digits=precision) == -1
                    for line in order.order_line):
                order.delivery_status = 'to receive'
            elif all(float_compare(
                    line.qty_received, line.product_qty,
                    precision_digits=precision) >= 0
                    for line in order.order_line):
                order.delivery_status = 'received'
            else:
                order.delivery_status = 'no'

    @api.multi
    def button_reopen(self):
        self.write({'state': 'purchase'})

    def _get_invoiced(self):
        # fix de esta funcion porque odoo no lo quiso arreglar
        # cambiamos != purchase por not in purchase, done
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for order in self:
            # if order.state != 'purchase':
            if order.state not in ('purchase', 'done'):
                order.invoice_status = 'no'
                continue

            if any(float_compare(
                    line.qty_invoiced, line.product_qty,
                    precision_digits=precision) == -1
                    for line in order.order_line):
                order.invoice_status = 'to invoice'
            elif all(float_compare(
                    line.qty_invoiced, line.product_qty,
                    precision_digits=precision) >= 0
                    for line in order.order_line):
                order.invoice_status = 'invoiced'
            else:
                order.invoice_status = 'no'
