# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api
from ast import literal_eval


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    purchase_ids = fields.Many2many(
        'purchase.order',
        # related='move_lines.purchase_line_id.order_id',
        compute='_compute_purchase_ids',
        string="Purchase Orders",
        readonly=True,
    )

    @api.multi
    @api.depends('move_lines.purchase_line_id.order_id')
    def _compute_purchase_ids(self):
        for rec in self:
            rec.purchase_ids = self.move_lines.mapped(
                'purchase_line_id.order_id')

    @api.multi
    def add_purchase_line_moves(self):
        self.ensure_one()
        actions = self.env.ref(
            'purchase_usability.action_purchase_line_tree')
        if actions:
            action_read = actions.read()[0]
            context = literal_eval(action_read['context'])
            context['purchase_line_moves'] = True
            action_read['context'] = context
            action_read['domain'] = [
                ('partner_id.commercial_partner_id', '=',
                    self.partner_id.commercial_partner_id.id),
                ('company_id', '=', self.company_id.id),
                ('delivery_status', '=', 'to receive'),
                # estas condiciones podrian borrarse si es necesario
                ('order_id.picking_type_id', '=', self.picking_type_id.id),
                # se pueden agregar condiciones de location (adaptarlas)
                # ('location_dest_id', '=',
                #     order._get_destination_location()),
                # ('location_id', '=',
                #     order.partner_id.property_stock_supplier.id),
            ]
        return action_read
