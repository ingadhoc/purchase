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

    @api.multi
    def _create_picking(self):
        for order in self:
            if order.picking_type_id.merge_incoming_picking:
                picking = self.env['stock.picking'].search([
                    ('partner_id', '=', order.partner_id.id),
                    ('picking_type_id', '=', order.picking_type_id.id),
                    ('location_dest_id', '=',
                        order._get_destination_location()),
                    ('location_id', '=',
                        order.partner_id.property_stock_supplier.id),
                    ('company_id', '=', order.company_id.id),
                    ('state', '!=', 'done'),
                ], limit=1)
                if picking:
                    if any([ptype in ['product', 'consu']
                            for ptype in
                            order.order_line.mapped('product_id.type')]):
                        moves = order.order_line.filtered(
                            lambda r: r.product_id.type in
                            ['product', 'consu'])._create_stock_moves(picking)
                        move_ids = moves.action_confirm()
                        moves = self.env['stock.move'].browse(move_ids)
                        moves.force_assign()
                    self -= order
        return super(PurchaseOrder, self)._create_picking()
