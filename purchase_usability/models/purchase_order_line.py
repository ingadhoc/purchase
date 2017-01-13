# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api
from openerp.tools.float_utils import float_compare


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

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
