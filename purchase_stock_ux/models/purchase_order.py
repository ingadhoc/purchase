##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    force_delivered_status = fields.Selection([
        ('no', 'Not purchased'),
        ('received', 'Received'),
    ],
        tracking=True,
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
        'state', 'order_line.qty_received', 'order_line.qty_returned', 'order_line.product_qty',
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
                    (line.qty_received + line.qty_returned), line.product_qty,
                    precision_digits=precision) == -1
                    for line in order.order_line):
                order.delivery_status = 'to receive'
            elif all(float_compare(
                    (line.qty_received + line.qty_returned), line.product_qty,
                    precision_digits=precision) >= 0
                    for line in order.order_line):
                order.delivery_status = 'received'
            else:
                order.delivery_status = 'no'

    def write(self, values):
        self.check_force_delivered_status(values)
        return super().write(values)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self.check_force_delivered_status(vals)
        return super().create(vals_list)

    @api.model
    def check_force_delivered_status(self, vals):
        if vals.get('force_delivered_status') and not self.user_has_groups('base.group_system'):
            group = self.env.ref('base.group_system').sudo()
            raise UserError(_(
                'Only users with "%s / %s" can Set Received manually') % (
                group.category_id.name, group.name))

    def button_cancel(self):
        self = self.with_context(cancel_from_order=True)
        return super().button_cancel()

    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        res['note'] = self.internal_notes
        return res
