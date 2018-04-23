##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    manually_set_invoiced = fields.Boolean(
        string='Manually Set Invoiced?',
        help='If you set this field to True, then all lines invoiceable lines'
        'will be set to invoiced?',
        track_visibility='onchange',
        copy=False,
    )
    manually_set_received = fields.Boolean(
        string='Manually Set Received?',
        help='If you set this field to True, then all lines deliverable lines'
        'will be set to received?',
        track_visibility='onchange',
        copy=False,
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

    @api.depends(
        'state', 'order_line.qty_received', 'order_line.product_qty',
        'manually_set_received')
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

            if order.manually_set_received:
                order.delivery_status = 'received'
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

    @api.depends('manually_set_invoiced', 'order_line.move_ids.state')
    def _get_invoiced(self):
        # fix de esta funcion porque odoo no lo quiso arreglar
        # cambiamos != purchase por not in purchase, done
        # precision = self.env['decimal.precision'].precision_get(
        #     'Product Unit of Measure')
        for order in self:
            # if order.state != 'purchase':
            if order.state not in ('purchase', 'done'):
                order.invoice_status = 'no'
                continue

            if order.manually_set_invoiced:
                order.invoice_status = 'invoiced'
                continue

            # tambien modificamos y hacemos de esta manera para poder
            # usar en purchase_usability_return_invoicing
            if any(line.invoice_status == 'to invoice'
                   for line in order.order_line):
                order.invoice_status = 'to invoice'
            elif all(line.invoice_status == 'invoiced'
                     for line in order.order_line):
                order.invoice_status = 'invoiced'
            else:
                order.invoice_status = 'no'
            # if any(float_compare(
            #         line.qty_invoiced, line.product_qty,
            #         precision_digits=precision) == -1
            #         for line in order.order_line):
            #     order.invoice_status = 'to invoice'
            # elif all(float_compare(
            #         line.qty_invoiced, line.product_qty,
            #         precision_digits=precision) >= 0
            #         for line in order.order_line):
            #     order.invoice_status = 'invoiced'
            # else:
            #     order.invoice_status = 'no'

    @api.multi
    def button_set_invoiced(self):
        if not self.user_has_groups('base.group_system'):
            group = self.env.ref('base.group_system').sudo()
            raise UserError(_(
                'Only users with "%s / %s" can Set Invoiced manually') % (
                group.category_id.name, group.name))
        # en compras el invoice_status no se calcula desde las lineas por eso
        # lo pisamos en la PO. No pisamos el qty_invoiced porque nos parece
        # mas prolijo para restablecero ver que paso
        self.write({'invoice_status': 'invoiced'})
        self.order_line.write({'qty_to_invoice': 0.0})
        self.message_post(body='Manually setted as invoiced')

    @api.multi
    def write(self, vals):
        self.check_manually_set_invoiced(vals)
        self.check_manually_set_received(vals)
        return super(PurchaseOrder, self).write(vals)

    @api.model
    def create(self, vals):
        self.check_manually_set_invoiced(vals)
        self.check_manually_set_received(vals)
        return super(PurchaseOrder, self).create(vals)

    @api.model
    def check_manually_set_invoiced(self, vals):
        if vals.get('manually_set_invoiced') and not self.user_has_groups(
                'base.group_system'):
            group = self.env.ref('base.group_system').sudo()
            raise UserError(_(
                'Only users with "%s / %s" can Set Invoiced manually') % (
                group.category_id.name, group.name))

    @api.model
    def check_manually_set_received(self, vals):
        if vals.get('manually_set_received') and not self.user_has_groups(
                'base.group_system'):
            group = self.env.ref('base.group_system').sudo()
            raise UserError(_(
                'Only users with "%s / %s" can Set Received manually') % (
                group.category_id.name, group.name))

    @api.multi
    def action_view_invoice(self):
        # we fix that if we create an invoice from an
        # PO send the currency in the context
        result = super(PurchaseOrder, self).action_view_invoice()
        result['context'].update({'default_currency_id': self.currency_id.id})
        # Modificamos para que desde las compras se vaya a facturas en vista
        # lista siempre por un error con el módulo account_invoice_commission.
        # Para probarlo en v10 a ver si se reproduce:
        # 1. Generar orden de compra y validar
        # 2. Generar una factura y validarla
        # 3. Desde la orden de compra ir a ver facturas
        # (desactivar este parche) y entones nos lleva
        # a la factura en vista form
        # 4. Probar generar nueva factura
        result['domain'] = "[('id', 'in', " + str(self.invoice_ids.ids) + ")]"
        result['views'] = []
        return result
