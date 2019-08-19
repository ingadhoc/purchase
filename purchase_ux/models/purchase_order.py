##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    force_invoiced_status = fields.Selection([
        ('no', 'Nothing to Bill'),
        ('invoiced', 'No Bill to Receive'),
    ],
        track_visibility='onchange',
        copy=False,
    )
    force_delivered_status = fields.Selection([
        ('no', 'Not purchased'),
        ('received', 'Received'),
    ],
        track_visibility='onchange',
        copy=False,
    )
    delivery_status = fields.Selection([
        ('no', 'Not purchased'),
        ('to receive', 'To Receive'),
        ('received', 'Received'),
    ],
        compute='_compute_delivery_status',
        store=True,
        readonly=True,
        copy=False,
        default='no'
    )

    with_returns = fields.Boolean(
        compute='_compute_with_returns',
        store=True,
    )

    @api.depends('order_line.qty_returned')
    def _compute_with_returns(self):
        for order in self:
            if any(line.qty_returned for line in order.order_line):
                order.with_returns = True
            else:
                order.with_returns = False

    @api.depends(
        'state', 'order_line.qty_received', 'order_line.product_qty',
        'force_delivered_status')
    def _compute_delivery_status(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for order in self:
            if order.state not in ('purchase', 'done'):
                order.delivery_status = 'no'
                continue

            if order.force_delivered_status:
                order.delivery_status = order.force_delivered_status
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

    @api.depends('force_invoiced_status', 'order_line.move_ids.state')
    def _get_invoiced(self):
        for order in self:
            if order.state not in ('purchase', 'done'):
                order.invoice_status = 'no'
                continue

            if order.force_invoiced_status:
                order.invoice_status = order.force_invoiced_status
                continue

            # we also modify and do in this way to be able
            # use in purchase_usability_return_invoicing
            if any(line.invoice_status == 'to invoice'
                   for line in order.order_line):
                order.invoice_status = 'to invoice'
            elif all(line.invoice_status == 'invoiced'
                     for line in order.order_line):
                order.invoice_status = 'invoiced'
            else:
                order.invoice_status = 'no'

    @api.multi
    def button_set_invoiced(self):
        if not self.user_has_groups('base.group_system'):
            group = self.env.ref('base.group_system').sudo()
            raise UserError(_(
                'Only users with "%s / %s" can Set Invoiced manually') % (
                group.category_id.name, group.name))
        # In purchases the invoice status is not calculated from the lines,
        # so we step on it in the PO. Do not step on the qty_invoiced because
        # it seems more neat to restore what happened

        self.write({'invoice_status': 'invoiced'})
        self.order_line.write({'qty_to_invoice': 0.0})
        self.message_post(body=_('Manually setted as invoiced'))

    @api.multi
    def write(self, vals):
        self.check_force_invoiced_status(vals)
        self.check_force_delivered_status(vals)
        return super(PurchaseOrder, self).write(vals)

    @api.model
    def create(self, vals):
        self.check_force_invoiced_status(vals)
        self.check_force_delivered_status(vals)
        return super(PurchaseOrder, self).create(vals)

    @api.model
    def check_force_invoiced_status(self, vals):
        if vals.get('force_invoiced_status') and not self.user_has_groups(
                'base.group_system'):
            group = self.env.ref('base.group_system').sudo()
            raise UserError(_(
                'Only users with "%s / %s" can Set Invoiced manually') % (
                group.category_id.name, group.name))

    @api.model
    def check_force_delivered_status(self, vals):
        if vals.get('force_delivered_status') and not self.user_has_groups(
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
        return result

    @api.multi
    def update_prices_with_supplier_cost(self):
        net_price_installed = 'net_price' in self.env[
            'product.supplierinfo']._fields
        for rec in self.order_line.filtered('price_unit'):
            seller = rec.product_id._select_seller(
                partner_id=rec.order_id.partner_id,
                # usamos minimo de cantidad 0 porque si no seria complicado
                # y generariamos registros para cada cantidad que se esta
                # comprando
                quantity=0.0,
                date=rec.order_id.date_order and
                rec.order_id.date_order.date(),
                # idem quantity, no lo necesitamos
                uom_id=False,
            )
            if not seller:
                seller = self.env['product.supplierinfo'].create({
                    'date_start': rec.order_id.date_order and
                    rec.order_id.date_order.date(),
                    'name': rec.order_id.partner_id.id,
                    'product_tmpl_id': rec.product_id.product_tmpl_id.id,
                })
            price_unit = rec.price_unit
            if rec.product_uom and seller.product_uom != rec.product_uom:
                price_unit = rec.product_uom._compute_price(
                    price_unit, seller.product_uom)

            if net_price_installed:
                seller.net_price = rec.order_id.currency_id.compute(
                    price_unit, seller.currency_id)
            else:
                seller.price = rec.order_id.currency_id.compute(
                    price_unit, seller.currency_id)

    @api.multi
    def update_prices(self):
        for line in self.order_line:
            line._onchange_quantity()
